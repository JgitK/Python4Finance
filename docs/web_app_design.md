# Portfolio Optimizer Web App - Technical Design

## Part 1: Core Concepts (For R Users)

Before diving into the design, let's clarify some concepts that are different from R scripting.

---

### What is a Database?

In R, you store data in `.rds` files or CSVs. A **database** is similar but designed for:
- Multiple users accessing data simultaneously
- Fast lookups ("get me user #42's portfolio")
- Data that changes frequently

Think of it as a collection of data frames (called "tables") that live on a server and can be queried with a language called SQL.

**R equivalent:**
```r
# In R, you might do:
portfolios <- readRDS("portfolios.rds")
user_portfolio <- portfolios %>% filter(user_id == 42)

# In a database (SQL), you'd write:
# SELECT * FROM portfolios WHERE user_id = 42
```

---

### What is an API?

Your R scripts run locally. An **API** (Application Programming Interface) lets other programs request data or actions from your server over the internet.

Think of it as a menu at a restaurant:
- The menu lists what you can order (endpoints)
- You make a request ("I want the /portfolio with $3500")
- The kitchen (backend) prepares it
- You get a response (JSON data with your allocation)

**Example:**
```
Request:  GET https://yourapp.com/api/portfolio?amount=3500
Response: {
  "stocks": [
    {"ticker": "BBVA", "shares": 24, "amount": 585.12},
    {"ticker": "TFPM", "shares": 15, "amount": 554.85},
    ...
  ],
  "total_invested": 3123.38,
  "cash_remaining": 376.62
}
```

Your React/web frontend calls these API endpoints to get data, then displays it nicely.

---

### How the Pieces Fit Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           YOUR WEB APP                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐    │
│   │  FRONTEND   │ ---> │   BACKEND   │ ---> │     DATABASE        │    │
│   │  (React)    │ <--- │   (Python)  │ <--- │     (Postgres)      │    │
│   └─────────────┘      └─────────────┘      └─────────────────────┘    │
│         │                    │                                          │
│    What user sees      Handles requests        Stores persistent        │
│    Buttons, forms      Runs calculations       data (users,             │
│    Charts, tables      Talks to database       portfolios, stocks)      │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    R PIPELINE (runs separately)                  │  │
│   │                                                                  │  │
│   │   00_daily_update.R  →  Runs daily, updates prices               │  │
│   │   01-06_modules.R    →  Runs weekly, generates portfolios        │  │
│   │                                                                  │  │
│   │   Output: Writes results to DATABASE so backend can read them    │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** Your R scripts don't change much. They just write their output to a database instead of `.rds` files, and the web app reads from that database.

---

## Part 2: Database Schema

A "schema" is the structure of your database - what tables exist and what columns they have.

### Table 1: `stocks`

Stores basic info about each stock in our universe.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| ticker | TEXT (primary key) | Stock symbol | "BBVA" |
| company_name | TEXT | Full company name | "Banco Bilbao Vizcaya" |
| sector | TEXT | Industry sector | "Finance" |
| current_price | DECIMAL | Latest price | 24.38 |
| price_updated_at | TIMESTAMP | When price was last updated | 2026-01-21 18:00:00 |

**R equivalent:** This is like your `metadata/filtered_tickers.csv` plus current prices.

---

### Table 2: `stock_prices`

Daily price history for each stock (what's currently in your `stocks/` folder).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| ticker | TEXT | Stock symbol | "BBVA" |
| date | DATE | Trading day | 2026-01-21 |
| open | DECIMAL | Opening price | 24.10 |
| high | DECIMAL | Daily high | 24.55 |
| low | DECIMAL | Daily low | 23.90 |
| close | DECIMAL | Closing price | 24.38 |
| adjusted | DECIMAL | Adjusted close | 24.38 |
| volume | BIGINT | Shares traded | 5420000 |

**Primary key:** (ticker, date) - meaning each ticker+date combo is unique.

**R equivalent:** This replaces all your `stocks/*.rds` files with one unified table.

---

### Table 3: `analysis_runs`

Tracks each time we run the full analysis pipeline (Modules 2-6).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| run_id | INTEGER (primary key) | Unique ID for this run | 1 |
| run_date | TIMESTAMP | When analysis was run | 2026-01-19 02:00:00 |
| status | TEXT | Success/failed | "success" |
| sharpe_ratio | DECIMAL | Walk-forward Sharpe | 2.45 |
| notes | TEXT | Any notes/errors | "Weekly run" |

**Why this exists:** So we know which analysis generated which portfolio. Useful for debugging and history.

---

### Table 4: `portfolio_stocks`

The 12 stocks selected by each analysis run (output of Module 3).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| run_id | INTEGER | Which analysis run | 1 |
| ticker | TEXT | Stock symbol | "BBVA" |
| rank | INTEGER | Position in portfolio (1-12) | 1 |
| weight | DECIMAL | Optimal weight (0-1) | 0.1699 |
| sharpe_ratio | DECIMAL | Stock's Sharpe | 1.31 |
| avg_correlation | DECIMAL | Avg correlation with others | 0.216 |
| ichimoku_signal | TEXT | BULLISH/NEUTRAL/BEARISH | "BULLISH" |

**Primary key:** (run_id, ticker)

**R equivalent:** This is your `analysis/final_portfolio.rds` + `analysis/optimal_weights.rds` combined.

---

### Table 5: `bench_stocks`

The "bench" - next 10 alternates ready to promote.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| run_id | INTEGER | Which analysis run | 1 |
| ticker | TEXT | Stock symbol | "VIST" |
| rank | INTEGER | Bench position (1-10) | 1 |
| sector | TEXT | Sector | "Energy" |
| sharpe_ratio | DECIMAL | Stock's Sharpe | 1.15 |
| notes | TEXT | Why not in top 12 | "Correlated with TRGP" |

**Primary key:** (run_id, ticker)

**R equivalent:** This is NEW - we'll modify Module 3 to output this.

---

### Table 6: `users`

Registered users of the app.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| user_id | INTEGER (primary key) | Unique user ID | 42 |
| email | TEXT | User's email | "jackson@email.com" |
| created_at | TIMESTAMP | When they signed up | 2026-01-15 10:30:00 |

---

### Table 7: `user_portfolios`

Each user's actual holdings (what they bought).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | INTEGER (primary key) | Unique record ID | 1 |
| user_id | INTEGER | Which user | 42 |
| ticker | TEXT | Stock symbol | "BBVA" |
| shares | INTEGER | How many shares they own | 24 |
| purchase_price | DECIMAL | Price when they "bought" | 24.38 |
| purchase_date | DATE | When they added it | 2026-01-21 |
| sold_at | DECIMAL | Price when sold (NULL if still held) | NULL |
| sold_date | DATE | When sold (NULL if still held) | NULL |
| status | TEXT | "held" or "sold" | "held" |

**R equivalent:** This is NEW - tracks what users actually do.

---

### Table 8: `price_alerts`

Alerts users set (e.g., "tell me when BBVA is up 15%").

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| alert_id | INTEGER (primary key) | Unique alert ID | 1 |
| user_id | INTEGER | Which user | 42 |
| ticker | TEXT | Stock to watch | "BBVA" |
| condition | TEXT | "above" or "below" | "above" |
| target_percent | DECIMAL | Percent change from purchase | 15.0 |
| triggered | BOOLEAN | Has it fired yet? | FALSE |
| created_at | TIMESTAMP | When alert was set | 2026-01-21 |

---

### Schema Diagram (Relationships)

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   users     │       │  analysis_runs  │       │     stocks      │
├─────────────┤       ├─────────────────┤       ├─────────────────┤
│ user_id (PK)│       │ run_id (PK)     │       │ ticker (PK)     │
│ email       │       │ run_date        │       │ company_name    │
│ created_at  │       │ sharpe_ratio    │       │ sector          │
└──────┬──────┘       └────────┬────────┘       │ current_price   │
       │                       │                └────────┬────────┘
       │                       │                         │
       ▼                       ▼                         │
┌─────────────────┐   ┌─────────────────┐               │
│ user_portfolios │   │ portfolio_stocks│◄──────────────┘
├─────────────────┤   ├─────────────────┤
│ user_id (FK)    │   │ run_id (FK)     │
│ ticker (FK)     │   │ ticker (FK)     │
│ shares          │   │ weight          │
│ purchase_price  │   │ rank            │
└─────────────────┘   └─────────────────┘
                              │
                              │ (same structure)
                              ▼
                      ┌─────────────────┐
                      │  bench_stocks   │
                      ├─────────────────┤
                      │ run_id (FK)     │
                      │ ticker (FK)     │
                      │ rank            │
                      └─────────────────┘

PK = Primary Key (unique identifier)
FK = Foreign Key (references another table)
```

---

## Part 3: API Endpoints

These are the "menu items" your frontend can request.

### Authentication Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/api/auth/signup` | Create account | `{email, password}` | `{user_id, token}` |
| POST | `/api/auth/login` | Log in | `{email, password}` | `{user_id, token}` |
| POST | `/api/auth/logout` | Log out | (token in header) | `{success: true}` |

---

### Portfolio Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio?amount=3500` | Get recommended allocation for an amount |
| GET | `/api/portfolio/latest` | Get the latest top 12 stocks (no amount) |
| GET | `/api/bench` | Get the current bench (10 alternates) |

**Example: GET `/api/portfolio?amount=3500`**

```json
{
  "generated_on": "2026-01-19",
  "sharpe_ratio": 2.45,
  "stocks": [
    {
      "ticker": "BBVA",
      "company_name": "Banco Bilbao Vizcaya",
      "sector": "Finance",
      "shares": 24,
      "price": 24.38,
      "amount": 585.12,
      "weight": 0.17,
      "ichimoku_signal": "BULLISH"
    },
    ...
  ],
  "bench": [
    {
      "ticker": "VIST",
      "company_name": "Vista Energy",
      "sector": "Energy",
      "sharpe_ratio": 1.15
    },
    ...
  ],
  "summary": {
    "total_invested": 3123.38,
    "cash_remaining": 376.62,
    "efficiency": 0.89,
    "stocks_included": 8,
    "stocks_skipped": 4
  }
}
```

---

### User Holdings Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/holdings` | Get user's current holdings |
| POST | `/api/holdings` | Add a stock to holdings |
| PUT | `/api/holdings/{ticker}/sell` | Mark a stock as sold |
| POST | `/api/holdings/promote` | Promote a bench stock to holdings |

**Example: POST `/api/holdings`** (adding a stock)

Request:
```json
{
  "ticker": "BBVA",
  "shares": 24,
  "purchase_price": 24.38
}
```

Response:
```json
{
  "success": true,
  "holding_id": 1,
  "message": "Added 24 shares of BBVA"
}
```

**Example: PUT `/api/holdings/BBVA/sell`**

Request:
```json
{
  "sell_price": 28.50
}
```

Response:
```json
{
  "success": true,
  "ticker": "BBVA",
  "shares": 24,
  "purchase_price": 24.38,
  "sell_price": 28.50,
  "gain_loss": 98.88,
  "gain_loss_percent": 16.9,
  "suggested_replacements": [
    {"ticker": "VIST", "sector": "Energy", "correlation_with_portfolio": 0.18},
    {"ticker": "COKE", "sector": "Consumer Staples", "correlation_with_portfolio": 0.21}
  ]
}
```

---

### Stock Info Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stock/{ticker}` | Get info about a specific stock |
| GET | `/api/stock/{ticker}/price-history?days=30` | Get recent price history |

---

### Alert Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | Get user's active alerts |
| POST | `/api/alerts` | Create a new price alert |
| DELETE | `/api/alerts/{alert_id}` | Remove an alert |

---

### Performance Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/performance` | Get user's portfolio performance |
| GET | `/api/performance/history` | Get historical walk-forward results |

**Example: GET `/api/performance`**

```json
{
  "user_id": 42,
  "holdings": [
    {
      "ticker": "BBVA",
      "shares": 24,
      "purchase_price": 24.38,
      "current_price": 28.50,
      "gain_loss": 98.88,
      "gain_loss_percent": 16.9
    },
    ...
  ],
  "total_invested": 3123.38,
  "current_value": 3589.22,
  "total_gain_loss": 465.84,
  "total_gain_loss_percent": 14.9
}
```

---

## Part 4: Validation Tests

These tests verify our design makes sense BEFORE we write code.

### Test 1: Can we store all the R pipeline output?

**Question:** Does our schema capture everything the R scripts produce?

| R Output | Database Table | Covered? |
|----------|---------------|----------|
| `stocks/*.rds` (price history) | `stock_prices` | ✓ |
| `metadata/filtered_tickers.csv` | `stocks` | ✓ |
| `analysis/final_portfolio.rds` | `portfolio_stocks` | ✓ |
| `analysis/optimal_weights.rds` | `portfolio_stocks.weight` | ✓ |
| `analysis/ichimoku_validation.rds` | `portfolio_stocks.ichimoku_signal` | ✓ |
| `analysis/candidate_stocks.rds` (bench) | `bench_stocks` | ✓ |

**Result:** ✓ PASS - All R outputs have a home in the database.

---

### Test 2: Can we calculate the allocation?

**Question:** Given an investment amount, can we compute shares to buy?

**Input:** User wants to invest $3,500

**Required data:**
1. Latest `portfolio_stocks` (from most recent `analysis_runs`) → Have it
2. Current prices (`stocks.current_price`) → Have it
3. Weights (`portfolio_stocks.weight`) → Have it

**Calculation:**
```
For each stock:
  dollar_amount = weight × investment_amount
  shares = floor(dollar_amount / current_price)
  actual_invested = shares × current_price
```

**Result:** ✓ PASS - We have all required data.

---

### Test 3: Can we track sells and suggest replacements?

**Question:** When user sells a stock, can we suggest bench replacements?

**Scenario:** User sells TFPM after 18% gain

**Required data:**
1. User's current holdings (`user_portfolios`) → Have it
2. Bench stocks (`bench_stocks`) → Have it
3. Correlation between bench stocks and remaining portfolio → ❓

**Gap found:** We need to store the correlation matrix to suggest low-correlation replacements.

**Fix:** Add table `stock_correlations`:

| Column | Type | Description |
|--------|------|-------------|
| run_id | INTEGER | Which analysis run |
| ticker_a | TEXT | First stock |
| ticker_b | TEXT | Second stock |
| correlation | DECIMAL | Correlation coefficient |

**Result:** ✓ PASS (after adding `stock_correlations` table)

---

### Test 4: Can we trigger price alerts?

**Question:** Can we detect when a stock is up 15% from purchase?

**Required data:**
1. User's purchase price (`user_portfolios.purchase_price`) → Have it
2. Current price (`stocks.current_price`) → Have it
3. Alert threshold (`price_alerts.target_percent`) → Have it

**Calculation:**
```
percent_change = (current_price - purchase_price) / purchase_price × 100
if percent_change >= target_percent AND alert not triggered:
  send notification
  mark alert as triggered
```

**Result:** ✓ PASS - We have all required data.

---

### Test 5: Can we show performance history?

**Question:** Can we show how walk-forward Sharpe has changed over time?

**Required data:**
1. Historical analysis runs (`analysis_runs.sharpe_ratio`) → Have it
2. Run dates (`analysis_runs.run_date`) → Have it

**Result:** ✓ PASS - We can plot Sharpe ratio over time.

---

### Test 6: Data freshness validation

**Question:** How do we know if prices are stale?

**Check:** `stocks.price_updated_at`

**Rule:**
- If `price_updated_at` < today: show warning "Prices as of {date}"
- If `price_updated_at` < 3 days ago: show error "Prices are stale"

**Result:** ✓ PASS - We track when prices were updated.

---

### Test 7: User flow validation

**Question:** Does the API support the full user journey?

| User Action | API Endpoint | Works? |
|-------------|--------------|--------|
| Signs up | `POST /api/auth/signup` | ✓ |
| Enters $3,500 | `GET /api/portfolio?amount=3500` | ✓ |
| Sees allocation | Response includes stocks + amounts | ✓ |
| Clicks "I bought these" | `POST /api/holdings` (multiple) | ✓ |
| Checks performance later | `GET /api/performance` | ✓ |
| Stock up 18%, clicks "Sell" | `PUT /api/holdings/TFPM/sell` | ✓ |
| Sees replacement suggestions | Response includes `suggested_replacements` | ✓ |
| Promotes VIST from bench | `POST /api/holdings/promote` | ✓ |
| Sets alert for +15% | `POST /api/alerts` | ✓ |

**Result:** ✓ PASS - Full user journey is supported.

---

## Part 5: Summary

### What We Designed

1. **8 database tables** that store everything from stock prices to user portfolios
2. **15+ API endpoints** that let the frontend request data and perform actions
3. **7 validation tests** that confirm the design works before writing code

### What R Scripts Need to Change

| Script | Change Needed |
|--------|---------------|
| Module 1 | Write to `stock_prices` table instead of `.rds` files |
| Module 3 | Output bench stocks (next 10) to `bench_stocks` table |
| Module 3 | Save correlation matrix to `stock_correlations` table |
| Module 5 | Write optimal weights to `portfolio_stocks` table |
| Module 6 | Write run metadata to `analysis_runs` table |
| NEW: `00_daily_update.R` | Append daily prices to `stock_prices` |

### Next Steps

1. Set up a Postgres database with these tables
2. Modify R scripts to write to database
3. Build the Python/FastAPI backend
4. Build the React frontend
5. Deploy and test

---

## Questions?

If any part of this is unclear, let me know and I'll explain further!
