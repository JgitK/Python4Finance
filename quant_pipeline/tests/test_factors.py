"""Tests for the momentum factor and the two-factor regression (D30).

The screen ranks the stocks on the trailing compound return. That is the
classic momentum signal. These tests check the tools that separate the
momentum premium from the rest of the alpha.

The regression tests build a portfolio with known loadings. The factor
tests use a tiny price panel. A person can check its long leg and its
short leg by hand.
"""

from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
import pytest

from quant import capm, factors

DAYS = 252
RF = 0.045


def _two_factors(days: int = 600, seed: int = 1) -> tuple[pd.Series, pd.Series]:
    """Give a market series and a momentum series with no relation."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=days)
    market = pd.Series(rng.normal(0.0005, 0.01, days), index=dates)
    umd = pd.Series(rng.normal(0.0003, 0.008, days), index=dates)
    return market, umd


def _portfolio(market: pd.Series, umd: pd.Series, beta: float, loading: float,
               alpha_daily: float, noise_sd: float = 0.0,
               seed: int = 2) -> pd.Series:
    """Build a portfolio: excess = alpha + beta * market excess + loading * UMD."""
    rf_daily = RF / DAYS
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, noise_sd, len(market)) if noise_sd else 0.0
    excess = alpha_daily + beta * (market - rf_daily) + loading * umd + noise
    return excess + rf_daily


# --- regress_two_factor ---------------------------------------------------

def test_regress_two_factor_finds_known_loadings_without_noise():
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=0.3, loading=0.8, alpha_daily=0.0001)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(0.3, abs=1e-10)
    assert result["umd_loading"] == pytest.approx(0.8, abs=1e-10)
    # The annual alpha is the daily intercept times the trading days.
    assert result["alpha"] == pytest.approx(0.0001 * DAYS, abs=1e-10)
    assert result["r_squared"] == pytest.approx(1.0, abs=1e-10)
    assert result["n_days"] == len(market)


def test_regress_two_factor_finds_known_loadings_with_noise():
    market, umd = _two_factors(days=2000)
    port = _portfolio(market, umd, beta=0.3, loading=0.8,
                      alpha_daily=0.0004, noise_sd=0.002)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(0.3, abs=0.03)
    assert result["umd_loading"] == pytest.approx(0.8, abs=0.04)
    # The noise is large against the alpha, so the tolerance is wide. The
    # sign and the size must still be correct.
    assert result["alpha"] == pytest.approx(0.0004 * DAYS, abs=0.05)
    # The t statistic of a loading of 0.8 on 2000 days is very large.
    assert result["umd_t"] > 20
    assert result["r_squared"] < 1.0


def test_regress_two_factor_t_statistic_matches_the_textbook_formula():
    # Compute the standard error with the OLS formula, independently.
    market, umd = _two_factors(days=300, seed=5)
    port = _portfolio(market, umd, beta=1.2, loading=0.2,
                      alpha_daily=0.0, noise_sd=0.01, seed=6)
    rf_daily = RF / DAYS
    y = (port - rf_daily).to_numpy()
    x = np.column_stack([np.ones(len(y)), (market - rf_daily).to_numpy(),
                         umd.to_numpy()])
    coef = np.linalg.solve(x.T @ x, x.T @ y)
    resid = y - x @ coef
    sigma2 = resid @ resid / (len(y) - 3)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(x.T @ x)))
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["umd_t"] == pytest.approx(coef[2] / se[2], rel=1e-9)
    assert result["alpha_t"] == pytest.approx(coef[0] / se[0], rel=1e-9)
    assert result["beta_t"] == pytest.approx(coef[1] / se[1], rel=1e-9)


def test_regress_two_factor_does_not_subtract_the_risk_free_rate_from_umd():
    # UMD is a long-short return. It costs nothing, so it has no risk-free
    # part. A regression that subtracts the rate from UMD moves the alpha
    # by loading * rate.
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=1.0, loading=1.0, alpha_daily=0.0)
    result = factors.regress_two_factor(port, market, umd, RF, DAYS)
    assert result["alpha"] == pytest.approx(0.0, abs=1e-10)


def test_regress_two_factor_with_no_momentum_equals_the_capm_alpha():
    # A portfolio with no momentum loading and no noise has the same beta
    # and the same alpha in the two regressions.
    market, umd = _two_factors()
    port = _portfolio(market, umd, beta=1.3, loading=0.0,
                      alpha_daily=0.0002)
    two = factors.regress_two_factor(port, market, umd, RF, DAYS)
    one = capm.regress_on_market(port, market, RF, DAYS)
    assert two["beta"] == pytest.approx(one["beta"], abs=1e-10)
    assert two["alpha"] == pytest.approx(one["alpha"], abs=1e-10)


def test_regress_two_factor_uses_only_the_common_dates():
    market, umd = _two_factors(days=400)
    port = _portfolio(market, umd, beta=0.5, loading=0.5, alpha_daily=0.0)
    result = factors.regress_two_factor(port, market, umd.iloc[100:], RF,
                                        DAYS)
    assert result["n_days"] == 300
    assert result["umd_loading"] == pytest.approx(0.5, abs=1e-10)


def test_regress_two_factor_gives_nan_for_too_few_days():
    market, umd = _two_factors(days=3)
    result = factors.regress_two_factor(market, market, umd, RF, DAYS)
    assert np.isnan(result["umd_loading"])
    assert np.isnan(result["alpha"])
    assert result["n_days"] == 3


def test_spy_on_itself_gives_beta_one_and_no_momentum_or_alpha():
    # The sanity check of D30. The market factor is SPY minus the
    # risk-free rate. A regression of SPY on that factor and on UMD must
    # give a beta of 1, a UMD loading of 0, and an alpha of 0.
    market, umd = _two_factors()
    result = factors.regress_two_factor(market, market, umd, RF, DAYS)
    assert result["beta"] == pytest.approx(1.0, abs=1e-10)
    assert result["umd_loading"] == pytest.approx(0.0, abs=1e-10)
    assert result["alpha"] == pytest.approx(0.0, abs=1e-10)


# --- the in-house UMD factor ----------------------------------------------
#
# The tiny panel has 12 trading days, from 2024-01-24 to 2024-02-08. The
# last trading day of January is 2024-01-31 (row 5). That day is the
# formation date. With a lookback of 4 days and a skip of 1 day, the signal
# is the compound return of rows 2, 3 and 4. Row 5 is the skipped day. The
# portfolio holds the legs from row 6 (2024-02-01) to the end.
#
# Six stocks and a quantile of 1/3 give 2 stocks in each leg.
#   Signal rows 2-4:  A 5%, B 4%, C 3%, D 2%, E 1%, F 0% each day.
#   So the long leg is A and B, and the short leg is E and F.
#   The skipped row 5: A and B fall 50%, E and F rise 50%. A rule without
#   the skip puts A and B in the short leg.
#   Hold rows 6-11:   A 1.0%, B 2.0%, C 0, D 0, E 0.1%, F 0.3% each day.
#   So UMD = (1.0% + 2.0%) / 2 - (0.1% + 0.3%) / 2 = 1.3% each day.

LOOKBACK = 4
SKIP = 1
QUANTILE = 1 / 3
TICKERS = ["A", "B", "C", "D", "E", "F"]


def _panel() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-24", periods=12)
    signal = {"A": 0.05, "B": 0.04, "C": 0.03, "D": 0.02, "E": 0.01,
              "F": 0.00}
    skipped = {"A": -0.5, "B": -0.5, "C": 0.0, "D": 0.0, "E": 0.5, "F": 0.5}
    hold = {"A": 0.010, "B": 0.020, "C": 0.0, "D": 0.0, "E": 0.001,
            "F": 0.003}
    rows = []
    for position in range(12):
        if position < 2:
            rows.append({t: 0.0 for t in TICKERS})
        elif position < 5:
            rows.append(dict(signal))
        elif position == 5:
            rows.append(dict(skipped))
        else:
            rows.append(dict(hold))
    return pd.DataFrame(rows, index=dates)


def _members(tickers: list[str], date: str = "2024-01-01") -> pd.DataFrame:
    return pd.DataFrame({"as_of_date": pd.Timestamp(date), "ticker": tickers})


def test_formation_dates_are_the_last_trading_day_of_each_month():
    index = pd.bdate_range("2024-01-24", periods=12)
    assert factors.formation_dates(index) == [pd.Timestamp("2024-01-31"),
                                              pd.Timestamp("2024-02-08")]


def test_umd_legs_hold_the_winners_and_the_losers_by_hand():
    legs = factors.umd_legs(_panel(), _members(TICKERS), LOOKBACK, SKIP,
                            QUANTILE)
    first = legs[0]
    assert first["formation_date"] == pd.Timestamp("2024-01-31")
    assert first["long"] == ["A", "B"]
    assert first["short"] == ["E", "F"]


def test_build_umd_gives_the_hand_value_on_each_hold_day():
    umd = factors.build_umd(_panel(), _members(TICKERS), LOOKBACK, SKIP,
                            QUANTILE)
    # The factor starts on the day after the formation date.
    assert umd.index[0] == pd.Timestamp("2024-02-01")
    assert len(umd) == 6
    assert np.allclose(umd.to_numpy(), 0.013, atol=1e-12)


def test_build_umd_skips_the_most_recent_days():
    # With the skip, A and B are winners. Without it, they are losers.
    with_skip = factors.umd_legs(_panel(), _members(TICKERS), LOOKBACK, SKIP,
                                 QUANTILE)
    assert with_skip[0]["long"] == ["A", "B"]
    no_skip = factors.umd_legs(_panel(), _members(TICKERS), LOOKBACK - 1, 0,
                               QUANTILE)
    assert no_skip[0]["short"] == ["A", "B"]


def test_build_umd_uses_only_the_members_on_the_formation_date():
    # G has the highest signal, but G joins the index after the formation
    # date. The rule must not use G.
    panel = _panel()
    panel["G"] = panel["A"] * 2
    members = pd.concat([_members(TICKERS),
                         _members(TICKERS + ["G"], "2024-02-01")])
    legs = factors.umd_legs(panel, members, LOOKBACK, SKIP, QUANTILE)
    assert "G" not in legs[0]["long"] + legs[0]["short"]


def test_build_umd_needs_a_full_history_in_the_formation_window():
    # A stock with a gap in the formation window has no signal. A gap
    # before the window does not matter.
    panel = _panel()
    panel.loc[panel.index[3], "A"] = np.nan
    panel.loc[panel.index[0], "F"] = np.nan
    legs = factors.umd_legs(panel, _members(TICKERS), LOOKBACK, SKIP,
                            QUANTILE)
    assert "A" not in legs[0]["long"] + legs[0]["short"]
    assert "F" in legs[0]["short"]


def test_build_umd_uses_no_future_prices():
    # Change every return after a cut day. The factor up to the cut day
    # and the legs of the formation date must not change.
    panel = _panel()
    base = factors.build_umd(panel, _members(TICKERS), LOOKBACK, SKIP,
                             QUANTILE)
    cut = panel.index[8]
    tampered = panel.copy()
    rng = np.random.default_rng(0)
    after = tampered.index > cut
    tampered.loc[after] = rng.normal(0.0, 0.3, (after.sum(), len(TICKERS)))
    changed = factors.build_umd(tampered, _members(TICKERS), LOOKBACK, SKIP,
                                QUANTILE)
    assert changed[changed.index <= cut].equals(base[base.index <= cut])
    assert not changed.equals(base)


def test_umd_legs_use_no_return_after_the_formation_date():
    # For each cut day, give a crash to one pair of stocks and a jump to
    # the other pair on every day after the cut. Do it in both directions.
    # A leg that a formation date on or before the cut gives must not
    # change. A rule that reads one day too far fails.
    panel = _panel()
    for cut, (up, down) in itertools.product(
            panel.index, [(["A", "B"], ["E", "F"]), (["E", "F"], ["A", "B"])]):
        tampered = panel.copy()
        after = tampered.index > cut
        tampered.loc[after, up] = 5.0
        tampered.loc[after, down] = -0.9
        base = factors.umd_legs(panel, _members(TICKERS), LOOKBACK, SKIP,
                                QUANTILE)
        changed = factors.umd_legs(tampered, _members(TICKERS), LOOKBACK,
                                   SKIP, QUANTILE)
        known = [leg for leg in base if leg["formation_date"] <= cut]
        assert [leg for leg in changed
                if leg["formation_date"] <= cut] == known, cut


def test_build_umd_does_not_use_the_formation_day_return():
    # The return of the formation date is in the skipped window and not in
    # the hold. A factor that holds the legs on the formation date itself
    # takes the -50% and +50% moves of row 5.
    umd = factors.build_umd(_panel(), _members(TICKERS), LOOKBACK, SKIP,
                            QUANTILE)
    assert pd.Timestamp("2024-01-31") not in umd.index


def test_build_umd_with_too_few_stocks_gives_no_factor():
    # Two stocks and a quantile of 1/3 give no stock in a leg.
    umd = factors.build_umd(_panel()[["A", "F"]], _members(["A", "F"]),
                            LOOKBACK, SKIP, QUANTILE)
    assert umd.empty


# --- the Ken French data --------------------------------------------------

MOM_TEXT = """This file was created by using the 202609 CRSP database.  It
contains a momentum factor.

Missing data are indicated by -99.99 or -999.

,Mom
20260928,   1.63
20260929,  -0.31
20260930, -99.99

Copyright 2026 Eugene F. Fama and Kenneth R. French
"""

FF3_TEXT = """This file was created by using the 202609 CRSP database.

,Mkt-RF,SMB,HML,RF
20260928,    0.50,   -0.01,   -0.50,    0.01
20260929,   -0.21,   -0.01,   -0.50,    0.01

Copyright 2026 Eugene F. Fama and Kenneth R. French
"""


def test_read_french_csv_reads_percent_as_a_decimal():
    frame = factors.read_french_csv(MOM_TEXT)
    assert list(frame.columns) == ["umd"]
    assert frame.index[0] == pd.Timestamp("2026-09-28")
    assert frame.loc["2026-09-28", "umd"] == pytest.approx(0.0163)
    assert frame.loc["2026-09-29", "umd"] == pytest.approx(-0.0031)


def test_read_french_csv_gives_nan_for_a_missing_value():
    frame = factors.read_french_csv(MOM_TEXT)
    assert np.isnan(frame.loc["2026-09-30", "umd"])


def test_read_french_csv_names_the_three_factor_columns():
    frame = factors.read_french_csv(FF3_TEXT)
    assert list(frame.columns) == ["mkt_rf", "smb", "hml", "rf"]
    assert frame.loc["2026-09-28", "mkt_rf"] == pytest.approx(0.005)
    assert frame.loc["2026-09-29", "rf"] == pytest.approx(0.0001)
    assert len(frame) == 2


def _write_zip(path, name: str, text: str) -> None:
    import zipfile
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, text)


def test_load_french_factors_joins_the_two_files(tmp_path):
    _write_zip(tmp_path / factors.FRENCH_FILES["momentum"],
               "F-F_Momentum_Factor_daily.csv", MOM_TEXT)
    _write_zip(tmp_path / factors.FRENCH_FILES["three_factor"],
               "F-F_Research_Data_Factors_daily.csv", FF3_TEXT)
    frame = factors.load_french_factors(tmp_path)
    # Only the dates in both files with a value in each column stay.
    assert list(frame.index) == [pd.Timestamp("2026-09-28"),
                                 pd.Timestamp("2026-09-29")]
    assert {"umd", "mkt_rf", "rf"} <= set(frame.columns)


def test_load_french_factors_gives_none_without_the_files(tmp_path):
    assert factors.load_french_factors(tmp_path) is None


def test_download_french_keeps_a_cached_file(tmp_path):
    calls = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return b"new"

    for name in factors.FRENCH_FILES.values():
        (tmp_path / name).write_bytes(b"old")
    factors.download_french(tmp_path, fetch=fetch)
    assert calls == []
    factors.download_french(tmp_path, fetch=fetch, refresh=True)
    assert len(calls) == 2
    for name in factors.FRENCH_FILES.values():
        assert (tmp_path / name).read_bytes() == b"new"
