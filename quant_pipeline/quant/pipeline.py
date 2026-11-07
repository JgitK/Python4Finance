"""Compose the selection and the optimization into one portfolio build.

This module joins the small parts into one step. It ranks the stocks by
Sharpe ratio, picks a diversified set, and finds the Max Sharpe weights.
Both the live run and the backtest use the same build step. But the live
run starts from the dbt screen candidates, and the backtest does not apply
the screen gates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from quant import capm, optimize, select_portfolio


@dataclass
class PortfolioParams:
    """The settings for one portfolio build."""

    # The user selected 10 stocks. D20 and D21 measured 10, 12, 24, 40 and
    # 60 stocks. This dataclass is the one place that holds the two caps.
    target_size: int = 10
    max_per_sector: int = 3
    max_avg_correlation: float = 0.6
    risk_free: float = 0.045
    trading_days: int = 252
    n_portfolios: int = 10000
    seed: int = 42
    # The build step uses this many recent rows. The dbt analysis_window
    # has the same value, so the screen and the build use the same year.
    lookback_days: int = 252
    # The measure that ranks the candidates: cum_return or sharpe. The dbt
    # variable rank_metric holds the same choice for the screen, so a
    # change here needs the same change there. See decision D22.
    rank_metric: str = "cum_return"


# The points of the capital allocation line in the live output (D25).
ALLOCATION_FRACTIONS = [0.0, 0.25, 0.5, 0.75, 1.0]


def live_capm(returns: pd.DataFrame, weights: dict[str, float],
              benchmark: str, params: "PortfolioParams",
              tangency_return: float,
              tangency_volatility: float) -> dict[str, Any]:
    """Give the CAPM view of the live portfolio over the lookback window.

    Return a table of beta and alpha for each stock, the same measures for
    the portfolio, the capital allocation line, the volatility of the
    benchmark, and the share of the money in the portfolio that gives the
    volatility of the benchmark. The rest of the money is cash.

    The measures are in-sample. The weights come from the same window.
    """
    tickers = list(weights)
    window = returns[tickers + [benchmark]].tail(params.lookback_days)
    table = capm.capm_table(window, tickers, benchmark, params.risk_free,
                            params.trading_days)
    table.insert(1, "weight", [weights[t] for t in tickers])
    portfolio = capm.portfolio_capm(window, weights, benchmark,
                                    params.risk_free, params.trading_days)
    benchmark_vol = float(window[benchmark].std(ddof=1)
                          * math.sqrt(params.trading_days))
    line = capm.capital_allocation_line(tangency_return, tangency_volatility,
                                        params.risk_free,
                                        ALLOCATION_FRACTIONS)
    return {"table": table, "portfolio": portfolio, "line": line,
            "benchmark_volatility": benchmark_vol,
            "fraction_at_benchmark_risk": capm.fraction_for_volatility(
                tangency_volatility, benchmark_vol)}


def lookback_window(returns: pd.DataFrame,
                    params: PortfolioParams) -> pd.DataFrame:
    """Keep the last lookback_days rows. Drop a stock with a gap in them.

    The live run and the backtest both use this function. Because of this,
    both select and weight the stocks from the same window.
    """
    return returns.tail(params.lookback_days).dropna(axis=1)


def rank_by_sharpe(returns: pd.DataFrame, risk_free: float = 0.045,
                   trading_days: int = 252) -> list[str]:
    """Order the stocks from the highest Sharpe ratio to the lowest."""
    annual_return = returns.mean() * trading_days
    annual_vol = returns.std(ddof=1) * math.sqrt(trading_days)
    sharpe = (annual_return - risk_free) / annual_vol
    return list(sharpe.sort_values(ascending=False).index)


def rank_by_cumulative_return(returns: pd.DataFrame) -> list[str]:
    """Order the stocks from the highest compound return to the lowest.

    The measure is the compound return of the whole frame, so the caller
    must cut the frame to the lookback window first. This measure takes no
    account of the risk. A wild stock that rose can rank above a calm
    stock that rose less.
    """
    compound = (1.0 + returns).prod() - 1.0
    return list(compound.sort_values(ascending=False).index)


def rank_candidates(returns: pd.DataFrame,
                    params: PortfolioParams) -> list[str]:
    """Order the stocks by the rank metric of the settings.

    Raise ValueError for an unknown metric. A silent default would give a
    portfolio that nobody asked for.
    """
    if params.rank_metric == "cum_return":
        return rank_by_cumulative_return(returns)
    if params.rank_metric == "sharpe":
        return rank_by_sharpe(returns, params.risk_free, params.trading_days)
    raise ValueError(
        f"rank_metric must be 'cum_return' or 'sharpe', not "
        f"{params.rank_metric!r}")


def build_max_sharpe_portfolio(returns: pd.DataFrame,
                               sector_of: dict[str, str],
                               params: PortfolioParams | None = None,
                               rng: Any = None
                               ) -> dict[str, Any]:
    """Build one Max Sharpe portfolio from a return matrix.

    Rank the stocks on `params.rank_metric`, pick a diversified set, then
    optimize the weights. The rank decides which stock takes a place of a
    sector. The optimizer then finds the Max Sharpe weights of the stocks
    that the rank selected, so the rank metric and the weight objective
    are two different measures.
    Return an empty result when no stock passes the selection.

    An `rng` replaces the rank order with a random order of the same
    candidates. Every other step stays the same. This is the null
    benchmark of `quant.null_benchmark`, which measures what the rank
    order is worth.
    """
    params = params or PortfolioParams()

    ranked = rank_candidates(returns, params)
    if rng is not None:
        ranked = [str(ticker) for ticker in rng.permutation(ranked)]
    candidates = [
        {"ticker": ticker, "sector": sector_of.get(ticker, "Unknown")}
        for ticker in ranked
    ]
    corr = returns.corr()
    selected = select_portfolio.greedy_low_correlation(
        candidates, corr, params.target_size, params.max_per_sector,
        params.max_avg_correlation,
    )
    if not selected:
        return {"weights": {}, "selected": []}

    result = optimize.optimize_max_sharpe(
        returns[selected], params.n_portfolios, params.risk_free,
        params.trading_days, params.seed,
    )
    result["selected"] = selected
    return result


def candidates_as_of(screen_history: pd.DataFrame, date: Any) -> list[str]:
    """Return the stocks that passed the screen on a date.

    Use the latest screen on or before the date. A later screen is future
    data, so this function does not use it. Return an empty list when no
    screen exists on or before the date.
    """
    cut = pd.Timestamp(date)
    dates = pd.to_datetime(screen_history["as_of_date"])
    past = dates[dates <= cut]
    if past.empty:
        return []
    latest = screen_history[dates == past.max()]
    return sorted(latest["ticker"].tolist())


def make_builder(sector_of: dict[str, str], params: PortfolioParams,
                 benchmark: str,
                 screen_history: pd.DataFrame | None = None,
                 rng: Any = None
                 ) -> Callable[[pd.DataFrame], dict[str, float]]:
    """Make a build_portfolio function for the backtest.

    The function that this returns uses a train frame as input.
    It returns weights by ticker.
    It drops the benchmark first, so the benchmark never enters the portfolio.
    When you supply a screen history, the function uses only the stocks that
    passed the screen on the last day of the train frame.

    An `rng` gives the null benchmark: the same candidates in a random
    order. See `quant.null_benchmark`.
    """
    def build(train: pd.DataFrame) -> dict[str, float]:
        tradeable = train.drop(columns=[benchmark], errors="ignore")
        if screen_history is not None:
            passed = candidates_as_of(screen_history, train.index.max())
            tradeable = tradeable[[t for t in passed if t in tradeable.columns]]
        tradeable = lookback_window(tradeable, params)
        if tradeable.shape[1] == 0:
            return {}
        result = build_max_sharpe_portfolio(tradeable, sector_of, params, rng)
        return result.get("weights", {})

    return build


def sector_mix(selected: list[str],
               sector_of: dict[str, str]) -> dict[str, int]:
    """Count the stocks of each sector in a portfolio.

    The sector cap of the screen also balances the sectors. A change of
    the cap therefore moves the mix. Return the largest sector first, and
    name a stock with no sector "Unknown".
    """
    counts: dict[str, int] = {}
    for ticker in selected:
        sector = sector_of.get(ticker, "Unknown")
        counts[sector] = counts.get(sector, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def coverage_summary(coverage: pd.DataFrame, dates: list[Any]) -> pd.DataFrame:
    """Count the index members that the pipeline drops on each date.

    A member is usable when it has a price and a sector. The screen cannot
    select a member that is not usable. For each date, use the latest
    coverage date on or before it. Return one row for each date.
    """
    covered = pd.to_datetime(coverage["as_of_date"])
    rows = []
    for date in dates:
        cut = pd.Timestamp(date)
        day = covered[covered <= cut].max()
        members = coverage[covered == day]
        usable = members["has_prices"] & members["has_sector"]
        rows.append({
            "date": cut,
            "coverage_date": day,
            "members": int(len(members)),
            "usable": int(usable.sum()),
            "dropped": int((~usable).sum()),
            "dropped_tickers": " ".join(sorted(members.loc[~usable, "ticker"])),
        })
    return pd.DataFrame(rows)
