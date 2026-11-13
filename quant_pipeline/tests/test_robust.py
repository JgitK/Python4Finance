"""Tests for the robust Markowitz objective (D36).

Boyd et al. (2024), "Markowitz Portfolio Construction at Seventy", section
3.5, make the forecasts robust:

- The mean of each stock can be anywhere in mu +- rho. A long-only
  portfolio then earns the worst case (mu - rho)' w.
- The covariance can be anywhere in Sigma + Delta with
  |Delta_ij| <= varrho * sqrt(Sigma_ii * Sigma_jj). For a long-only
  portfolio the worst case is w' (Sigma + varrho * s s') w, where s holds
  the volatilities.

The objective `robust` maximizes the worst-case return. The worst-case
risk must stay at or below the worst-case risk of equal weight on the
same stocks, so the test against equal weight is at the same risk.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import run_pipeline
from quant import exact, pipeline

SECTORS = ["Tech", "Health", "Energy", "Utilities", "Materials", "Finance"]


def _many_stocks(n: int = 12, days: int = 252, seed: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    means = np.linspace(-0.0005, 0.0020, n)
    vols = np.linspace(0.010, 0.030, n)[::-1]
    data = rng.normal(means, vols, size=(days, n))
    columns = [f"T{i:02d}" for i in range(n)]
    return pd.DataFrame(data, columns=columns,
                        index=pd.bdate_range("2023-01-02", periods=days))


def _sectors(returns: pd.DataFrame) -> dict[str, str]:
    return {t: SECTORS[i % len(SECTORS)] for i, t in enumerate(returns)}


def _annual(returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return (returns.mean().to_numpy() * 252,
            returns.cov().to_numpy() * 252)


# --- the uncertainty of the mean ---------------------------------------------

def test_robust_is_an_objective():
    assert "robust" in exact.OBJECTIVES


def test_rho_none_is_zero():
    returns = _many_stocks()
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, n_days=252, rule="none")
    assert np.array_equal(rho, np.zeros(len(mu)))


def test_rho_paper_is_the_20th_percentile_of_the_absolute_mean():
    returns = _many_stocks()
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, n_days=252, rule="paper")
    expected = np.quantile(np.abs(mu), 0.20)
    assert np.allclose(rho, expected, rtol=0, atol=1e-15)


def test_rho_stderr_is_the_standard_error_of_each_annual_mean():
    returns = _many_stocks()
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, n_days=126, rule="stderr")
    vols = np.sqrt(np.diag(cov))
    # 126 days are half a year, so the error is the volatility / sqrt(0.5).
    assert np.allclose(rho, vols / math.sqrt(0.5), rtol=1e-12)


def test_an_unknown_rho_rule_raises():
    mu, cov = _annual(_many_stocks())
    with pytest.raises(ValueError, match="rho_rule"):
        exact.mean_uncertainty(mu, cov, n_days=252, rule="guess")


# --- the uncertainty of the covariance ---------------------------------------

def test_worst_case_variance_matches_the_formula_of_the_paper():
    mu, cov = _annual(_many_stocks())
    rng = np.random.default_rng(0)
    w = rng.random(len(mu))
    w /= w.sum()
    vols = np.sqrt(np.diag(cov))
    # Equation 17: sigma^2 + varrho * (sum of s_i |w_i|)^2.
    expected = w @ cov @ w + 0.02 * (vols @ np.abs(w)) ** 2
    assert exact.worst_case_variance(w, cov, 0.02) == pytest.approx(
        expected, rel=1e-12)


def test_worst_case_variance_with_no_uncertainty_is_the_variance():
    mu, cov = _annual(_many_stocks())
    w = np.full(len(mu), 1 / len(mu))
    assert exact.worst_case_variance(w, cov, 0.0) == pytest.approx(
        w @ cov @ w, rel=1e-12)


# --- the solver --------------------------------------------------------------

@pytest.mark.parametrize("rule,varrho", [("none", 0.0), ("paper", 0.02),
                                         ("stderr", 0.02)])
def test_robust_weights_hold_the_risk_of_equal_weight(rule, varrho):
    returns = _many_stocks()
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, 252, rule)
    w = exact.robust_weights(mu, rho, cov, varrho, 0.0, 0.25)
    n = len(mu)
    ew = np.full(n, 1 / n)
    assert w.sum() == pytest.approx(1.0, abs=1e-12)
    assert w.min() >= -1e-12 and w.max() <= 0.25 + 1e-12
    assert exact.worst_case_variance(w, cov, varrho) <= \
        exact.worst_case_variance(ew, cov, varrho) * (1 + 1e-6)
    # The solver never does worse than its feasible start, equal weight.
    assert (mu - rho) @ w >= (mu - rho) @ ew - 1e-12


def test_robust_weights_tilt_toward_the_better_forecast():
    returns = _many_stocks()
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, 252, "none")
    w = exact.robust_weights(mu, rho, cov, 0.0, 0.0, 0.25)
    ew = np.full(len(mu), 1 / len(mu))
    assert mu @ w > mu @ ew + 0.01


def test_the_worst_case_risk_limit_binds_with_varrho():
    # The signal pushes toward risk, so the limit binds. It must bind on
    # the worst-case variance, not on the nominal variance.
    returns = _many_stocks()
    mu, cov = _annual(returns)
    ew = np.full(len(mu), 1 / len(mu))
    w = exact.robust_weights(mu, np.zeros(len(mu)), cov, 0.2, 0.0, 0.25)
    assert exact.worst_case_variance(w, cov, 0.2) == pytest.approx(
        exact.worst_case_variance(ew, cov, 0.2), rel=1e-5)


def test_a_large_rho_on_one_stock_cuts_its_weight():
    returns = _many_stocks()
    mu, cov = _annual(returns)
    plain = exact.robust_weights(mu, np.zeros(len(mu)), cov, 0.02, 0.0, 0.25)
    top = int(np.argmax(plain))
    rho = np.zeros(len(mu))
    rho[top] = 1.0
    doubtful = exact.robust_weights(mu, rho, cov, 0.02, 0.0, 0.25)
    assert doubtful[top] < plain[top] - 0.05


def test_a_uniform_rho_does_not_change_long_only_weights():
    # (mu - c)' w = mu' w - c when the weights sum to 1. So the rule of
    # the paper only shifts the objective of a long-only portfolio.
    returns = _many_stocks()
    mu, cov = _annual(returns)
    plain = exact.robust_weights(mu, np.zeros(len(mu)), cov, 0.02, 0.0, 0.25)
    shifted = exact.robust_weights(mu, np.full(len(mu), 0.05), cov, 0.02,
                                   0.0, 0.25)
    assert np.allclose(plain, shifted, atol=1e-6)


def test_solve_robust_uses_the_rules_of_the_call():
    returns = _many_stocks()
    result = exact.solve(returns, "robust", 0.02, 0.25, rho_rule="stderr",
                         varrho=0.02)
    mu, cov = _annual(returns)
    rho = exact.mean_uncertainty(mu, cov, len(returns), "stderr")
    direct = exact.robust_weights(mu, rho, cov, 0.02, 0.02, 0.25)
    assert np.allclose(list(result["weights"].values()), direct, atol=1e-12)
    assert result["objective"] == "robust"


# --- the settings ------------------------------------------------------------

def test_the_default_settings_of_the_robust_objective():
    params = pipeline.PortfolioParams()
    assert params.rho_rule == "stderr"
    assert params.varrho == 0.02


@pytest.mark.parametrize("change", [{"rho_rule": "guess"},
                                    {"varrho": -0.01},
                                    {"varrho": 1.0}])
def test_bad_robust_settings_raise(change):
    params = pipeline.PortfolioParams(optimizer="exact", objective="robust",
                                      **change)
    with pytest.raises(ValueError):
        exact.check_settings(params)


def test_the_pool_build_passes_the_robust_settings():
    returns = _many_stocks(n=18)
    params = pipeline.PortfolioParams(optimizer="exact", objective="robust",
                                      size_mode="pool", pool_size=12,
                                      rho_rule="none", varrho=0.0)
    result = pipeline.build_max_sharpe_portfolio(returns, _sectors(returns),
                                                 params)
    kept = list(result["weights"])
    direct = exact.solve(returns[kept], "robust", params.min_weight,
                         params.max_weight, rho_rule="none", varrho=0.0)
    assert result["weights"] == pytest.approx(direct["weights"], abs=1e-9)


def test_the_label_names_the_robust_settings():
    params = pipeline.PortfolioParams(optimizer="exact", objective="robust",
                                      size_mode="pool", pool_size=33,
                                      rho_rule="paper", varrho=0.02)
    assert exact.optimizer_label(params) == \
        "exact robust(rho=paper,varrho=0.02) 2-25% pool33"


def test_the_label_of_another_objective_has_no_robust_settings():
    params = pipeline.PortfolioParams(optimizer="exact",
                                      objective="max_sharpe")
    assert exact.optimizer_label(params) == "exact max_sharpe 2-25% fixed"


def test_the_command_line_sets_the_robust_settings():
    args = run_pipeline.make_parser().parse_args(
        ["--optimizer", "exact", "--objective", "robust",
         "--rho-rule", "none", "--varrho", "0"])
    params = run_pipeline.params_from_args(args)
    assert params.objective == "robust"
    assert params.rho_rule == "none"
    assert params.varrho == 0.0
