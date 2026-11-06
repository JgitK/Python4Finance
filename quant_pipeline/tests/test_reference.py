"""Tests for the reference data: index membership and sectors.

These tests use small fixed rows. They do not use the network.
"""

from __future__ import annotations

from quant import reference


# --- tickers_in_range -------------------------------------------------------
# A ticker is in the download list when its index membership overlaps the
# date range. An empty end_date means that the stock is still in the index.

def _intervals() -> list[dict[str, str]]:
    return [
        {"ticker": "OLD", "start_date": "2000-01-03", "end_date": "2010-05-03"},
        {"ticker": "LEFT", "start_date": "2001-01-02", "end_date": "2024-03-18"},
        {"ticker": "STAY", "start_date": "2005-06-01", "end_date": ""},
        {"ticker": "NEW", "start_date": "2025-09-22", "end_date": ""},
        # A stock can join two times. Each stint is one row.
        {"ticker": "BACK", "start_date": "1999-01-04", "end_date": "2001-02-01"},
        {"ticker": "BACK", "start_date": "2023-05-01", "end_date": ""},
    ]


def test_tickers_in_range_keeps_every_overlapping_stint():
    tickers = reference.tickers_in_range(_intervals(), "2022-11-01", "2026-11-01")
    assert tickers == ["BACK", "LEFT", "NEW", "STAY"]


def test_tickers_in_range_drops_a_stint_that_ends_on_the_start_date():
    # The end date is the first day out of the index.
    rows = [{"ticker": "EDGE", "start_date": "2010-01-04", "end_date": "2022-11-01"}]
    assert reference.tickers_in_range(rows, "2022-11-01", "2026-11-01") == []


# --- sector_map ---------------------------------------------------------------
# The sector of a ticker comes from the newest snapshot with a valid GICS
# sector. Old snapshots use a "Sector" column. New snapshots use "GICS Sector".

def _snapshots() -> list[tuple[str, list[dict[str, str]]]]:
    return [
        ("2015-01-02", [{"Symbol": "AAA", "Name": "A", "Sector": "Information Technology"},
                        {"Symbol": "BBB", "Name": "B", "Sector": "Financials"}]),
        ("2023-03-07", [{"Symbol": "BBB", "Security": "B", "GICS Sector": "Regional Banks"}]),
        ("2024-01-02", [{"Symbol": "AAA", "Security": "A", "GICS Sector": "Financials"}]),
    ]


def test_sector_map_uses_the_newest_snapshot():
    sectors = reference.sector_map(_snapshots())
    # AAA moved from Information Technology to Financials. The newest wins.
    assert sectors["AAA"] == "Financials"


def test_sector_map_ignores_a_label_that_is_not_a_gics_sector():
    sectors = reference.sector_map(_snapshots())
    # "Regional Banks" is a sub-industry, so the older valid label stays.
    assert sectors["BBB"] == "Financials"


def test_sector_map_does_not_depend_on_the_input_order():
    snapshots = list(reversed(_snapshots()))
    assert reference.sector_map(snapshots) == reference.sector_map(_snapshots())
