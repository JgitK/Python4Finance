"""Build the reference data: S&P 500 membership and GICS sectors.

The universe is the S&P 500 on each date. A stock is in the universe only
while it is in the index. This rule removes the survivorship bias of a list
of stocks that are large today.

The Nasdaq universe is a rule, not an index. A stock is in the universe in
a month when it is an operating company listed on the Nasdaq, with a market
cap of at least a limit in the snapshot of that month. Each rule uses only
the data of that month, so the universe is point-in-time.

Three free sources supply the data:
  - fja05680/sp500 (MIT license). The file sp500_ticker_start_end.csv has one
    row for each stint of a stock in the index.
  - datasets/s-and-p-500-companies (ODC-PDDL). The git history of
    data/constituents.csv has the GICS sector of each member over time.
  - rreichel3/US-Stock-Symbols. The git history of
    nasdaq/nasdaq_full_tickers.json has the Nasdaq listing of each day,
    with the market cap and the sector. The repository has no license
    file. The seeds keep only derived facts: tickers, dates, and sectors.

Clone the three repositories, then run:

    python -m quant.reference --sp500 PATH --companies PATH --nasdaq PATH

The script writes four dbt seeds: sp500_membership.csv, stock_sectors.csv,
nasdaq_membership.csv, and nasdaq_sectors.csv.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

# The 11 GICS sectors. A label that is not in this set is a data error.
GICS_SECTORS = frozenset({
    "Communication Services", "Consumer Discretionary", "Consumer Staples",
    "Energy", "Financials", "Health Care", "Industrials",
    "Information Technology", "Materials", "Real Estate", "Utilities",
})

SEEDS_DIR = Path(__file__).resolve().parents[1] / "dbt" / "seeds"

# The Nasdaq sector names, with the GICS sector that is nearest to each one.
# The two systems are not the same, so this map is an approximation.
NASDAQ_TO_GICS = {
    "Technology": "Information Technology",
    "Finance": "Financials",
    "Health Care": "Health Care",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Basic Materials": "Materials",
    "Telecommunications": "Communication Services",
}

# The minimum market cap for the Nasdaq universe, in dollars.
DEFAULT_MIN_MARKET_CAP = 1e9

# A security with one of these names is not an operating company: a warrant,
# a right, a unit of a blank-check company, a fund, a preferred share, or a
# note. "Common Units" of a partnership are company shares, so they stay.
_NOT_A_COMPANY = re.compile(
    r"\bwarrants?\b|\brights?\b|(?<!common )\bunits?\b|acquisition corp"
    r"|\betf\b|\bfund\b|preferred (stock|shares)"
    r"|depositary shares? (each )?representing|\bnotes? due\b",
    re.IGNORECASE,
)


def tickers_in_range(intervals: Iterable[dict[str, str]], start: str,
                     end: str) -> list[str]:
    """Return the tickers with an index stint that overlaps the date range.

    The end_date of a stint is the first day out of the index. An empty
    end_date means that the stock is still in the index.
    """
    found = {
        row["ticker"]
        for row in intervals
        if row["start_date"] <= end
        and (not row["end_date"] or row["end_date"] > start)
    }
    return sorted(found)


def sector_map(snapshots: Iterable[tuple[str, list[dict[str, str]]]]
               ) -> dict[str, str]:
    """Return the GICS sector of each ticker.

    Each snapshot is a date and the rows of the constituents file on that
    date. Use the newest snapshot with a valid GICS sector for each ticker.
    """
    sectors: dict[str, str] = {}
    for _, rows in sorted(snapshots, key=lambda snap: snap[0]):
        for row in rows:
            ticker = (row.get("Symbol") or "").strip()
            label = (row.get("GICS Sector") or row.get("Sector") or "").strip()
            if ticker and label in GICS_SECTORS:
                sectors[ticker] = label
    return sectors


def is_operating_company(name: str) -> bool:
    """Return True when the security name is the stock of a company."""
    return not _NOT_A_COMPANY.search(name)


def _market_cap(row: dict[str, str]) -> float:
    try:
        return float(row.get("marketCap") or 0)
    except ValueError:
        return 0.0


def nasdaq_intervals(snapshots: list[tuple[str, list[dict[str, str]]]],
                     min_market_cap: float) -> list[dict[str, str]]:
    """Make the index stints of the Nasdaq universe from monthly snapshots.

    A stock is in the universe on a snapshot date when it is an operating
    company with a market cap of at least the limit. A stint starts on the
    first such snapshot. It ends on the next snapshot without the stock,
    because the end date is the first day out. An open stint has an empty
    end date.
    """
    stints: list[dict[str, str]] = []
    open_stints: dict[str, dict[str, str]] = {}
    for date, rows in sorted(snapshots, key=lambda snap: snap[0]):
        members = {
            row["symbol"].strip() for row in rows
            if is_operating_company(row.get("name", ""))
            and _market_cap(row) >= min_market_cap
        }
        for ticker in sorted(set(open_stints) - members):
            open_stints.pop(ticker)["end_date"] = date
        for ticker in sorted(members - set(open_stints)):
            stint = {"ticker": ticker, "start_date": date, "end_date": ""}
            open_stints[ticker] = stint
            stints.append(stint)
    return sorted(stints, key=lambda s: (s["ticker"], s["start_date"]))


def nasdaq_sector_map(snapshots: list[tuple[str, list[dict[str, str]]]]
                      ) -> dict[str, str]:
    """Return the GICS sector of each Nasdaq stock. The newest label wins."""
    sectors: dict[str, str] = {}
    for _, rows in sorted(snapshots, key=lambda snap: snap[0]):
        for row in rows:
            label = NASDAQ_TO_GICS.get((row.get("sector") or "").strip())
            if label:
                sectors[row["symbol"].strip()] = label
    return sectors


def first_commit_of_each_month(log: list[tuple[str, str]], start: str,
                               end: str) -> list[tuple[str, str]]:
    """Select the first commit of each month in the range.

    Each log item is a date and a commit hash.
    """
    picked: dict[str, tuple[str, str]] = {}
    for date, commit in sorted(log):
        if start <= date <= end and date[:7] not in picked:
            picked[date[:7]] = (date, commit)
    return [picked[month] for month in sorted(picked)]


def read_nasdaq_snapshots(repo: Path, start: str, end: str
                          ) -> list[tuple[str, list[dict[str, str]]]]:
    """Read the first Nasdaq listing of each month from the git history."""
    path = "nasdaq/nasdaq_full_tickers.json"
    log = subprocess.run(
        ["git", "log", "--format=%ad %H", "--date=short", "--", path],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.split()
    commits = first_commit_of_each_month(
        list(zip(log[0::2], log[1::2])), start, end)
    snapshots = []
    for date, commit in commits:
        text = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=repo, check=True, capture_output=True, text=True,
        ).stdout
        snapshots.append((date, json.loads(text)))
    return snapshots


def write_nasdaq_seeds(nasdaq_repo: Path, start: str, end: str,
                       min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
                       seeds_dir: Path = SEEDS_DIR) -> tuple[int, int]:
    """Write the Nasdaq membership seed and the Nasdaq sector seed.

    Return the number of stints and the number of sector rows.
    """
    snapshots = read_nasdaq_snapshots(nasdaq_repo, start, end)
    stints = nasdaq_intervals(snapshots, min_market_cap)
    sectors = nasdaq_sector_map(snapshots)

    with (seeds_dir / "nasdaq_membership.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, ["ticker", "start_date", "end_date"])
        writer.writeheader()
        writer.writerows(stints)

    members = {stint["ticker"] for stint in stints}
    with (seeds_dir / "nasdaq_sectors.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "sector"])
        for ticker in sorted(members & set(sectors)):
            writer.writerow([ticker, sectors[ticker]])
    return len(stints), len(members & set(sectors))


def read_snapshots(repo: Path) -> list[tuple[str, list[dict[str, str]]]]:
    """Read every version of data/constituents.csv from the git history."""
    path = "data/constituents.csv"
    log = subprocess.run(
        ["git", "log", "--format=%H %ad", "--date=short", "--", path],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.split()
    snapshots = []
    for commit, date in zip(log[0::2], log[1::2]):
        text = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=repo, check=True, capture_output=True, text=True,
        ).stdout.lstrip("﻿")
        snapshots.append((date, list(csv.DictReader(io.StringIO(text)))))
    return snapshots


def write_seeds(sp500_repo: Path, companies_repo: Path,
                seeds_dir: Path = SEEDS_DIR) -> tuple[int, int]:
    """Write the membership seed and the sector seed.

    Return the number of membership rows and the number of sector rows.
    """
    with (sp500_repo / "sp500_ticker_start_end.csv").open() as handle:
        intervals = list(csv.DictReader(handle))
    sectors = sector_map(read_snapshots(companies_repo))

    with (seeds_dir / "sp500_membership.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, ["ticker", "start_date", "end_date"])
        writer.writeheader()
        writer.writerows(
            {k: row[k] for k in ("ticker", "start_date", "end_date")}
            for row in intervals
        )

    members = {row["ticker"] for row in intervals}
    with (seeds_dir / "stock_sectors.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "sector"])
        for ticker in sorted(members & set(sectors)):
            writer.writerow([ticker, sectors[ticker]])
    return len(intervals), len(members & set(sectors))


def main() -> None:
    """Parse the command line and write the seeds."""
    parser = argparse.ArgumentParser(description="Build the reference seeds.")
    parser.add_argument("--sp500", type=Path, required=True,
                        help="The path of the fja05680/sp500 clone.")
    parser.add_argument("--companies", type=Path, required=True,
                        help="The path of the s-and-p-500-companies clone.")
    parser.add_argument("--nasdaq", type=Path, required=True,
                        help="The path of the US-Stock-Symbols clone.")
    parser.add_argument("--start", default="2022-11-01")
    parser.add_argument("--end", default="2026-11-30")
    parser.add_argument("--min-market-cap", type=float,
                        default=DEFAULT_MIN_MARKET_CAP)
    args = parser.parse_args()
    n_members, n_sectors = write_seeds(args.sp500, args.companies)
    print(f"S&P 500: {n_members} membership rows and {n_sectors} sectors.")
    n_members, n_sectors = write_nasdaq_seeds(
        args.nasdaq, args.start, args.end, args.min_market_cap)
    print(f"Nasdaq: {n_members} membership rows and {n_sectors} sectors.")


if __name__ == "__main__":
    main()
