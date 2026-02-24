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
from webapp.api import stock_info_service
from webapp.api import efficient_frontier_service

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
def get_portfolio(
    amount: float = Query(..., description="Investment amount in dollars"),
    portfolio_type: str = Query("max_sharpe", description="Portfolio optimization strategy"),
    risk_tolerance: float = Query(None, description="Risk tolerance 0-1 (optional, for custom blend)")
):
    """
    Calculate portfolio allocation for a given investment amount.

    Args:
        amount: Dollar amount to invest (required, must be positive)
        portfolio_type: Optimization strategy - one of:
            - max_sharpe: Maximum Sharpe Ratio (best risk-adjusted returns)
            - min_variance: Minimum Variance (lowest volatility)
            - max_sortino: Maximum Sortino Ratio (best downside risk-adjusted)
            - min_cvar: Minimum CVaR (tail risk protection)
            - risk_parity: Risk Parity (equal risk contribution)
            - equal_weight: Equal Weight (simple 1/N)
        risk_tolerance: Optional 0-1 value to blend max_sharpe with min_variance

    Returns:
        - stocks: List of stocks with shares to buy
        - total_invested: Actual amount invested
        - cash_remaining: Leftover cash (couldn't buy partial shares)
        - efficiency: Percentage of money invested
        - portfolio_type: The strategy used
    """
    # Validate the amount
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero"
        )

    # Validate risk_tolerance if provided
    if risk_tolerance is not None:
        if risk_tolerance < 0 or risk_tolerance > 1:
            raise HTTPException(
                status_code=400,
                detail="Risk tolerance must be between 0 and 1"
            )

    # Calculate allocation using our service
    result = portfolio_service.calculate_allocation(amount, portfolio_type, risk_tolerance)

    return result


@app.get("/api/portfolio-types")
def get_portfolio_types():
    """
    Get available portfolio optimization strategies.

    Returns list of portfolio types with their descriptions.
    """
    return {
        'types': portfolio_service.get_available_portfolio_types(),
        'default': 'max_sharpe'
    }


# ============================================================================
# ENDPOINT: Bench (Alternate Stocks)
# ============================================================================
# GET /api/bench?portfolio_type=max_sharpe
#
# Returns the "bench" - stocks that are ready to replace portfolio stocks
# if you sell one (e.g., after a 15% gain).
# Each strategy has its own bench stocks.

@app.get("/api/bench")
def get_bench(
    portfolio_type: str = Query("max_sharpe", description="Portfolio strategy to get bench for")
):
    """
    Get the bench stocks (alternates ready to promote) for a strategy.

    Each strategy has its own bench of alternate stocks that didn't make
    the final selection but are ready to replace any stock you sell.

    Args:
        portfolio_type: Strategy to get bench for (max_sharpe, min_variance, etc.)
    """
    result = portfolio_service.get_bench(portfolio_type)

    return result


# ============================================================================
# ENDPOINT: Strategy Metadata
# ============================================================================
# GET /api/strategy-metadata
#
# Returns metadata about each strategy's portfolio (stock count, sectors, etc.)

@app.get("/api/strategy-metadata")
def get_strategy_metadata():
    """
    Get metadata about each strategy's portfolio.

    Returns summary stats for each strategy including:
    - Number of stocks
    - Number of sectors
    - Average Sharpe ratio
    - Average Sortino ratio
    - Average correlation
    - List of tickers
    """
    return portfolio_service.get_strategy_metadata()


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


# ============================================================================
# ENDPOINT: Stock Info
# ============================================================================
# GET /api/stock/{ticker}/info
#
# Returns company information (name, sector, industry, description, market cap).

@app.get("/api/stock/{ticker}/info")
def get_stock_info(ticker: str):
    """
    Get company information for a specific stock.

    Args:
        ticker: Stock symbol

    Returns:
        - company_name: Full company name
        - sector: Business sector
        - industry: Specific industry
        - description: Company business summary
        - market_cap: Market capitalization
        - market_cap_formatted: Human-readable market cap
    """
    result = stock_info_service.get_stock_info(ticker.upper())
    return result


# ============================================================================
# ENDPOINT: Efficient Frontier
# ============================================================================
# GET /api/efficient-frontier
#
# Returns portfolio simulation data for the efficient frontier visualization.

@app.get("/api/efficient-frontier")
def get_efficient_frontier():
    """
    Get efficient frontier data for all simulated portfolios.

    Returns:
        - portfolios: Array of 10,000 portfolio simulations
        - optimal: Portfolio with maximum Sharpe ratio
        - min_variance: Portfolio with minimum risk
        - risk_free_rate: Risk-free rate used in calculations
        - total_portfolios: Number of portfolios in simulation
    """
    try:
        result = efficient_frontier_service.get_efficient_frontier_data()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
