"""Tests for the independent verification script.

`verify_indicators.py` rebuilds the indicators, the metrics and the screen
with pandas and compares them to dbt. It is the one check that does not
share code with the pipeline, so a stale rule in it makes the check
useless: it then compares dbt against a rule that nobody uses.

D22 made the rank metric a setting. These tests hold the script to that
setting.
"""

from __future__ import annotations

import pytest

import verify_indicators
from quant import pipeline


def test_the_script_reads_the_rank_metric_from_the_project_file():
    # The script takes every other gate from this dictionary. The rank
    # metric must come from the same place, or a change of the setting
    # leaves the check behind.
    assert "rank_metric" in verify_indicators.DBT_VARS


def test_the_dbt_rank_metric_matches_the_python_default():
    # The screen ranks in dbt and the selection ranks in Python. The two
    # must agree, or the screen keeps one set of stocks and the selection
    # prefers another. This test fails when somebody changes one layer.
    assert (verify_indicators.DBT_VARS["rank_metric"]
            == pipeline.PortfolioParams().rank_metric)


def test_the_rank_column_follows_the_metric():
    assert verify_indicators.screen_rank_column("cum_return") == "cum_return"
    assert verify_indicators.screen_rank_column("sharpe") == "sharpe"


def test_the_rank_column_refuses_an_unknown_metric():
    # A silent default would make the check compare dbt against a rule
    # that nobody asked for, and the check would still report PASS.
    with pytest.raises(ValueError, match="magic"):
        verify_indicators.screen_rank_column("magic")
