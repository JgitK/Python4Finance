"""Export the data of the web page as JSON files.

The web page is static. This module reads the warehouse one time and it
writes the JSON files that the page loads. The contract of these files is
in docs/web_plan.md, section "The data contract".

Most functions here are pure transforms of pandas frames. Only `main` and
the `read_*` functions open the warehouse.

Run it with:  .venv/bin/python -m quant.export_web
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
WEB_DATA_DIR = ROOT / "web" / "public" / "data"

BENCHMARK = "SPY"
RISK_FREE = 0.045
TRADING_DAYS = 252
TOP_N = 5
RETURNS_DAYS = 504
ICHIMOKU_DAYS = 252
DISPLACEMENT = 26

# Each window: key, trading days, the name of the effect, what it means.
WINDOW_TABLE = [
    ("1M", 21, "Short-term reversal", "Past winners tend to fall back"),
    ("3M", 63, "Momentum", "Past winners tend to continue"),
    ("6M", 126, "Momentum", "Past winners tend to continue"),
    ("1Y", 252, "Momentum", "Past winners tend to continue"),
    ("2Y", 504, "Long-term reversal", "Past winners tend to fall back"),
    ("5Y", 1260, "Long-term reversal", "Past winners tend to fall back"),
]
WINDOW_DAYS = {key: days for key, days, _, _ in WINDOW_TABLE}
STABLE_KEYS = ("3M", "6M", "1Y")

# The holding period of the walk-forward windows, in trading days.
SCORECARD_HOLD_DAYS = 180


# --- small helpers -----------------------------------------------------

def clean(value: Any) -> float | None:
    """Round a number to 6 places. Return None for NaN and None."""
    if value is None:
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, 6)


def clean_list(values: Any) -> list[float | None]:
    """Apply `clean` to each value of a sequence."""
    return [clean(v) for v in values]


def date_text(value: Any) -> str:
    """Return a date as YYYY-MM-DD."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def write_json(path: Path, payload: Any) -> None:
    """Write compact JSON. Make the folder when it does not exist."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"),
                               allow_nan=False))


# --- leaders -----------------------------------------------------------

def window_cum_returns(returns: pd.DataFrame, days: int) -> pd.Series:
    """Return the cumulative return of each ticker over the last `days`.

    A ticker needs a return on each of the `days` dates. A ticker with a
    shorter history is not in the result.
    """
    if len(returns) < days:
        return pd.Series(dtype=float)
    tail = returns.tail(days)
    full = tail.notna().all(axis=0)
    return (1.0 + tail.loc[:, full]).prod(axis=0) - 1.0


def window_annual_vol(returns: pd.DataFrame, days: int,
                      tickers: list[str]) -> pd.Series:
    """Return the annual volatility of the daily returns of the window."""
    tail = returns.tail(days)[tickers]
    return tail.std(axis=0, ddof=1) * math.sqrt(TRADING_DAYS)


def rank_in_sectors(cum: pd.Series, sectors: dict[str, str]) -> pd.DataFrame:
    """Rank the tickers by cumulative return inside each sector.

    Tickers with no sector are dropped. A tie goes to the first ticker
    in alphabetical order.
    """
    frame = pd.DataFrame({"ticker": cum.index, "cum": cum.to_numpy()})
    frame["sector"] = frame["ticker"].map(sectors)
    frame = frame.dropna(subset=["sector", "cum"])
    frame = frame.sort_values(["sector", "cum", "ticker"],
                              ascending=[True, False, True])
    frame["rank"] = frame.groupby("sector").cumcount() + 1
    return frame.reset_index(drop=True)


def build_leaders(returns: pd.DataFrame, sectors: dict[str, str],
                  windows: dict[str, int] | None = None,
                  top_n: int = TOP_N) -> dict[str, list[dict[str, Any]]]:
    """Return the top `top_n` of each sector for each window.

    `returns` is a wide frame. The rows are dates and the columns are
    tickers. `stable` is true for a ticker that is in the top `top_n` of
    its sector on the 3M, 6M and 1Y windows.
    """
    windows = WINDOW_DAYS if windows is None else windows
    ranked = {key: rank_in_sectors(window_cum_returns(returns, days), sectors)
              for key, days in windows.items()}

    stable_sets = []
    for key in STABLE_KEYS:
        if key not in ranked:
            stable_sets = []
            break
        frame = ranked[key]
        stable_sets.append(set(frame.loc[frame["rank"] <= top_n, "ticker"]))
    stable = set.intersection(*stable_sets) if stable_sets else set()

    result: dict[str, list[dict[str, Any]]] = {}
    for key, days in windows.items():
        top = ranked[key][ranked[key]["rank"] <= top_n]
        vols = window_annual_vol(returns, days, list(top["ticker"]))
        rows = []
        for item in top.itertuples():
            vol = float(vols[item.ticker])
            half = 1.96 * vol * math.sqrt(days / TRADING_DAYS)
            rows.append({
                "ticker": item.ticker,
                "sector": item.sector,
                "rank": int(item.rank),
                "cumReturn": clean(item.cum),
                "annualVol": clean(vol),
                "rangeLow": clean(item.cum - half),
                "rangeHigh": clean(item.cum + half),
                "stable": item.ticker in stable,
            })
        result[key] = rows
    return result


# --- meta --------------------------------------------------------------

def union_tickers(leaders: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Return the sorted tickers that are in the leaders of any window."""
    return sorted({row["ticker"] for rows in leaders.values()
                   for row in rows})


def build_meta(as_of: str, leaders: dict[str, list[dict[str, Any]]],
               last_prices: dict[str, float]) -> dict[str, Any]:
    """Return the content of meta.json."""
    sector_of = {row["ticker"]: row["sector"]
                 for rows in leaders.values() for row in rows}
    tickers = union_tickers(leaders)
    return {
        "asOf": as_of,
        "universe": "sp500",
        "riskFree": RISK_FREE,
        "tradingDays": TRADING_DAYS,
        "windows": [{"key": key, "days": days, "effect": effect,
                     "label": label}
                    for key, days, label, effect in WINDOW_TABLE],
        "sectors": sorted(set(sector_of.values())),
        "tickers": [{"ticker": t, "sector": sector_of[t],
                     "lastPrice": clean(last_prices[t])} for t in tickers],
        "benchmark": BENCHMARK,
    }


# --- returns -----------------------------------------------------------

def build_returns(returns: pd.DataFrame, tickers: list[str],
                  n_days: int = RETURNS_DAYS) -> dict[str, Any]:
    """Return the content of returns.json: the last `n_days` of returns."""
    tail = returns.tail(n_days)
    return {
        "dates": [date_text(d) for d in tail.index],
        "series": {t: clean_list(tail[t].to_numpy()) for t in tickers},
    }


# --- ichimoku ----------------------------------------------------------

def midpoint(high: pd.Series, low: pd.Series, length: int) -> pd.Series:
    """Return the midpoint of the highest high and the lowest low."""
    return (high.rolling(length).max() + low.rolling(length).min()) / 2


def move_ahead(values: np.ndarray, shift: int) -> np.ndarray:
    """Move a series `shift` places ahead and add `shift` future places.

    The result is `shift` places longer. The first `shift` places are NaN.
    """
    return np.concatenate([np.full(shift, np.nan), values])


def build_ichimoku(ticker: str, prices: pd.DataFrame,
                   n_days: int = ICHIMOKU_DAYS) -> dict[str, Any]:
    """Return the content of ichimoku/<TICKER>.json.

    `prices` has the columns price_date, high, low and close. Give it
    enough history before the first shown date (about 80 more days).

    The lines follow dbt/models/intermediate/int_ichimoku.sql:
      conversion  midpoint of 9 days; base  midpoint of 26 days.
      spanA       the mean of those two lines, moved 26 days ahead.
      spanB       the midpoint of 52 days, moved 26 days ahead.
      lagging     the close, moved 26 days back (null for the last 26).
    The spans are already moved. The output adds 26 future dates (next
    business days) where only the spans have values.
    """
    prices = prices.sort_values("price_date").reset_index(drop=True)
    high, low, close = prices["high"], prices["low"], prices["close"]
    conversion = midpoint(high, low, 9)
    base = midpoint(high, low, 26)
    span_b_raw = midpoint(high, low, 52)
    span_a_raw = (conversion + base) / 2

    size = len(prices)
    span_a = move_ahead(span_a_raw.to_numpy(), DISPLACEMENT)
    span_b = move_ahead(span_b_raw.to_numpy(), DISPLACEMENT)
    lagging = close.shift(-DISPLACEMENT).to_numpy()

    start = size - n_days
    last_date = prices["price_date"].iloc[-1]
    future = pd.bdate_range(last_date + pd.Timedelta(days=1),
                            periods=DISPLACEMENT)
    pad = np.full(DISPLACEMENT, np.nan)

    def real(values: np.ndarray) -> np.ndarray:
        return np.concatenate([values[start:size], pad])

    dates = list(prices["price_date"].iloc[start:]) + list(future)
    span_a_out = span_a[start:size + DISPLACEMENT]
    span_b_out = span_b[start:size + DISPLACEMENT]

    last = size - 1
    cloud_top = np.nanmax([span_a[last], span_b[last]]) \
        if not (np.isnan(span_a[last]) and np.isnan(span_b[last])) else np.nan
    signals = {
        "priceAboveCloud": bool(close.iloc[last] > cloud_top),
        "conversionAboveBase": bool(conversion.iloc[last] > base.iloc[last]),
        # The close today against the close 26 days ago.
        "laggingAbovePrice": bool(close.iloc[last]
                                  > close.iloc[last - DISPLACEMENT]),
    }
    return {
        "ticker": ticker,
        "dates": [date_text(d) for d in dates],
        "close": clean_list(real(close.to_numpy())),
        "conversion": clean_list(real(conversion.to_numpy())),
        "base": clean_list(real(base.to_numpy())),
        "spanA": clean_list(span_a_out),
        "spanB": clean_list(span_b_out),
        "lagging": clean_list(real(lagging)),
        "score": int(sum(signals.values())),
        "signals": signals,
    }


# --- scorecard ---------------------------------------------------------

def null_value(null: pd.DataFrame, measure: str) -> float | None:
    """Return the null median of one measure, or None when it is missing."""
    rows = null[null["measure"] == measure]
    if rows.empty:
        return None
    return clean(rows["null_median"].iloc[0])


def window_measures(windows: pd.DataFrame) -> dict[str, float | None]:
    """Summarize one table of walk-forward windows against the benchmark."""
    if windows.empty:
        return {"meanSharpe": None, "medianExcess": None,
                "winReturn": None, "winSharpe": None}
    excess = windows["portfolio_return"] - windows["benchmark_return"]
    return {
        "meanSharpe": clean(windows["portfolio_sharpe"].mean()),
        "medianExcess": clean(excess.median()),
        "winReturn": clean((excess > 0).mean()),
        "winSharpe": clean((windows["portfolio_sharpe"]
                            > windows["benchmark_sharpe"]).mean()),
    }


def build_scorecard(windows: pd.DataFrame, equal_windows: pd.DataFrame,
                    null: pd.DataFrame, in_sample_sharpe: float | None,
                    hold_days: int = SCORECARD_HOLD_DAYS) -> dict[str, Any]:
    """Return the content of scorecard.json.

    Each figure comes from an output file of run_pipeline.py. The
    optimizer rows come from walk_forward_windows.csv. The equal-weight
    rows come from a run with the equal_weight objective on the same
    dates. The random-order row comes from null_comparison.csv.
    """
    ordered = windows.sort_values("selection_date")
    per_window = [{
        "date": date_text(r.selection_date),
        "portfolioReturn": clean(r.portfolio_return),
        "benchmarkReturn": clean(r.benchmark_return),
        "portfolioSharpe": clean(r.portfolio_sharpe),
        "benchmarkSharpe": clean(r.benchmark_sharpe),
    } for r in ordered.itertuples()]

    optimizer = window_measures(windows)
    spy_sharpe = (clean(windows["benchmark_sharpe"].mean())
                  if not windows.empty else None)
    rows = [
        {"name": "Optimizer", **optimizer,
         "note": "The default method: 10 stocks, Monte Carlo weights for "
                 "the highest Sharpe ratio."},
        {"name": "Equal weight", **window_measures(equal_windows),
         "note": "The same 10 stocks on the same dates, each with one "
                 "tenth of the money."},
        {"name": "SPY", "meanSharpe": spy_sharpe,
         "medianExcess": None, "winReturn": None, "winSharpe": None,
         "note": "The benchmark over the same windows."},
        {"name": "Random order",
         "meanSharpe": null_value(null, "mean_sharpe"),
         "medianExcess": null_value(null, "median_excess"),
         "winReturn": null_value(null, "win_return"),
         "winSharpe": null_value(null, "win_sharpe"),
         "note": "The median of 200 runs that pick the same candidates "
                 "in a random order."},
    ]
    return {
        "windows": len(per_window),
        "holdDays": hold_days,
        "inSampleSharpe": clean(in_sample_sharpe),
        "realizedSharpe": optimizer["meanSharpe"],
        "rows": rows,
        "perWindow": per_window,
    }



# --- warehouse readers (not tested; they need the warehouse) -----------

def read_current_members(con: Any, as_of: str) -> dict[str, str]:
    """Return {ticker: sector} for the S&P 500 members on the last date."""
    frame = con.execute(
        """
        select d.ticker, d.sector
        from main.dim_ticker as d
        join main.stg_membership as m using (ticker)
        where m.start_date <= ? and (m.end_date is null or m.end_date > ?)
        """, [as_of, as_of]).fetchdf()
    return dict(zip(frame["ticker"], frame["sector"]))


def read_wide_returns(con: Any, tickers: list[str],
                      dates: list[Any]) -> pd.DataFrame:
    """Return a wide returns frame for the tickers on the given dates."""
    frame = con.execute(
        """
        select ticker, price_date, daily_return
        from main.mart_daily_returns
        where price_date >= ? and ticker in (select unnest(?))
        """, [min(dates), tickers]).fetchdf()
    wide = frame.pivot(index="price_date", columns="ticker",
                       values="daily_return")
    wide.index = pd.to_datetime(wide.index)
    return wide.reindex(pd.to_datetime(dates)).sort_index()


def read_last_prices(con: Any, tickers: list[str]) -> dict[str, float]:
    """Return the latest close of each ticker."""
    frame = con.execute(
        """
        select ticker, close from main.stg_prices
        qualify row_number() over (partition by ticker
                                   order by price_date desc) = 1
        """).fetchdf()
    prices = dict(zip(frame["ticker"], frame["close"]))
    return {t: prices[t] for t in tickers}


def read_ohlc(con: Any, tickers: list[str], since: Any) -> pd.DataFrame:
    """Return high, low and close for the tickers from `since` on."""
    frame = con.execute(
        """
        select ticker, price_date, high, low, close
        from main.stg_prices
        where price_date >= ? and ticker in (select unnest(?))
        order by ticker, price_date
        """, [since, tickers]).fetchdf()
    frame["price_date"] = pd.to_datetime(frame["price_date"])
    return frame


def main(out_dir: Path = WEB_DATA_DIR) -> None:
    """Read the warehouse and write all the JSON files."""
    from quant import warehouse

    con = warehouse.connect(read_only=True)
    spy_dates = con.execute(
        "select price_date from main.stg_prices where ticker = ? "
        "order by price_date desc limit ?",
        [BENCHMARK, max(WINDOW_DAYS.values()) + 1]).fetchdf()["price_date"]
    dates = sorted(pd.to_datetime(spy_dates))
    as_of = date_text(dates[-1])

    sectors = read_current_members(con, as_of)
    members = sorted(sectors)
    wide = read_wide_returns(con, members + [BENCHMARK], dates)
    # The first date has no return. The window needs only the returns.
    leaders = build_leaders(wide[members], sectors)
    tickers = union_tickers(leaders)

    meta = build_meta(as_of, leaders, read_last_prices(con, tickers))
    write_json(out_dir / "meta.json", meta)
    write_json(out_dir / "leaders.json", leaders)
    write_json(out_dir / "returns.json",
               build_returns(wide, tickers + [BENCHMARK]))

    since = dates[-(ICHIMOKU_DAYS + 90)]
    ohlc = read_ohlc(con, tickers, since)
    for ticker, prices in ohlc.groupby("ticker"):
        write_json(out_dir / "ichimoku" / f"{ticker}.json",
                   build_ichimoku(ticker, prices))
    con.close()

    windows = pd.read_csv(OUTPUT_DIR / "walk_forward_windows.csv")
    equal = pd.read_csv(OUTPUT_DIR / "walk_forward_windows_equal.csv")
    null = pd.read_csv(OUTPUT_DIR / "null_comparison.csv")
    # The in-sample figure is the best Sharpe ratio of the live search.
    frontier = pd.read_csv(OUTPUT_DIR / "efficient_frontier.csv")
    write_json(out_dir / "scorecard.json", build_scorecard(
        windows, equal, null, frontier["sharpe"].max()))
    print(f"Wrote {len(tickers)} tickers as of {as_of} to {out_dir}.")


if __name__ == "__main__":
    main()
