"""Add one row to the results log after each pipeline run.

The log is a Markdown table in docs/results_log.md. Each row records the
date, the git commit, and the results. Then you can see how each change to
the code moved the numbers. The last cell is empty. Write a short note in it.

A commit with "-dirty" had uncommitted changes when the pipeline ran.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

LOG_FILE = Path(__file__).resolve().parents[1] / "docs" / "results_log.md"

TABLE_HEADER = (
    "| Run date | Commit | Universe | Candidates | Live Sharpe (in-sample) "
    "| Window 1: portfolio vs SPY | Window 2 | Window 3 "
    "| Walk-forward, many windows | Note |\n"
    "|---|---|---|---|---|---|---|---|---|---|"
)


def git_revision(folder: Path) -> str:
    """Return the short commit hash. Add "-dirty" for uncommitted changes.

    Return "unknown" when the folder is not in a git repository.
    """
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=folder, check=True,
                              capture_output=True, text=True).stdout.strip()
    try:
        commit = git("rev-parse", "--short", "HEAD")
        # A new row in the log is not a code change.
        changes = git("status", "--porcelain", "--", ".",
                      ":(exclude)docs/results_log.md")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return f"{commit}-dirty" if changes else commit


def format_summary(summary: dict | None) -> str:
    """Write the measure of a many-window run in one cell.

    The cell gives the count of the windows, the share that beats the
    benchmark on the return and on the Sharpe ratio, and the excess
    return. When the summary cannot score every window, the cell gives
    both counts. A reader must see that a window has no result.
    """
    if not summary or not summary.get("n_scored"):
        return ""
    count = (f"{summary['n_scored']} of {summary['n_windows']} windows"
             if summary["n_scored"] != summary["n_windows"]
             else f"{summary['n_windows']} windows")
    return (f"{count}: {summary['win_return']:.1%} on return, "
            f"{summary['win_sharpe']:.1%} on Sharpe, "
            f"mean excess {summary['mean_excess']:+.1%}, "
            f"median {summary['median_excess']:+.1%}")


def format_row(run_date: str, revision: str, universe: str,
               n_candidates: int, live_sharpe: float,
               backtest: pd.DataFrame, summary: dict | None = None) -> str:
    """Make one Markdown table row from the results of a run.

    `summary` holds the measure of a many-window run. See
    `quant.backtest.summarize_windows`. A run without that measure leaves
    the cell empty.
    """
    windows = [
        f"{pd.Timestamp(r.selection_date).date()}: "
        f"{r.portfolio_return:+.1%} vs {r.benchmark_return:+.1%}"
        for r in backtest.itertuples()
    ]
    # The table has three window columns.
    windows = (windows + ["", "", ""])[:3]
    cells = [run_date, revision, universe, str(n_candidates),
             f"{live_sharpe:.2f}",
             *windows, format_summary(summary), ""]
    return "| " + " | ".join(cells) + " |"


def _without_date(row: str) -> str:
    """Return the row without its first cell, the run date."""
    return row.split("|", 2)[2]


def append_row(path: Path, row: str) -> bool:
    """Add the row to the end of the table. Return True if the row is new.

    Skip a row when the same clean commit already has the same results. A
    dirty run always gets a row, because its code can be different.
    """
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Results log\n\n" + TABLE_HEADER + "\n")
    text = path.read_text()
    revision = row.split("|")[2].strip()
    if not revision.endswith("-dirty"):
        for line in text.splitlines():
            if line.startswith("| ") and _without_date(line) == _without_date(row):
                return False
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + row + "\n")
    return True
