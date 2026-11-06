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


def _row(revision: str = "abc1234") -> str:
    return results_log.format_row(
        run_date="2026-11-06", revision=revision, n_candidates=110,
        live_sharpe=4.6573, backtest=_backtest())


def test_format_row_shows_each_window_against_the_benchmark():
    row = _row()
    assert row.startswith("| 2026-11-06 | abc1234 | 110 | 4.66 |")
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
