"""Tests for the backtest inputs in run_pipeline.

The backtest must not start from the stocks that pass the screen today.
Today's screen uses data from the holding periods of the backtest.
These tests read the real DuckDB warehouse. Run the dbt build before
these tests. The tests skip when the warehouse file is not there.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import run_pipeline
from quant import pipeline, universe, warehouse

pytestmark = pytest.mark.skipif(
    not warehouse.DEFAULT_WAREHOUSE.exists(),
    reason="Run 'dbt build' first to create the warehouse.",
)


@pytest.fixture(scope="module")
def con():
    connection = warehouse.connect()
    yield connection
    connection.close()


def test_backtest_inputs_hold_every_stock_and_the_benchmark(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    every_stock = set(warehouse.read_sector_map(con))
    # A stock with prices but no sector can be in the frame too.
    assert every_stock | {universe.BENCHMARK} <= set(returns.columns)


def test_backtest_inputs_include_stocks_that_fail_the_screen_today(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    today = set(warehouse.read_candidates(con)["ticker"])
    # Some stocks fail the screen today. They can still pass on a past date.
    assert set(returns.columns) - today - {universe.BENCHMARK}


def test_backtest_inputs_include_the_screen_history(con):
    _, history = run_pipeline.load_backtest_inputs(con)
    assert len(history) > 0


def test_backtest_builder_on_the_last_date_equals_the_live_portfolio(con):
    # On the last date, the backtest and the live run have the same data.
    # Because of this, they must give the same weights. A different lookback
    # window or a different stock list makes the weights different.
    params = pipeline.PortfolioParams(n_portfolios=300, seed=7)
    live = run_pipeline.build_live_portfolio(con, params)

    returns, history = run_pipeline.load_backtest_inputs(con)
    build = pipeline.make_builder(warehouse.read_sector_map(con), params,
                                  universe.BENCHMARK, screen_history=history)
    assert build(returns) == pytest.approx(live["weights"])


def test_coverage_report_has_one_row_for_each_date(con):
    returns, _ = run_pipeline.load_backtest_inputs(con)
    dates = run_pipeline.choose_selection_dates(returns.index) + [returns.index[-1]]
    report = run_pipeline.coverage_report(con, dates)
    assert len(report) == len(dates)
    assert (report["members"] >= report["usable"]).all()
    if warehouse.read_universe(con) == "sp500":
        # The S&P 500 has about 500 members on each date.
        assert report["members"].between(490, 510).all()


def test_dbt_command_passes_the_universe():
    command = run_pipeline.dbt_command("nasdaq")
    assert command[:2] == ["dbt", "build"]
    assert "--vars" in command
    assert command[command.index("--vars") + 1] == '{"universe": "nasdaq"}'


def test_choose_selection_dates_skips_dates_before_the_screen_history(con):
    # The screen history starts after the warm-up of the risk metrics and
    # the Ichimoku lines. On a date before that, no stock passes the screen,
    # so the backtest holds nothing and reports a 0% return. Such a window
    # is not a result. The function must not return such a date.
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    every_date = run_pipeline.choose_selection_dates(index)
    assert len(every_date) == 3

    # A cut-off on the newest date must drop the two older dates.
    newest = max(every_date)
    kept = run_pipeline.choose_selection_dates(index, first_screen_date=newest)
    assert kept == [newest]

    # The real screen history must keep all three dates of the live run.
    _, history = run_pipeline.load_backtest_inputs(con)
    first = pd.Timestamp(history["as_of_date"].min())
    returns, _ = run_pipeline.load_backtest_inputs(con)
    real = run_pipeline.choose_selection_dates(returns.index,
                                               first_screen_date=first)
    assert len(real) == 3
    assert min(real) >= first


# ---------------------------------------------------------------------------
# Many selection dates.


def test_choose_many_selection_dates_steps_through_every_valid_date():
    # Three overlapping windows cannot show that a result is not luck.
    # This function gives every date that has a full holding window after
    # it, with a step between the dates.
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    dates = run_pipeline.choose_many_selection_dates(index, step=5)
    # The first date needs 261 days of warm-up. The last date needs 180
    # days of holding period after it.
    assert dates[0] == index[261]
    assert dates[-1] <= index[1001 - run_pipeline.HOLDING_PERIOD]
    assert len(dates) == 113
    # The step must hold between each pair of dates.
    positions = [index.get_loc(d) for d in dates]
    assert set(np.diff(positions)) == {5}


def test_choose_many_selection_dates_obeys_the_step():
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    assert len(run_pipeline.choose_many_selection_dates(index, step=1)) == 561
    assert len(run_pipeline.choose_many_selection_dates(index, step=20)) == 29


def test_choose_many_selection_dates_skips_dates_before_the_screen_history():
    # A date before the start of the screen history selects no stock. The
    # backtest then holds nothing and reports a 0% return. Such a window
    # is not a result, so this function must not return such a date.
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    every_date = run_pipeline.choose_many_selection_dates(index, step=5)
    cut = every_date[len(every_date) // 2]
    kept = run_pipeline.choose_many_selection_dates(
        index, step=5, first_screen_date=cut)
    assert kept[0] == cut
    assert len(kept) == len(every_date) - len(every_date) // 2


def test_choose_many_selection_dates_on_the_real_warehouse(con):
    import pandas as pd

    returns, history = run_pipeline.load_backtest_inputs(con)
    first = pd.Timestamp(history["as_of_date"].min())
    dates = run_pipeline.choose_many_selection_dates(
        returns.index, step=5, first_screen_date=first)
    # The experiment of 2026-11-06 found 84 valid windows with this step.
    assert len(dates) >= 80
    assert min(dates) >= first


# ---------------------------------------------------------------------------
# The two caps of the exposure (D20).
#
# `top_n_per_sector` caps the candidates of each sector in dbt.
# `target_size` and `max_per_sector` cap the portfolio in Python.
# A measurement of the exposure must set the three from the command line,
# because a hand edit of dbt_project.yml does not reach the results log.


def test_dbt_command_passes_the_sector_cap():
    command = run_pipeline.dbt_command("nasdaq", top_n_per_sector=25)
    variables = json.loads(command[command.index("--vars") + 1])
    assert variables == {"universe": "nasdaq", "top_n_per_sector": 25}


def test_dbt_command_without_a_cap_keeps_the_project_default():
    # No cap on the command line means no cap in the vars. dbt then reads
    # the value of dbt_project.yml.
    command = run_pipeline.dbt_command("sp500")
    variables = json.loads(command[command.index("--vars") + 1])
    assert variables == {"universe": "sp500"}


def test_the_parser_defaults_match_the_portfolio_params():
    args = run_pipeline.make_parser().parse_args([])
    default = pipeline.PortfolioParams()
    assert args.target_size == default.target_size
    assert args.max_per_sector == default.max_per_sector
    assert args.top_n_per_sector is None


def test_the_parser_reads_the_three_caps():
    args = run_pipeline.make_parser().parse_args(
        ["--top-n-per-sector", "50", "--target-size", "30",
         "--max-per-sector", "6"])
    assert args.top_n_per_sector == 50
    assert args.target_size == 30
    assert args.max_per_sector == 6


def test_params_from_args_carries_the_two_python_caps():
    args = run_pipeline.make_parser().parse_args(
        ["--target-size", "30", "--max-per-sector", "6",
         "--n-portfolios", "500"])
    params = run_pipeline.params_from_args(args)
    assert params.target_size == 30
    assert params.max_per_sector == 6
    assert params.n_portfolios == 500


def test_caps_label_names_the_three_caps():
    # The results log must say which caps made a row. Without the label,
    # two rows of the same commit look like the same experiment.
    args = run_pipeline.make_parser().parse_args(
        ["--top-n-per-sector", "50", "--target-size", "30",
         "--max-per-sector", "6"])
    assert run_pipeline.caps_label(args) == "50/30/6"


def test_caps_label_reads_the_sector_cap_of_the_project_file():
    # Without --top-n-per-sector, the run reads the cap from
    # dbt_project.yml. The label must still state the number, or a reader
    # of the results log cannot repeat the run.
    args = run_pipeline.make_parser().parse_args([])
    cap = run_pipeline.project_default_top_n()
    default = pipeline.PortfolioParams()
    assert isinstance(cap, int)
    assert run_pipeline.caps_label(args) == (
        f"{cap}/{default.target_size}/{default.max_per_sector}")


def test_the_project_file_still_holds_the_sector_cap_of_the_handoff():
    # D20 measured the caps from this start value. A change of the project
    # file moves every baseline, so this test states the start value.
    assert run_pipeline.project_default_top_n() == 10


# ---------------------------------------------------------------------------
# The rank metric on the command line (D22).


def test_dbt_command_passes_the_rank_metric():
    command = run_pipeline.dbt_command("sp500", rank_metric="sharpe")
    variables = json.loads(command[command.index("--vars") + 1])
    assert variables == {"universe": "sp500", "rank_metric": "sharpe"}


def test_dbt_command_without_a_rank_metric_keeps_the_project_default():
    command = run_pipeline.dbt_command("sp500")
    variables = json.loads(command[command.index("--vars") + 1])
    assert "rank_metric" not in variables


def test_the_parser_default_rank_metric_matches_the_portfolio_params():
    args = run_pipeline.make_parser().parse_args([])
    assert args.rank_metric == pipeline.PortfolioParams().rank_metric


def test_params_from_args_carries_the_rank_metric():
    args = run_pipeline.make_parser().parse_args(["--rank-metric", "sharpe"])
    assert run_pipeline.params_from_args(args).rank_metric == "sharpe"


def test_a_rank_metric_change_reaches_dbt_as_well_as_python():
    # The screen ranks in dbt and the selection ranks in Python. A flag
    # that reaches only one of the two gives a screen and a selection that
    # disagree.
    args = run_pipeline.make_parser().parse_args(["--rank-metric", "sharpe"])
    command = run_pipeline.dbt_command(args.universe, args.top_n_per_sector,
                                       args.rank_metric)
    variables = json.loads(command[command.index("--vars") + 1])
    assert variables["rank_metric"] == "sharpe"
    assert run_pipeline.params_from_args(args).rank_metric == "sharpe"


# --- the share plan (D26) -------------------------------------------------

def test_whole_shares_are_the_default():
    args = run_pipeline.make_parser().parse_args([])
    assert args.fractional_shares is False


def test_the_flag_turns_on_fractional_shares():
    args = run_pipeline.make_parser().parse_args(["--fractional-shares"])
    assert args.fractional_shares is True


def test_a_fractional_plan_holds_every_stock_and_gives_no_warning():
    weights = {"A": 0.5, "B": 0.5}
    prices = {"A": 10.0, "B": 4000.0}
    whole, whole_warnings = run_pipeline.share_plan(
        weights, prices, 1000.0, fractional=False)
    assert whole.set_index("ticker").loc["B", "shares"] == 0
    assert any("drops B" in w for w in whole_warnings)
    part, part_warnings = run_pipeline.share_plan(
        weights, prices, 1000.0, fractional=True)
    assert part.set_index("ticker").loc["B", "shares"] == pytest.approx(0.125)
    assert part_warnings == []


# ---------------------------------------------------------------------------
# The holding-period checkpoints (D31).


def test_choose_many_selection_dates_takes_a_shorter_hold():
    # A shorter hold ends earlier, so a later date has a full window.
    import pandas as pd

    index = pd.DatetimeIndex(pd.bdate_range("2022-11-01", periods=1002))
    long = run_pipeline.choose_many_selection_dates(index, step=5)
    short = run_pipeline.choose_many_selection_dates(index, step=5,
                                                     holding_period=90)
    assert short[-1] <= index[1001 - 90]
    assert short[-1] > index[1001 - 90 - 5]
    assert len(short) == 131
    # The grid is the same, so the long hold is the first part of it.
    assert short[:len(long)] == long


def test_the_default_hold_is_the_single_period_of_180_days():
    args = run_pipeline.make_parser().parse_args([])
    assert args.hold_days == [run_pipeline.HOLDING_PERIOD]


def test_the_parser_reads_the_hold_days():
    args = run_pipeline.make_parser().parse_args(
        ["--hold-days", "180,90,120,150"])
    assert args.hold_days == [90, 120, 150, 180]


def test_run_checkpoints_gives_the_two_views(tmp_path, monkeypatch):
    # A synthetic panel with 600 days. The view of all valid dates must
    # give the short hold more windows than the same-dates view.
    import argparse

    import pandas as pd

    monkeypatch.setattr(run_pipeline, "OUTPUT_DIR", tmp_path)
    index = pd.bdate_range("2022-01-03", periods=600)
    rng = np.random.default_rng(1)
    returns = pd.DataFrame({"AAA": rng.normal(0.001, 0.01, 600),
                            universe.BENCHMARK: rng.normal(0.0, 0.01, 600)},
                           index=index)
    history = pd.DataFrame({"as_of_date": [index[0]], "ticker": ["AAA"]})
    args = argparse.Namespace(window_step=5, hold_days=[90, 180])
    tables = run_pipeline.run_checkpoints(
        returns, history, lambda train: {"AAA": 1.0},
        pipeline.PortfolioParams(), args)
    same = tables["same_dates"].set_index("hold_days")
    every = tables["all_dates"].set_index("hold_days")
    # Positions 261 to 599 - 180 = 419 with a step of 5: 32 dates.
    assert same.loc[90, "windows"] == same.loc[180, "windows"] == 32
    # Positions 261 to 599 - 90 = 509 with a step of 5: 50 dates.
    assert every.loc[90, "windows"] == 50
    assert every.loc[180, "windows"] == 32
    assert (tmp_path / "holding_checkpoints_all_dates.csv").exists()
