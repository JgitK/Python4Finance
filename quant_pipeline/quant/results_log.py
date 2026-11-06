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
    "| Run date | Commit | Candidates | Live Sharpe (in-sample) "
    "| Window 1: portfolio vs SPY | Window 2 | Window 3 | Note |\n"
    "|---|---|---|---|---|---|---|---|"
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


def format_row(run_date: str, revision: str, n_candidates: int,
               live_sharpe: float, backtest: pd.DataFrame) -> str:
    """Make one Markdown table row from the results of a run."""
    windows = [
        f"{pd.Timestamp(r.selection_date).date()}: "
        f"{r.portfolio_return:+.1%} vs {r.benchmark_return:+.1%}"
        for r in backtest.itertuples()
    ]
    # The table has three window columns.
    windows = (windows + ["", "", ""])[:3]
    cells = [run_date, revision, str(n_candidates), f"{live_sharpe:.2f}",
             *windows, ""]
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
