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


# --- the Nasdaq universe ----------------------------------------------------
# The Nasdaq universe is a rule: an operating company listed on the Nasdaq
# with a market cap of at least a limit in a monthly snapshot.

def test_is_operating_company_drops_securities_that_are_not_companies():
    for name in ["Acme Corp. Warrants", "Acme Corp. Rights",
                 "Hera Acquisition Corp. Class A Ordinary Shares",
                 "Acme Capital Units", "Big Tech ETF",
                 "Nuveen NASDAQ 100 Dynamic Overwrite Fund Shares",
                 "Acme Bank 7.5% Preferred Stock",
                 "Acme Depositary Shares Each Representing 1/40th Interest",
                 "Acme 5.25% Notes due 2030"]:
        assert not reference.is_operating_company(name), name


def test_is_operating_company_keeps_real_companies():
    for name in ["Apple Inc. Common Stock", "Preferred Bank Common Stock",
                 "Plains All American Pipeline L.P. Common Units representing",
                 "ATA Creativity Global American Depositary Shares",
                 "Northern Trust Corporation Common Stock"]:
        assert reference.is_operating_company(name), name


def _snap(*rows):
    return [{"symbol": s, "name": f"{s} Inc. Common Stock",
             "marketCap": str(cap), "sector": sector} for s, cap, sector in rows]


def _nasdaq_snapshots():
    return [
        ("2022-11-01", _snap(("BIG", 5e9, "Technology"), ("EDGE", 9e8, "Finance"),
                             ("GONE", 2e9, "Health Care"))),
        ("2022-12-01", _snap(("BIG", 5e9, "Technology"), ("EDGE", 1.2e9, "Finance"),
                             ("GONE", 2e9, "Health Care"))),
        # GONE is not listed any more. EDGE falls under the limit.
        ("2023-01-03", _snap(("BIG", 6e9, "Technology"), ("EDGE", 8e8, "Finance"))),
        ("2023-02-01", _snap(("BIG", 6e9, "Technology"), ("EDGE", 1.5e9, "Finance"))),
    ]


def test_nasdaq_intervals_follow_the_monthly_snapshots():
    stints = reference.nasdaq_intervals(_nasdaq_snapshots(), min_market_cap=1e9)
    assert stints == [
        {"ticker": "BIG", "start_date": "2022-11-01", "end_date": ""},
        # EDGE is in the universe two times: December, and from February.
        {"ticker": "EDGE", "start_date": "2022-12-01", "end_date": "2023-01-03"},
        {"ticker": "EDGE", "start_date": "2023-02-01", "end_date": ""},
        # The end date is the first snapshot without the stock.
        {"ticker": "GONE", "start_date": "2022-11-01", "end_date": "2023-01-03"},
    ]


def test_nasdaq_intervals_skip_a_security_that_is_not_a_company():
    snaps = [("2022-11-01", [{"symbol": "SPAC", "marketCap": "5e9", "sector": "",
                              "name": "Hera Acquisition Corp. Class A Ordinary Shares"}])]
    assert reference.nasdaq_intervals(snaps, min_market_cap=1e9) == []


def test_nasdaq_sector_map_uses_gics_names():
    sectors = reference.nasdaq_sector_map(_nasdaq_snapshots())
    assert sectors["BIG"] == "Information Technology"
    assert sectors["EDGE"] == "Financials"
    assert sectors["GONE"] == "Health Care"


def test_nasdaq_sector_map_skips_a_label_with_no_gics_sector():
    snaps = [("2022-11-01", _snap(("ODD", 5e9, "Miscellaneous"), ("NONE", 5e9, "")))]
    assert reference.nasdaq_sector_map(snaps) == {}


def test_first_commit_of_each_month():
    log = [("2022-10-31", "a"), ("2022-11-01", "b"), ("2022-11-02", "c"),
           ("2022-12-02", "d"), ("2022-12-01", "e")]
    picked = reference.first_commit_of_each_month(log, "2022-11-01", "2022-12-31")
    assert picked == [("2022-11-01", "b"), ("2022-12-01", "e")]
