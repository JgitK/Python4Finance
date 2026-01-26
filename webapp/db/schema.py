# ============================================================================
# Database Schema
# ============================================================================
# This file defines the structure of our database tables.
#
# We're using SQLite which stores everything in a single file (portfolio.db).
# No separate database server needed - perfect for getting started.
#
# Later, you can switch to Postgres by just changing the connection string.

import sqlite3
from pathlib import Path

# Database file location (in the webapp/db folder)
DB_PATH = Path(__file__).parent / "portfolio.db"


def get_connection():
    """
    Get a connection to the database.

    In R terms, this is like:
        conn <- dbConnect(RSQLite::SQLite(), "portfolio.db")
    """
    conn = sqlite3.connect(DB_PATH)
    # This makes rows behave like dictionaries (access by column name)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """
    Create all database tables if they don't exist.

    This is safe to run multiple times - it won't destroy existing data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # Table: stocks
    # Basic info about each stock in our universe
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            current_price REAL,
            price_updated_at TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # Table: analysis_runs
    # Tracks each time we run the full analysis pipeline
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL,
            status TEXT NOT NULL,
            sharpe_ratio REAL,
            notes TEXT
        )
    """)

    # -------------------------------------------------------------------------
    # Table: portfolio_stocks
    # The 12 stocks selected by each analysis run
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_stocks (
            run_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            rank INTEGER NOT NULL,
            weight REAL NOT NULL,
            sharpe_ratio REAL,
            avg_correlation REAL,
            ichimoku_signal TEXT,
            PRIMARY KEY (run_id, ticker),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id),
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        )
    """)

    # -------------------------------------------------------------------------
    # Table: bench_stocks
    # The "bench" - next 10 alternates ready to promote
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bench_stocks (
            run_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            rank INTEGER NOT NULL,
            sector TEXT,
            sharpe_ratio REAL,
            notes TEXT,
            PRIMARY KEY (run_id, ticker),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # -------------------------------------------------------------------------
    # Table: stock_correlations
    # Correlation matrix between portfolio stocks
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_correlations (
            run_id INTEGER NOT NULL,
            ticker_a TEXT NOT NULL,
            ticker_b TEXT NOT NULL,
            correlation REAL NOT NULL,
            PRIMARY KEY (run_id, ticker_a, ticker_b),
            FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id)
        )
    """)

    # -------------------------------------------------------------------------
    # Table: users
    # Registered users of the app
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # -------------------------------------------------------------------------
    # Table: user_portfolios
    # Each user's actual holdings (what they bought)
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            shares INTEGER NOT NULL,
            purchase_price REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            sold_at REAL,
            sold_date TEXT,
            status TEXT DEFAULT 'held',
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        )
    """)

    # -------------------------------------------------------------------------
    # Table: price_alerts
    # Alerts users set (e.g., "tell me when BBVA is up 15%")
    # -------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            condition TEXT NOT NULL,
            target_percent REAL NOT NULL,
            triggered INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        )
    """)

    conn.commit()
    conn.close()

    print(f"Database created at: {DB_PATH}")
    return DB_PATH


def verify_tables():
    """
    Verify all tables were created correctly.
    Returns a list of table names.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    return tables


# ============================================================================
# Run this file directly to create the database
# ============================================================================
if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()

    print("\nVerifying tables...")
    tables = verify_tables()
    print(f"Tables created: {tables}")

    print("\nDatabase setup complete!")
