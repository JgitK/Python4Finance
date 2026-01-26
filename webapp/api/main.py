# ============================================================================
# Portfolio Optimizer API - Main Entry Point
# ============================================================================
# This is where FastAPI handles incoming HTTP requests.
#
# Think of it like an R script that listens for requests instead of
# running once and stopping.

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import our service modules (the business logic)
from webapp.api import portfolio_service
from webapp.api import ichimoku_service

# Create the app
# This is like creating an empty "server" that will handle requests
app = FastAPI(
    title="Portfolio Optimizer API",
    description="API for the portfolio optimization web app",
    version="0.1.0"
)

# Path to static files (HTML, CSS, JS)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Mount static files directory
# This tells FastAPI: "serve files from /static/ URL path"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============================================================================
# ENDPOINT: Health Check (Hello World)
# ============================================================================
# This is our first endpoint. It just returns a message to prove the API works.
#
# The decorator @app.get("/") means:
#   - This function handles GET requests
#   - At the URL path "/" (the root, like going to google.com/)
#
# In R terms, this is like:
#   if (request$path == "/" && request$method == "GET") {
#       return(list(message = "Hello"))
#   }

@app.get("/")
def root():
    """Serve the main web page."""
    return FileResponse(STATIC_DIR / "index.html")


# ============================================================================
# ENDPOINT: Health Check with details
# ============================================================================
# A more detailed health check that we can use to verify the system status.

@app.get("/health")
def health_check():
    """Health check endpoint - returns system status."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "not connected yet"  # We'll update this later
    }


# ============================================================================
# ENDPOINT: Portfolio Allocation
# ============================================================================
# GET /api/portfolio?amount=3500
#
# This is the main endpoint. Given an investment amount, it returns
# a list of stocks with how many shares to buy.

@app.get("/api/portfolio")
def get_portfolio(amount: float = Query(..., description="Investment amount in dollars")):
    """
    Calculate portfolio allocation for a given investment amount.

    Args:
        amount: Dollar amount to invest (required, must be positive)

    Returns:
        - stocks: List of stocks with shares to buy
        - total_invested: Actual amount invested
        - cash_remaining: Leftover cash (couldn't buy partial shares)
        - efficiency: Percentage of money invested
    """
    # Validate the amount
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero"
        )

    # Calculate allocation using our service
    result = portfolio_service.calculate_allocation(amount)

    return result


# ============================================================================
# ENDPOINT: Bench (Alternate Stocks)
# ============================================================================
# GET /api/bench
#
# Returns the "bench" - stocks that are ready to replace portfolio stocks
# if you sell one (e.g., after a 15% gain).

@app.get("/api/bench")
def get_bench():
    """
    Get the bench stocks (alternates ready to promote).

    These are high-quality stocks that didn't make the final 12,
    but are ready to replace any stock you sell.
    """
    result = portfolio_service.get_bench()

    return result


# ============================================================================
# ENDPOINT: Ichimoku Chart Data
# ============================================================================
# GET /api/stock/{ticker}/ichimoku
#
# Returns OHLC price data plus Ichimoku indicator values for charting.

@app.get("/api/stock/{ticker}/ichimoku")
def get_stock_ichimoku(ticker: str):
    """
    Get Ichimoku chart data for a specific stock.

    Args:
        ticker: Stock symbol (must be in portfolio or bench)

    Returns:
        - ticker: The stock symbol
        - data: Array of daily values with OHLC and Ichimoku indicators
    """
    try:
        result = ichimoku_service.get_ichimoku_data(ticker)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
