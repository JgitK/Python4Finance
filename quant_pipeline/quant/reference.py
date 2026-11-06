"""Build the reference data: S&P 500 membership and GICS sectors.

The universe is the S&P 500 on each date. A stock is in the universe only
while it is in the index. This rule removes the survivorship bias of a list
of stocks that are large today.

Two free sources supply the data:
  - fja05680/sp500 (MIT license). The file sp500_ticker_start_end.csv has one
    row for each stint of a stock in the index.
  - datasets/s-and-p-500-companies (ODC-PDDL). The git history of
    data/constituents.csv has the GICS sector of each member over time.

Clone the two repositories, then run:

    python -m quant.reference --sp500 PATH --companies PATH

The script writes two dbt seeds: sp500_membership.csv and stock_sectors.csv.
"""

from __future__ import annotations

import argparse
import csv
import io
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
    args = parser.parse_args()
    n_members, n_sectors = write_seeds(args.sp500, args.companies)
    print(f"Wrote {n_members} membership rows and {n_sectors} sectors.")


if __name__ == "__main__":
    main()
