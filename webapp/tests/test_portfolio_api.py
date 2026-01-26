# ============================================================================
# Tests for Portfolio API
# ============================================================================
# These tests verify that our API endpoints work correctly.
#
# We write tests FIRST, before writing the actual code.
# This is called "Test-Driven Development" (TDD).
#
# The pattern:
#   1. Write a test that describes what SHOULD happen
#   2. Run the test (it fails - the code doesn't exist yet)
#   3. Write the code to make the test pass
#   4. Run the test again (it passes!)
#   5. Repeat

import pytest
from fastapi.testclient import TestClient

# Import our app
from webapp.api.main import app

# Create a test client - this lets us call the API without running a server
client = TestClient(app)


# ============================================================================
# TEST: Root endpoint works
# ============================================================================
def test_root_endpoint():
    """The root endpoint should return the HTML page."""
    response = client.get("/")

    # Check status code is 200 (OK)
    assert response.status_code == 200

    # Check the response is HTML
    assert "text/html" in response.headers["content-type"]
    assert "Portfolio Optimizer" in response.text


# ============================================================================
# TEST: Health endpoint works
# ============================================================================
def test_health_endpoint():
    """The health endpoint should return status info."""
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ============================================================================
# TEST: Portfolio endpoint returns allocation
# ============================================================================
def test_portfolio_endpoint_returns_allocation():
    """
    GET /api/portfolio?amount=3500 should return:
    - A list of stocks with shares to buy
    - Total invested amount
    - Cash remaining
    """
    response = client.get("/api/portfolio?amount=3500")

    # Should succeed
    assert response.status_code == 200

    data = response.json()

    # Should have these fields
    assert "stocks" in data
    assert "total_invested" in data
    assert "cash_remaining" in data
    assert "efficiency" in data

    # Stocks should be a list
    assert isinstance(data["stocks"], list)

    # Total invested should not exceed the amount
    assert data["total_invested"] <= 3500

    # Cash remaining should be non-negative
    assert data["cash_remaining"] >= 0

    # Efficiency should be between 0 and 1
    assert 0 <= data["efficiency"] <= 1


# ============================================================================
# TEST: Portfolio endpoint validates input
# ============================================================================
def test_portfolio_endpoint_rejects_invalid_amount():
    """
    GET /api/portfolio with invalid amount should return an error.
    """
    # Negative amount
    response = client.get("/api/portfolio?amount=-100")
    assert response.status_code == 400  # Bad Request

    # Zero amount
    response = client.get("/api/portfolio?amount=0")
    assert response.status_code == 400


# ============================================================================
# TEST: Portfolio endpoint requires amount parameter
# ============================================================================
def test_portfolio_endpoint_requires_amount():
    """
    GET /api/portfolio without amount should return an error.
    """
    response = client.get("/api/portfolio")

    # FastAPI returns 422 for missing required parameters
    assert response.status_code == 422


# ============================================================================
# TEST: Each stock in response has required fields
# ============================================================================
def test_portfolio_stocks_have_required_fields():
    """
    Each stock in the response should have ticker, shares, price, amount.
    """
    response = client.get("/api/portfolio?amount=3500")
    assert response.status_code == 200

    data = response.json()

    # Check each stock has required fields
    for stock in data["stocks"]:
        assert "ticker" in stock
        assert "shares" in stock
        assert "price" in stock
        assert "amount" in stock
        assert "sector" in stock

        # Shares should be a positive integer
        assert isinstance(stock["shares"], int)
        assert stock["shares"] > 0

        # Amount should equal shares * price (approximately)
        expected_amount = stock["shares"] * stock["price"]
        assert abs(stock["amount"] - expected_amount) < 0.01


# ============================================================================
# TEST: Bench endpoint returns alternates
# ============================================================================
def test_bench_endpoint_returns_alternates():
    """
    GET /api/bench should return a list of alternate stocks.
    """
    response = client.get("/api/bench")

    assert response.status_code == 200

    data = response.json()

    # Should have stocks
    assert "stocks" in data
    assert isinstance(data["stocks"], list)

    # Each bench stock should have these fields
    for stock in data["stocks"]:
        assert "ticker" in stock
        assert "sector" in stock
        assert "sharpe_ratio" in stock


# ============================================================================
# TEST: Ichimoku endpoint returns chart data
# ============================================================================
def test_ichimoku_endpoint_returns_data():
    """
    GET /api/stock/{ticker}/ichimoku should return OHLC + Ichimoku data.
    """
    response = client.get("/api/stock/BBVA/ichimoku")

    assert response.status_code == 200

    data = response.json()

    # Should have ticker and data array
    assert data["ticker"] == "BBVA"
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0

    # Each data point should have required fields
    point = data["data"][0]
    assert "date" in point
    assert "open" in point
    assert "high" in point
    assert "low" in point
    assert "close" in point
    assert "tenkan_sen" in point
    assert "kijun_sen" in point
    assert "senkou_span_a" in point
    assert "senkou_span_b" in point


# ============================================================================
# TEST: Ichimoku endpoint rejects invalid tickers
# ============================================================================
def test_ichimoku_endpoint_rejects_invalid_ticker():
    """
    GET /api/stock/{ticker}/ichimoku with invalid ticker should return 404.
    """
    response = client.get("/api/stock/INVALID/ichimoku")

    assert response.status_code == 404
