"""Verify the pipeline against an independent calculation.

This script does not trust the dbt models or the Python stats. It rebuilds
the numbers a second way with pandas, then compares the two. It also scans
for split artifacts and makes sure that the build step does not use future data.

Run it after a dbt build:

    cd quant_pipeline
    . .venv/bin/activate
    python verify_indicators.py

The script prints a PASS or FAIL line for each check. It exits with a
non-zero code when any check fails, so a script or a CI job can use it.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd
import yaml

import run_pipeline
from quant import backtest, pipeline, universe, warehouse

# Read the screen settings from the dbt project, so the two sides agree.
with open(warehouse.DEFAULT_WAREHOUSE.parent / "dbt_project.yml") as _handle:
    DBT_VARS = yaml.safe_load(_handle)["vars"]

# How close two numbers must be to count as equal.
ATOL = 1e-6
# A one-day move larger than this limit must be in the corporate_actions seed.
LARGE_MOVE_LIMIT = DBT_VARS["large_move_review_limit"]

# The raw price file and the seed folder of the dbt project.
PRICES_FILE = warehouse.DEFAULT_WAREHOUSE.parents[1] / "data" / "raw_prices.parquet"
SEEDS_DIR = warehouse.DEFAULT_WAREHOUSE.parent / "seeds"


def screen_rank_column(metric: str) -> str:
    """Return the column that ranks the stocks inside each sector.

    The dbt variable `rank_metric` selects it, and the rank_column macro
    makes the same choice in SQL. Raise ValueError for an unknown value. A
    silent default would make this script compare dbt against a rule that
    nobody asked for, and the check would still report PASS.
    """
    if metric == "cum_return":
        return "cum_return"
    if metric == "sharpe":
        return "sharpe"
    raise ValueError(
        f"rank_metric must be 'cum_return' or 'sharpe', not {metric!r}")


def read_seed(name: str) -> pd.DataFrame:
    """Read a dbt seed file directly, not through dbt."""
    return pd.read_csv(SEEDS_DIR / f"{name}.csv")


# Collect the names of the checks that fail.
FAILURES: list[str] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    """Print one result line and remember a failure."""
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}{(' - ' + detail) if detail else ''}")
    if not passed:
        FAILURES.append(name)


def max_abs_diff(mine: pd.Series, theirs: pd.Series) -> float:
    """Compare two series where my value is not null.

    My pandas value is null until the window is full. On the other days, both
    values use a full window, so the two values must agree.
    """
    mask = mine.notna()
    aligned = theirs.reindex(mine.index)
    return float((mine[mask] - aligned[mask]).abs().max())


# ---------------------------------------------------------------------------
# Load the warehouse once.
# ---------------------------------------------------------------------------

def load_tables(con) -> dict[str, pd.DataFrame]:
    """Read every table the checks need."""
    read = lambda sql: con.execute(sql).fetchdf()
    return {
        "prices": read("select ticker, price_date, high, low, close, volume "
                       "from main.stg_prices order by ticker, price_date"),
        "returns": read("select ticker, price_date, daily_return "
                        "from main.int_daily_returns"),
        "cumulative": read("select ticker, price_date, cum_return "
                           "from main.int_cumulative_returns"),
        "bollinger": read("select ticker, price_date, middle_band, upper_band, "
                          "lower_band from main.int_bollinger"),
        "ichimoku": read("select ticker, price_date, conversion_line, base_line, "
                         "span_a, span_b, lagging_line from main.int_ichimoku"),
        "risk": read("select * from main.int_risk_metrics"),
        "membership": read("select ticker, start_date, end_date "
                           "from main.stg_membership"),
    }


# ---------------------------------------------------------------------------
# Independent pandas recomputation per ticker.
# ---------------------------------------------------------------------------

def exact_rolling_mean_std(series: pd.Series,
                           window: int) -> tuple[pd.Series, pd.Series]:
    """Return the mean and the sample std of each full window, exactly."""
    values = series.to_numpy(dtype=float)
    mean = np.full(len(values), np.nan)
    std = np.full(len(values), np.nan)
    if len(values) >= window:
        windows = np.lib.stride_tricks.sliding_window_view(values, window)
        mean[window - 1:] = windows.mean(axis=1)
        std[window - 1:] = windows.std(axis=1, ddof=1)
    return (pd.Series(mean, index=series.index),
            pd.Series(std, index=series.index))


def pandas_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Rebuild the indicators for one ticker with pandas."""
    p = prices.sort_values("price_date").set_index("price_date").copy()
    close, high, low = p["close"], p["high"], p["low"]

    # A large move stays. The prices are already back-adjusted.
    p["ret"] = close.pct_change()

    # Bollinger Bands need a full 20-day window. Calculate each window
    # directly. The pandas rolling std uses a running sum, and a very large
    # price makes that sum drift.
    mb, sd = exact_rolling_mean_std(close, 20)
    p["mb"], p["ub"], p["lb"] = mb, mb + 2 * sd, mb - 2 * sd

    # Ichimoku lines.
    conv = (high.rolling(9).max() + low.rolling(9).min()) / 2
    base = (high.rolling(26).max() + low.rolling(26).min()) / 2
    span_b_raw = (high.rolling(52).max() + low.rolling(52).min()) / 2
    p["conv"], p["base"] = conv, base
    p["span_a"] = ((conv + base) / 2).shift(26)
    p["span_b"] = span_b_raw.shift(26)
    p["lagging"] = close.shift(-26)
    return p


def verify_indicators(tables: dict[str, pd.DataFrame]) -> None:
    """Compare the pandas indicators to the dbt indicators for every stock."""
    tickers = sorted(tables["prices"]["ticker"].unique())
    worst = {"ret": 0.0, "bollinger": 0.0, "ichimoku": 0.0, "cum": 0.0}

    def by_ticker(name: str, tk: str) -> pd.DataFrame:
        frame = tables[name]
        return frame[frame["ticker"] == tk].set_index("price_date")

    for tk in tickers:
        mine = pandas_indicators(tables["prices"][tables["prices"]["ticker"] == tk])

        ret = by_ticker("returns", tk)["daily_return"]
        worst["ret"] = max(worst["ret"], max_abs_diff(mine["ret"], ret))

        bb = by_ticker("bollinger", tk)
        worst["bollinger"] = max(
            worst["bollinger"],
            max_abs_diff(mine["mb"], bb["middle_band"]),
            max_abs_diff(mine["ub"], bb["upper_band"]),
        )

        ich = by_ticker("ichimoku", tk)
        worst["ichimoku"] = max(
            worst["ichimoku"],
            max_abs_diff(mine["conv"], ich["conversion_line"]),
            max_abs_diff(mine["span_a"], ich["span_a"]),
            max_abs_diff(mine["lagging"], ich["lagging_line"]),
        )

        # Cumulative return compounds the daily returns a second way.
        cum_mine = (1 + mine["ret"].fillna(0)).cumprod()
        cum = by_ticker("cumulative", tk)["cum_return"]
        worst["cum"] = max(worst["cum"], max_abs_diff(cum_mine, cum))

    check("daily_return matches pandas", worst["ret"] < ATOL,
          f"max diff {worst['ret']:.2e}")
    check("bollinger matches pandas", worst["bollinger"] < 1e-5,
          f"max diff {worst['bollinger']:.2e}")
    check("ichimoku matches pandas", worst["ichimoku"] < 1e-5,
          f"max diff {worst['ichimoku']:.2e}")
    check("cumulative return matches pandas", worst["cum"] < 1e-6,
          f"max diff {worst['cum']:.2e}")


# ---------------------------------------------------------------------------
# Independent risk metrics.
# ---------------------------------------------------------------------------

def verify_risk_metrics(tables: dict[str, pd.DataFrame]) -> None:
    """Rebuild the risk metrics for every stock and compare to dbt."""
    risk = tables["risk"].set_index("ticker")
    worst = 0.0

    for tk in risk.index:
        p = tables["prices"][tables["prices"]["ticker"] == tk].sort_values("price_date")
        raw_return = p["close"].pct_change()
        p = p.assign(ret=raw_return)
        recent = p.dropna(subset=["ret"]).tail(252)
        r = recent["ret"]

        annual_return = r.mean() * 252
        annual_vol = r.std(ddof=1) * math.sqrt(252)
        downside = math.sqrt((r.clip(upper=0) ** 2).mean()) * math.sqrt(252)
        threshold = r.quantile(0.05)
        cvar = r[r <= threshold].mean()
        sharpe = (annual_return - 0.045) / annual_vol
        sortino = (annual_return - 0.045) / downside

        row = risk.loc[tk]
        worst = max(
            worst,
            abs(sharpe - row["sharpe_ratio"]),
            abs(sortino - row["sortino_ratio"]),
            abs(cvar - row["cvar_5"]),
            abs(annual_vol - row["annual_volatility"]),
        )

    check("risk metrics match pandas", worst < ATOL, f"max diff {worst:.2e}")


# ---------------------------------------------------------------------------
# Corporate actions and large moves.
# ---------------------------------------------------------------------------

def verify_price_adjustment(con, tables: dict[str, pd.DataFrame]) -> None:
    """Back-adjust the raw prices with pandas and compare to stg_prices.

    Read the raw Parquet file, not a dbt model. Drop the excluded tickers.
    For each corporate action in the seed, multiply each earlier price by
    the open on the event day divided by the close of the day before.
    """
    raw = con.execute(
        f"select ticker, date as price_date, open, high, low, close "
        f"from read_parquet('{PRICES_FILE}') where close > 0"
    ).fetchdf()
    excluded = set(read_seed("price_data_exclusions")["ticker"])
    raw = raw[~raw["ticker"].isin(excluded)]
    raw["price_date"] = pd.to_datetime(raw["price_date"])
    raw = raw.sort_values(["ticker", "price_date"]).reset_index(drop=True)

    actions = read_seed("corporate_actions")
    actions = actions[actions["kind"] == "corporate_action"]
    factor = pd.Series(1.0, index=raw.index)
    for _, event in actions.iterrows():
        rows = raw[raw["ticker"] == event["ticker"]]
        day = pd.Timestamp(event["date"])
        position = rows.index[rows["price_date"] == day][0]
        gap = raw.loc[position, "open"] / raw.loc[position - 1, "close"]
        factor[rows.index[rows["price_date"] < day]] *= gap
    for column in ("open", "high", "low", "close"):
        raw[column] = raw[column] * factor

    dbt = tables["prices"].set_index(["ticker", "price_date"])
    mine = raw.set_index(["ticker", "price_date"])
    worst = float(((mine["close"] - dbt["close"]).abs() / dbt["close"]).max())
    check("stg_prices matches a pandas back-adjustment of the raw file",
          worst < 1e-12 and len(mine) == len(dbt),
          f"{len(actions)} corporate action(s), max relative diff {worst:.1e}")


def verify_large_moves_reviewed(tables: dict[str, pd.DataFrame]) -> None:
    """Make sure that each large move is in the corporate_actions seed."""
    prices = tables["prices"].sort_values(["ticker", "price_date"])
    prices = prices.assign(ret=prices.groupby("ticker")["close"].pct_change())
    large = prices[prices["ret"].abs() > LARGE_MOVE_LIMIT]
    seed = read_seed("corporate_actions")
    reviewed = set(zip(seed["ticker"], pd.to_datetime(seed["date"])))
    missing = [(r.ticker, r.price_date.date()) for r in large.itertuples()
               if (r.ticker, r.price_date) not in reviewed]
    print(f"      {len(large)} move(s) beyond {LARGE_MOVE_LIMIT:.0%}, "
          f"{len(missing)} not reviewed")
    check("each large move is in the corporate_actions seed", not missing,
          ", ".join(f"{t} {d}" for t, d in missing))


# ---------------------------------------------------------------------------
# Point-in-time screen check.
# ---------------------------------------------------------------------------

def members_on(membership: pd.DataFrame, date: pd.Timestamp) -> set[str]:
    """Return the S&P 500 members on a date. The end date is the first day out."""
    start = pd.to_datetime(membership["start_date"])
    end = pd.to_datetime(membership["end_date"])
    inside = (start <= date) & (end.isna() | (date < end))
    return set(membership.loc[inside, "ticker"])


def pandas_screen_as_of(prices: pd.DataFrame, sector_of: dict[str, str],
                        date: pd.Timestamp,
                        members: set[str] | None = None) -> set[str]:
    """Rebuild the screen on a date with pandas.

    First remove every price after the date. Then calculate each gate from
    the data that is left. Because of this, the screen cannot use future data.

    The rank inside each sector follows the dbt variable `rank_metric`, so
    this check follows the setting instead of a fixed rule. See D22.
    """
    v = DBT_VARS
    past = prices[prices["price_date"] <= date]
    rows = []
    for tk, p in past.groupby("ticker"):
        if tk not in sector_of or (members is not None and tk not in members):
            continue
        mine = pandas_indicators(p)
        # dbt has no metrics row on a date that has no return.
        if pd.isna(mine["ret"].iloc[-1]):
            continue
        recent = mine.dropna(subset=["ret"]).tail(v["analysis_window"])
        r = recent["ret"]
        annual_vol = r.std(ddof=1) * math.sqrt(v["trading_days_per_year"])
        sharpe = ((r.mean() * v["trading_days_per_year"] - v["risk_free_rate"])
                  / annual_vol)
        last = mine.iloc[-1]
        score = (int(last["close"] > last["span_a"])
                 + int(last["close"] > last["span_b"])
                 + int(last["conv"] > last["base"])
                 + int(last["span_a"] > last["span_b"])
                 + int(last["close"] > last["base"]))
        # The compound return of the same window. dbt computes
        # cum_return_window with exp(sum(ln(1 + r))) - 1 over this window.
        cum_return = float((1.0 + r).prod() - 1.0)
        rows.append({"ticker": tk, "sector": sector_of[tk], "sharpe": sharpe,
                     "cum_return": cum_return,
                     "passed": len(p) >= v["min_trading_days"]
                     and recent["volume"].mean() >= v["min_avg_volume"]
                     and r.std(ddof=1) <= v["max_daily_volatility"]
                     and score >= v["min_ichimoku_score"]})
    frame = pd.DataFrame(rows)
    rank_on = screen_rank_column(v["rank_metric"])
    frame = frame[frame["passed"]].sort_values(rank_on, ascending=False)
    top = frame.groupby("sector").head(v["top_n_per_sector"])
    return set(top["ticker"])


def verify_screen_history(con, tables: dict[str, pd.DataFrame]) -> None:
    """Compare the screen history to a pandas screen on truncated data."""
    returns, history = run_pipeline.load_backtest_inputs(con)
    sector_of = warehouse.read_sector_map(con)
    today = set(warehouse.read_candidates(con)["ticker"])
    dates = run_pipeline.choose_selection_dates(returns.index)

    all_match = True
    for date in dates:
        dbt_screen = set(pipeline.candidates_as_of(history, date))
        mine = pandas_screen_as_of(tables["prices"], sector_of, date,
                                   members_on(tables["membership"], date))
        all_match = all_match and dbt_screen == mine
        print(f"      {date.date()}: {len(dbt_screen)} stocks pass, "
              f"{len(dbt_screen ^ mine)} differ from pandas, "
              f"{len(dbt_screen ^ today)} differ from today's screen")
    check("screen history matches a pandas screen on truncated data",
          all_match and len(dates) > 0, f"{len(dates)} selection dates")


# ---------------------------------------------------------------------------
# Portfolio stats cross-check.
# ---------------------------------------------------------------------------

def verify_portfolio_stats(con) -> None:
    """Rebuild the optimizer's own numbers a second way."""
    candidates = warehouse.read_candidates(con)
    returns = warehouse.read_returns_matrix(con, candidates["ticker"].tolist())
    # Take the last 252 rows here without the pipeline helper.
    recent = returns.tail(252).dropna(axis=1)

    params = pipeline.PortfolioParams(n_portfolios=3000, seed=42)
    result = run_pipeline.build_live_portfolio(con, params)
    weights = result["weights"]
    selected = result["selected"]

    # The weights must sum to 1.
    check("portfolio weights sum to 1", abs(sum(weights.values()) - 1.0) < 1e-9,
          f"sum {sum(weights.values()):.6f}")

    # Rebuild the Sharpe ratio straight from the returns.
    w = np.array([weights[t] for t in selected])
    sub = recent[selected]
    annual_return = float(sub.mean().to_numpy() @ w * 252)
    annual_vol = float(math.sqrt(w @ sub.cov().to_numpy() @ w * 252))
    sharpe = (annual_return - 0.045) / annual_vol
    check("reported Sharpe matches an independent calc",
          abs(sharpe - result["sharpe"]) < 1e-9,
          f"reported {result['sharpe']:.4f} vs {sharpe:.4f}")


# ---------------------------------------------------------------------------
# No-look-ahead adversarial check.
# ---------------------------------------------------------------------------

def verify_no_look_ahead(con) -> None:
    """Prove that future returns cannot change the weights of a past build."""
    sector_of = warehouse.read_sector_map(con)
    returns, history = run_pipeline.load_backtest_inputs(con)
    params = pipeline.PortfolioParams(n_portfolios=1500, seed=42)
    build = pipeline.make_builder(sector_of, params, universe.BENCHMARK,
                                  screen_history=history)

    selection_date = returns.index[-(backtest_holding() + 1)]
    base = backtest.backtest_window(returns, selection_date, backtest_holding(),
                                    build, universe.BENCHMARK)["weights"]

    # Put absurd returns on every day after the selection date.
    tampered = returns.copy()
    future = tampered.index > selection_date
    tampered.loc[future, :] = 5.0
    tamper = backtest.backtest_window(tampered, selection_date, backtest_holding(),
                                      build, universe.BENCHMARK)["weights"]

    check("future data does not change past selection", base == tamper,
          f"{len(base)} weights identical")


def backtest_holding() -> int:
    """Return the holding period of the backtest."""
    return run_pipeline.HOLDING_PERIOD


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main() -> int:
    """Run every check and return an exit code."""
    if not warehouse.DEFAULT_WAREHOUSE.exists():
        print("No warehouse found. Run 'dbt build --profiles-dir .' first.")
        return 1

    con = warehouse.connect()
    tables = load_tables(con)

    print("== Indicator checks ==")
    verify_indicators(tables)
    verify_risk_metrics(tables)
    print("\n== Data quality ==")
    verify_price_adjustment(con, tables)
    verify_large_moves_reviewed(tables)
    print("\n== Point-in-time screen ==")
    verify_screen_history(con, tables)
    print("\n== Stats checks ==")
    verify_portfolio_stats(con)
    verify_no_look_ahead(con)
    con.close()

    print("\n== Summary ==")
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All checks PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
