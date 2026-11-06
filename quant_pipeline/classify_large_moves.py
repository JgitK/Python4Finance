"""Apply the volume rule to each large move that nobody classified.

Decision D11 asks for a review of each one-day move larger than the review
limit. Decision D14 gives the rule for that review. This script reads the
raw price file, finds the large moves, and runs the rule on each move that
is not yet in the corporate_actions seed.

The script writes the named moves into the seed. It prints the unclear
moves as a list. A person reads that list and writes those rows by hand.

Run this file from the quant_pipeline folder:

    . .venv/bin/activate
    python classify_large_moves.py --write

Build the dbt models again after a write. The seed changes the prices.
"""

from __future__ import annotations

import argparse
import sys

import duckdb
import pandas as pd
import yaml

from quant import large_moves, warehouse

DBT_DIR = warehouse.DEFAULT_WAREHOUSE.parent
SEEDS_DIR = DBT_DIR / "seeds"
SEED_FILE = SEEDS_DIR / "corporate_actions.csv"
PRICES_FILE = DBT_DIR.parents[0] / "data" / "raw_prices.parquet"


def read_limit() -> float:
    """Read the review limit from the dbt project, so both sides agree."""
    with open(DBT_DIR / "dbt_project.yml") as handle:
        return yaml.safe_load(handle)["vars"]["large_move_review_limit"]


def read_raw_prices() -> pd.DataFrame:
    """Read the raw price file. Drop the excluded tickers."""
    excluded = set(pd.read_csv(SEEDS_DIR / "price_data_exclusions.csv")["ticker"])
    frame = duckdb.sql(
        f"select ticker, date as price_date, open, close, volume "
        f"from read_parquet('{PRICES_FILE}') where close > 0").df()
    frame["price_date"] = pd.to_datetime(frame["price_date"])
    return frame[~frame["ticker"].isin(excluded)]


def main() -> None:
    """Run the rule and report. Write the seed only with --write."""
    parser = argparse.ArgumentParser(description="Classify the large moves.")
    parser.add_argument("--write", action="store_true",
                        help="Add the named moves to the corporate_actions seed.")
    args = parser.parse_args()

    limit = read_limit()
    prices = read_raw_prices()
    seed = pd.read_csv(SEED_FILE, parse_dates=["date"])
    reviewed = set(zip(seed["ticker"], seed["date"]))

    moves = large_moves.large_moves(prices, limit=limit)
    moves["price_date"] = pd.to_datetime(moves["price_date"])
    new = moves[[(t, d) not in reviewed
                 for t, d in zip(moves["ticker"], moves["price_date"])]]
    print(f"{len(moves)} move(s) beyond {limit:.0%}. "
          f"{len(moves) - len(new)} are already in the seed.")
    for kind, count in new["kind"].value_counts().items():
        print(f"  {kind:<17} {count}")

    unclear = new[new["kind"] == large_moves.UNCLEAR].sort_values(
        ["ticker", "price_date"])
    if len(unclear):
        print(f"\n{len(unclear)} unclear move(s) in "
              f"{unclear['ticker'].nunique()} ticker(s). A person reads these:")
        show = unclear[["ticker", "price_date", "prev_close", "open", "close",
                        "daily_return", "ratio", "intraday"]].copy()
        show["price_date"] = show["price_date"].dt.date
        print(show.to_string(index=False))

    rows = large_moves.seed_rows(new)
    if not args.write:
        print(f"\nDry run. {len(rows)} row(s) would go into the seed. "
              "Use --write to add them.")
        return
    merged = pd.concat([seed.assign(date=seed["date"].dt.strftime("%Y-%m-%d")),
                        rows], ignore_index=True)
    merged = merged.sort_values(["ticker", "date"]).drop_duplicates(
        ["ticker", "date"])
    merged.to_csv(SEED_FILE, index=False)
    print(f"\nWrote {len(rows)} new row(s). The seed holds {len(merged)} row(s).")
    if len(unclear):
        print("The unclear moves are not in the seed. Add them by hand.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
