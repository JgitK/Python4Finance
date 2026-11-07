"""Tests for the automatic results log.

Each pipeline run adds one row to a Markdown table. The row records the
commit and the results, so you can see how each change moved the numbers.
"""

from __future__ import annotations

import pandas as pd

from quant import results_log


def _backtest() -> pd.DataFrame:
    return pd.DataFrame({
        "selection_date": ["2026-02-11", "2025-08-12"],
        "portfolio_return": [0.126518, -0.021348],
        "benchmark_return": [0.111856, 0.135918],
    })


def _row(revision: str = "abc1234", universe: str = "sp500") -> str:
    return results_log.format_row(
        run_date="2026-11-06", revision=revision, universe=universe,
        n_candidates=110, live_sharpe=4.6573, backtest=_backtest())


def test_format_row_shows_each_window_against_the_benchmark():
    row = _row()
    # The caps cell is between the universe and the candidate count.
    # The caps and the rank cells sit between the universe and the count.
    assert row.startswith("| 2026-11-06 | abc1234 | sp500 |  |  | 110 | 4.66 |")
    assert "2026-02-11: +12.7% vs +11.2%" in row
    assert "2025-08-12: -2.1% vs +13.6%" in row
    assert row.endswith("|  |")  # The note cell is empty. You fill it in.


def test_append_row_creates_the_table_when_the_file_is_new(tmp_path):
    path = tmp_path / "results_log.md"
    assert results_log.append_row(path, _row()) is True
    text = path.read_text()
    assert results_log.TABLE_HEADER in text
    assert text.rstrip().endswith(_row())


def test_append_row_adds_to_the_end_of_an_existing_table(tmp_path):
    path = tmp_path / "results_log.md"
    results_log.append_row(path, _row("aaa1111"))
    results_log.append_row(path, _row("bbb2222"))
    lines = path.read_text().rstrip().splitlines()
    assert "aaa1111" in lines[-2] and "bbb2222" in lines[-1]


def test_append_row_skips_a_repeat_of_the_same_clean_commit(tmp_path):
    path = tmp_path / "results_log.md"
    results_log.append_row(path, _row())
    # The same commit and the same results on a later day add nothing new.
    later = _row().replace("2026-11-06", "2026-11-07")
    assert results_log.append_row(path, later) is False
    assert path.read_text().count("abc1234") == 1


def test_append_row_always_adds_a_run_with_uncommitted_changes(tmp_path):
    path = tmp_path / "results_log.md"
    results_log.append_row(path, _row("abc1234-dirty"))
    # Two dirty runs can have different code, so both rows stay.
    assert results_log.append_row(path, _row("abc1234-dirty")) is True
    assert path.read_text().count("abc1234-dirty") == 2


def test_git_revision_reports_unknown_outside_a_repository(tmp_path):
    assert results_log.git_revision(tmp_path) == "unknown"


def test_git_revision_ignores_a_change_to_the_log_itself(tmp_path):
    import subprocess

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True,
                       capture_output=True)

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "results_log.md").write_text("# Results log\n")
    (tmp_path / "code.py").write_text("x = 1\n")
    git("add", "-A")
    git("commit", "-q", "-m", "start")

    # A new log row is not a code change, so the run is still clean.
    (tmp_path / "docs" / "results_log.md").write_text("# Results log\nrow\n")
    assert not results_log.git_revision(tmp_path).endswith("-dirty")

    # A code change makes the run dirty.
    (tmp_path / "code.py").write_text("x = 2\n")
    assert results_log.git_revision(tmp_path).endswith("-dirty")


def test_append_row_keeps_runs_of_two_universes_on_one_commit(tmp_path):
    path = tmp_path / "results_log.md"
    results_log.append_row(path, _row(universe="sp500"))
    # The same commit with another universe is a different run.
    assert results_log.append_row(path, _row(universe="nasdaq")) is True


# ---------------------------------------------------------------------------
# The many-window column.


def _summary() -> dict:
    return {"n_windows": 84, "n_scored": 84, "n_sharpe": 84,
            "win_return": 0.5357, "win_sharpe": 0.4524,
            "mean_excess": 0.0022, "median_excess": 0.0019,
            "mean_sharpe": 0.58, "mean_benchmark_sharpe": 0.79}


def test_the_table_has_a_column_for_the_many_window_measure():
    assert "Walk-forward" in results_log.TABLE_HEADER
    # The header row and the separator row must have the same cell count.
    header, separator = results_log.TABLE_HEADER.splitlines()
    assert header.count("|") == separator.count("|")


def test_format_row_holds_the_many_window_measure():
    row = results_log.format_row(
        run_date="2026-11-06", revision="abc1234", universe="sp500",
        n_candidates=110, live_sharpe=4.6573, backtest=_backtest(),
        summary=_summary())
    assert "84 windows" in row
    assert "53.6% on return" in row
    assert "45.2% on Sharpe" in row
    assert "+0.2%" in row
    # The note cell stays last and stays empty.
    assert row.endswith("|  |")
    # The row must have the same cell count as the header.
    header = results_log.TABLE_HEADER.splitlines()[0]
    assert row.count("|") == header.count("|")


def test_format_row_without_a_measure_leaves_the_cell_empty():
    row = _row()
    header = results_log.TABLE_HEADER.splitlines()[0]
    assert row.count("|") == header.count("|")
    assert row.endswith("|  |  |")


def test_the_measure_says_when_a_window_has_no_result():
    # A window that the summary cannot score must stay visible. A silent
    # drop of such a window gave a wrong result in an earlier experiment.
    summary = _summary() | {"n_windows": 114, "n_scored": 84}
    row = results_log.format_row(
        run_date="2026-11-06", revision="abc1234", universe="sp500",
        n_candidates=110, live_sharpe=4.6573, backtest=_backtest(),
        summary=summary)
    assert "84 of 114 windows" in row


# ---------------------------------------------------------------------------
# The caps column (D20).
#
# A run can change the three caps of the exposure from the command line.
# The row must say which caps made it, or two rows of the same commit look
# like the same experiment.


def test_format_row_holds_the_caps_after_the_universe():
    row = results_log.format_row(
        run_date="2026-11-06", revision="abc1234", universe="both",
        caps="50/30/6", n_candidates=755, live_sharpe=4.6573,
        backtest=_backtest())
    assert row.startswith("| 2026-11-06 | abc1234 | both | 50/30/6 |  | 755 |")


def test_format_row_without_caps_leaves_the_cell_empty():
    row = results_log.format_row(
        run_date="2026-11-06", revision="abc1234", universe="sp500",
        n_candidates=110, live_sharpe=4.6573, backtest=_backtest())
    assert row.startswith("| 2026-11-06 | abc1234 | sp500 |  |  | 110 |")


def test_the_table_header_names_the_caps_column():
    assert "| Caps " in results_log.TABLE_HEADER


def test_append_row_separates_two_runs_that_differ_only_in_the_caps(tmp_path):
    # Two cap settings of the same commit are two experiments. The log
    # must hold both rows.
    path = tmp_path / "results_log.md"

    def row(caps: str) -> str:
        return results_log.format_row(
            run_date="2026-11-06", revision="abc1234", universe="sp500",
            caps=caps, n_candidates=110, live_sharpe=4.66,
            backtest=_backtest())

    assert results_log.append_row(path, row("10/12/3")) is True
    assert results_log.append_row(path, row("50/30/6")) is True
    assert path.read_text().count("abc1234") == 2


# ---------------------------------------------------------------------------
# The rank column (D22).


def test_format_row_holds_the_rank_metric_after_the_caps():
    row = results_log.format_row(
        run_date="2026-11-06", revision="abc1234", universe="sp500",
        caps="10/10/3", rank_metric="cum_return", n_candidates=110,
        live_sharpe=4.47, backtest=_backtest())
    assert row.startswith(
        "| 2026-11-06 | abc1234 | sp500 | 10/10/3 | cum_return | 110 |")


def test_the_table_header_names_the_rank_column():
    assert "| Rank " in results_log.TABLE_HEADER


def test_append_row_separates_two_runs_that_differ_only_in_the_rank(tmp_path):
    path = tmp_path / "results_log.md"

    def row(metric: str) -> str:
        return results_log.format_row(
            run_date="2026-11-06", revision="abc1234", universe="sp500",
            caps="10/10/3", rank_metric=metric, n_candidates=110,
            live_sharpe=4.47, backtest=_backtest())

    assert results_log.append_row(path, row("cum_return")) is True
    assert results_log.append_row(path, row("sharpe")) is True
    assert path.read_text().count("abc1234") == 2
