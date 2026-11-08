"""Tests for the exact portfolio optimizers (D29).

These tests use small inputs. You can check each answer by hand or with a
brute-force search over a fine grid of weights.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest

from quant import exact, optimize


def _returns(seed: int = 1, days: int = 300, n: int = 4) -> pd.DataFrame:
    """Make a small return frame with different means and volatilities."""
    rng = np.random.default_rng(seed)
    means = np.linspace(0.0002, 0.0012, n)
    vols = np.linspace(0.008, 0.025, n)
    data = rng.normal(means, vols, size=(days, n))
    columns = [f"S{i}" for i in range(n)]
    return pd.DataFrame(data, columns=columns,
                        index=pd.bdate_range("2023-01-02", periods=days))


# --- the bounds ------------------------------------------------------------

def test_bounds_that_cannot_sum_to_one_from_below_raise():
    # 10 stocks at a minimum of 15% need 150% of the money.
    with pytest.raises(ValueError, match="min_weight"):
        exact.check_bounds(10, 0.15, 0.25)


def test_bounds_that_cannot_sum_to_one_from_above_raise():
    # 3 stocks at a maximum of 25% hold only 75% of the money.
    with pytest.raises(ValueError, match="max_weight"):
        exact.check_bounds(3, 0.0, 0.25)


def test_bounds_that_sum_to_exactly_one_are_feasible():
    exact.check_bounds(4, 0.0, 0.25)
    exact.check_bounds(50, 0.02, 0.25)


def test_a_minimum_above_the_maximum_raises():
    with pytest.raises(ValueError):
        exact.check_bounds(4, 0.3, 0.2)


def test_the_solvers_check_the_bounds():
    returns = _returns(n=3)
    for objective in exact.OBJECTIVES:
        with pytest.raises(ValueError, match="max_weight"):
            exact.solve(returns, objective, 0.0, 0.25)


def test_an_unknown_objective_raises():
    with pytest.raises(ValueError, match="objective"):
        exact.solve(_returns(), "max_return", 0.0, 1.0)


# --- min_variance ----------------------------------------------------------

def test_min_variance_of_two_assets_matches_the_formula():
    # For two assets, w1 = (s2^2 - s12) / (s1^2 + s2^2 - 2 s12).
    returns = _returns(seed=3, n=2)
    cov = returns.cov().to_numpy()
    s1, s2, s12 = cov[0, 0], cov[1, 1], cov[0, 1]
    expected = (s2 - s12) / (s1 + s2 - 2 * s12)

    result = exact.solve(returns, "min_variance", 0.0, 1.0)
    assert result["weights"]["S0"] == pytest.approx(expected, abs=1e-6)
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-9)


def test_min_variance_of_three_uncorrelated_assets_is_inverse_variance():
    # With no correlation, the weight is proportional to 1 / variance.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.0, 1.0)
    inverse = 1.0 / np.diag(cov)
    np.testing.assert_allclose(weights, inverse / inverse.sum(), atol=1e-6)


def test_min_variance_holds_a_binding_maximum():
    # The calm asset wants 36/49 of the money alone. A cap of 50% binds.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.0, 0.5)
    assert weights[0] == pytest.approx(0.5, abs=1e-6)
    # The other two split the rest in proportion to 1 / variance.
    assert weights[1] / weights[2] == pytest.approx(9.0 / 4.0, rel=1e-4)


def test_min_variance_holds_a_binding_minimum():
    # The wild asset wants 4/49 of the money. A floor of 20% binds.
    cov = np.diag([1.0, 4.0, 9.0]) * 1e-4
    weights = exact.min_variance_weights(cov, 0.2, 1.0)
    assert weights[2] == pytest.approx(0.2, abs=1e-6)
    assert weights.min() >= 0.2 - 1e-9


# --- max_sharpe ------------------------------------------------------------

def _grid(n: int, step: float, low: float, high: float):
    """Give every weighting of n assets on a grid that sums to 1."""
    ticks = np.round(np.arange(low, high + 1e-9, step), 10)
    for head in itertools.product(ticks, repeat=n - 1):
        last = 1.0 - sum(head)
        if low - 1e-9 <= last <= high + 1e-9:
            yield np.array([*head, last])


def _sharpe(w, returns, risk_free=0.045):
    return optimize.portfolio_performance(
        w, returns.mean().to_numpy(), returns.cov().to_numpy(), 252,
        risk_free)[2]


def test_max_sharpe_of_two_assets_matches_the_tangency_formula():
    # With no bound that binds, the tangency weights are proportional to
    # inverse(cov) times the excess return.
    returns = _returns(seed=4, n=2)
    mu = returns.mean().to_numpy() * 252 - 0.045
    cov = returns.cov().to_numpy() * 252
    raw = np.linalg.solve(cov, mu)
    expected = raw / raw.sum()
    assert (expected > 0).all()

    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    got = np.array([result["weights"]["S0"], result["weights"]["S1"]])
    np.testing.assert_allclose(got, expected, atol=1e-5)


def test_max_sharpe_beats_a_fine_grid_with_binding_bounds():
    returns = _returns(seed=7, n=3)
    best = max(_sharpe(w, returns) for w in _grid(3, 0.01, 0.1, 0.5))
    result = exact.solve(returns, "max_sharpe", 0.1, 0.5)
    w = np.array(list(result["weights"].values()))
    assert w.min() >= 0.1 - 1e-9 and w.max() <= 0.5 + 1e-9
    assert result["sharpe"] >= best - 1e-9
    # The grid step is small, so the grid must come close to the optimum.
    assert result["sharpe"] - best < 0.01


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_max_sharpe_matches_or_beats_the_monte_carlo_search(seed):
    # The Monte Carlo search has no bounds, so give the exact solver none.
    returns = _returns(seed=seed, n=6)
    monte_carlo = optimize.optimize_max_sharpe(returns, n_portfolios=5000,
                                               seed=42)
    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    assert result["sharpe"] >= monte_carlo["sharpe"] - 1e-12


def test_max_sharpe_holds_the_default_bounds_on_ten_assets():
    returns = _returns(seed=11, n=10)
    result = exact.solve(returns, "max_sharpe", 0.02, 0.25)
    w = np.array(list(result["weights"].values()))
    assert w.sum() == pytest.approx(1.0, abs=1e-12)
    assert w.min() >= 0.02 - 1e-12
    assert w.max() <= 0.25 + 1e-12


def test_max_sharpe_works_when_every_asset_loses_to_cash():
    # Every excess return is negative, so the best Sharpe ratio is
    # negative too. The convex reformulation needs a positive one, so the
    # solver must still find the best weights another way.
    returns = _returns(seed=13, n=3) - 0.003
    best = max(_sharpe(w, returns) for w in _grid(3, 0.01, 0.0, 1.0))
    assert best < 0
    result = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    assert result["sharpe"] >= best - 1e-9


def test_the_reported_sharpe_matches_the_weights():
    returns = _returns(seed=17, n=5)
    result = exact.solve(returns, "max_sharpe", 0.05, 0.4)
    w = np.array([result["weights"][t] for t in returns.columns])
    assert result["sharpe"] == pytest.approx(_sharpe(w, returns), rel=1e-12)


def test_the_convex_reformulation_alone_beats_a_fine_grid():
    # Four assets with a cap of 40%. The cap binds on one asset, and the
    # other three weights are inside the bounds. The reformulation must
    # find the optimum without the help of the direct search.
    returns = _returns(seed=3, n=4)
    excess, cov = exact._annual_inputs(returns, 0.045, 252)
    weights = exact._tangency_by_reformulation(excess, cov, 0.05, 0.4)
    best = max(_sharpe(w, returns) for w in _grid(4, 0.01, 0.05, 0.4))
    assert weights.max() == pytest.approx(0.4, abs=1e-7)
    assert weights.min() >= 0.05 - 1e-12
    assert _sharpe(weights, returns) >= best - 1e-9
    assert _sharpe(weights, returns) - best < 0.01


def test_the_convex_reformulation_gives_none_when_every_asset_loses():
    returns = _returns(seed=13, n=3) - 0.003
    excess, cov = exact._annual_inputs(returns, 0.045, 252)
    assert exact._tangency_by_reformulation(excess, cov, 0.0, 1.0) is None


# --- max_sortino -----------------------------------------------------------

def test_sortino_ratio_matches_a_hand_calculation():
    # Four days. The daily target is 0.0252 / 252 = 0.0001.
    daily = np.array([0.0101, -0.0099, 0.0001, -0.0199])
    target = 0.0001
    shortfall = np.array([0.0, -0.01, 0.0, -0.02])
    downside = math.sqrt((shortfall ** 2).mean()) * math.sqrt(252)
    expected = (daily.mean() * 252 - 0.0252) / downside
    assert exact.sortino_ratio(daily, 0.0252, 252) == pytest.approx(expected)
    assert target == pytest.approx(0.0252 / 252)


def test_max_sortino_beats_a_fine_grid():
    returns = _returns(seed=3, n=3)
    risk_free = 0.045

    def sortino(w):
        return exact.sortino_ratio(returns.to_numpy() @ w, risk_free, 252)

    best = max(sortino(w) for w in _grid(3, 0.01, 0.05, 0.6))
    result = exact.solve(returns, "max_sortino", 0.05, 0.6)
    w = np.array([result["weights"][t] for t in returns.columns])
    assert w.min() >= 0.05 - 1e-12 and w.max() <= 0.6 + 1e-12
    assert sortino(w) >= best - 1e-9
    assert sortino(w) - best < 0.02
    assert result["sortino"] == pytest.approx(sortino(w))


def test_max_sortino_is_not_max_sharpe():
    # A skewed asset has a small downside and a large upside. The Sortino
    # ratio likes it more than the Sharpe ratio does.
    rng = np.random.default_rng(0)
    days = 400
    calm = rng.normal(0.0006, 0.01, days)
    skewed = np.where(rng.random(days) < 0.1, 0.06, -0.002)
    third = rng.normal(0.0004, 0.012, days)
    returns = pd.DataFrame({"CALM": calm, "SKEW": skewed, "THIRD": third})
    sharpe = exact.solve(returns, "max_sharpe", 0.0, 1.0)
    sortino = exact.solve(returns, "max_sortino", 0.0, 1.0)
    assert sortino["weights"]["SKEW"] > sharpe["weights"]["SKEW"] + 0.01


# --- min_cvar --------------------------------------------------------------

def test_cvar_5_follows_the_dbt_convention():
    # int_risk_metrics takes the linear 5% quantile of the daily returns,
    # then the mean of the returns at or below it. With 40 days the
    # quantile sits between the 2nd and 3rd worst day, so the two worst
    # days count.
    daily = np.linspace(-0.05, 0.05, 40)
    expected = daily[:2].mean()
    assert exact.cvar_5(daily) == pytest.approx(expected)


def _worst_mean(scenarios, w, k):
    """Give the mean return of the k worst days of a portfolio."""
    return np.sort(scenarios @ w)[:k].mean()


def test_min_cvar_matches_a_brute_force_search():
    # 40 scenarios at 5% means the two worst days.
    returns = _returns(seed=21, days=40, n=3)
    scenarios = returns.to_numpy()
    best = max(_worst_mean(scenarios, w, 2)
               for w in _grid(3, 0.01, 0.0, 1.0))
    result = exact.solve(returns, "min_cvar", 0.0, 1.0)
    w = np.array([result["weights"][t] for t in returns.columns])
    assert _worst_mean(scenarios, w, 2) >= best - 1e-9
    assert result["cvar_5"] == pytest.approx(exact.cvar_5(scenarios @ w))


def test_min_cvar_holds_a_binding_maximum():
    returns = _returns(seed=21, days=40, n=3)
    free = exact.solve(returns, "min_cvar", 0.0, 1.0)
    cap = max(free["weights"].values()) - 0.1
    capped = exact.solve(returns, "min_cvar", 0.0, cap)
    assert max(capped["weights"].values()) == pytest.approx(cap, abs=1e-9)
    scenarios = returns.to_numpy()
    best = max(_worst_mean(scenarios, w, 2)
               for w in _grid(3, 0.01, 0.0, cap))
    w = np.array([capped["weights"][t] for t in returns.columns])
    assert _worst_mean(scenarios, w, 2) >= best - 1e-9


def test_the_tail_count_follows_the_linear_quantile():
    # The linear quantile at 5% sits at position 0.05 * (T - 1). Every day
    # up to and on that position counts.
    assert exact.tail_count(252) == 13
    assert exact.tail_count(40) == 2
    assert exact.tail_count(30) == 2
    assert exact.tail_count(21) == 2
    assert exact.tail_count(20) == 1


def test_min_cvar_weights_minimize_the_mean_of_the_worst_days():
    # 30 scenarios: dbt averages the 2 worst days. The Rockafellar-Uryasev
    # program with a tail of 2 / 30 minimizes that mean.
    rng = np.random.default_rng(4)
    scenarios = rng.normal(0.0, 0.02, size=(30, 3))

    def worst_two(w):
        return np.sort(scenarios @ w)[:2].mean()

    best = max(worst_two(w) for w in _grid(3, 0.01, 0.0, 1.0))
    weights = exact.min_cvar_weights(scenarios, 0.0, 1.0)
    assert worst_two(weights) >= best - 1e-9
    # The optimum often puts two days at the same loss on the VaR point.
    # The dbt formula then counts every tied day, so its value can be
    # above the mean of the 2 worst days. It is never below it.
    assert exact.cvar_5(scenarios @ weights) >= worst_two(weights) - 1e-12


# --- prune_pool (option B: the optimizer picks the count) -------------------

class FakeSolver:
    """Give fixed weights for each set of tickers, and record each call."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def __call__(self, returns, low, high):
        key = frozenset(returns.columns)
        self.calls.append((tuple(sorted(key)), low, high))
        weights = self.table[(key, low)]
        return {"weights": dict(weights), "sharpe": 1.0}


def _frame(tickers):
    return pd.DataFrame(np.zeros((3, len(tickers))), columns=list(tickers))


def test_prune_pool_drops_the_small_weights_and_solves_again():
    pool = "ABCDEF"
    fake = FakeSolver({
        # Round 1 on the pool with a floor of 0: E and F fall below 2%.
        (frozenset(pool), 0.0): {"A": .3, "B": .3, "C": .2, "D": .19,
                                 "E": .01, "F": 0.0},
        # Round 2 on the survivors: every weight stays above 2%.
        (frozenset("ABCD"), 0.0): {"A": .3, "B": .3, "C": .2, "D": .2},
        # The final solve with the full bounds.
        (frozenset("ABCD"), 0.02): {"A": .3, "B": .3, "C": .2, "D": .2},
    })
    result = exact.prune_pool(_frame(pool), fake, 0.02, 0.3)
    assert sorted(result["weights"]) == list("ABCD")
    assert result["pool"] == list(pool)
    assert result["rounds"] == 2
    assert fake.calls == [(tuple(pool), 0.0, 0.3), (tuple("ABCD"), 0.0, 0.3),
                          (tuple("ABCD"), 0.02, 0.3)]


def test_prune_pool_repeats_until_no_weight_falls_below_the_floor():
    pool = "ABCDEF"
    fake = FakeSolver({
        (frozenset(pool), 0.0): {"A": .3, "B": .3, "C": .2, "D": .19,
                                 "E": .01, "F": 0.0},
        # Without E and F, D falls below the floor too.
        (frozenset("ABCD"), 0.0): {"A": .4, "B": .3, "C": .29, "D": .01},
        (frozenset("ABC"), 0.0): {"A": .4, "B": .3, "C": .3},
        (frozenset("ABC"), 0.02): {"A": .4, "B": .3, "C": .3},
    })
    result = exact.prune_pool(_frame(pool), fake, 0.02, 0.4)
    assert sorted(result["weights"]) == list("ABC")
    assert result["rounds"] == 3


def test_prune_pool_adds_back_names_when_too_few_survive():
    # Three names at the cap of 25% hold only 75% of the money. The
    # largest dropped name comes back, so four names can hold it all.
    pool = "ABCDEF"
    fake = FakeSolver({
        (frozenset(pool), 0.0): {"A": .25, "B": .25, "C": .25, "D": .09,
                                 "E": .08, "F": .08},
        (frozenset("ABCD"), 0.0): {"A": .25, "B": .25, "C": .25, "D": .25},
        (frozenset("ABCD"), 0.1): {"A": .25, "B": .25, "C": .25, "D": .25},
    })
    result = exact.prune_pool(_frame(pool), fake, 0.1, 0.25)
    assert sorted(result["weights"]) == list("ABCD")


def test_prune_pool_with_the_real_solver_holds_the_bounds():
    # Two of the eight assets lose money, so the floor of 0 drops them.
    returns = _returns(seed=8, n=8)
    returns["S0"] -= 0.004
    returns["S1"] -= 0.004

    def solver(frame, low, high):
        return exact.solve(frame, "max_sharpe", low, high)

    result = exact.prune_pool(returns, solver, 0.02, 0.4)
    weights = np.array(list(result["weights"].values()))
    assert "S0" not in result["weights"] and "S1" not in result["weights"]
    assert weights.min() >= 0.02 - 1e-12
    assert weights.max() <= 0.4 + 1e-12
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    # The kept set is stable: a floor of 0 drops no more names.
    again = solver(returns[list(result["weights"])], 0.0, 0.4)
    assert min(again["weights"].values()) >= 0.02 - 1e-9


def test_prune_pool_refuses_a_pool_that_the_cap_cannot_fill():
    with pytest.raises(ValueError, match="max_weight"):
        exact.prune_pool(_frame("ABC"), FakeSolver({}), 0.02, 0.25)
