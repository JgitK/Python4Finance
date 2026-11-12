// The data contract. quant/export_web.py writes these files to
// public/data/. These types must agree with docs/web_plan.md exactly.
// All returns are fractions (0.18 is +18%). All dates are YYYY-MM-DD.

/** The ranking window. Trading days: 21, 63, 126, 252, 504, 1260. */
export type WindowKey = "1M" | "3M" | "6M" | "1Y" | "2Y" | "5Y";

/** meta.json */
export interface Meta {
  /** The last price date. */
  asOf: string;
  universe: "sp500";
  /** 0.045 */
  riskFree: number;
  /** 252 */
  tradingDays: number;
  windows: { key: WindowKey; days: number; effect: string; label: string }[];
  /** Sorted. */
  sectors: string[];
  /** The union of the tickers in leaders.json. */
  tickers: { ticker: string; sector: string; lastPrice: number }[];
  benchmark: "SPY";
}

/** One row of leaders.json: a top-5 stock of a sector for one window. */
export interface Leader {
  ticker: string;
  sector: string;
  /** 1 to 5 inside the sector. */
  rank: number;
  /** Over the window. */
  cumReturn: number;
  /** From the daily returns of the window. */
  annualVol: number;
  /** cumReturn - 1.96 * annualVol * sqrt(days/252) */
  rangeLow: number;
  rangeHigh: number;
  /** Top 5 of its sector on 3M, 6M and 1Y. */
  stable: boolean;
}

/** leaders.json */
export type Leaders = Record<WindowKey, Leader[]>;

/**
 * returns.json: daily simple returns for the last 504 trading days, for
 * each ticker of meta.tickers and for SPY. null where a price is missing.
 */
export interface Returns {
  dates: string[];
  series: Record<string, (number | null)[]>;
}

/**
 * ichimoku/<TICKER>.json: the last 252 trading days, plus the 26 days of
 * span A and span B that lie ahead of the last date.
 */
export interface Ichimoku {
  ticker: string;
  dates: string[];
  close: (number | null)[];
  conversion: (number | null)[];
  base: (number | null)[];
  /** Already moved 26 days ahead. */
  spanA: (number | null)[];
  spanB: (number | null)[];
  lagging: (number | null)[];
  /** 0 to 3 on the last date. */
  score: number;
  signals: {
    priceAboveCloud: boolean;
    conversionAboveBase: boolean;
    laggingAbovePrice: boolean;
  };
}

/** scorecard.json: from the existing output files and docs/context.md. */
export interface Scorecard {
  /** 85 */
  windows: number;
  /** 180 */
  holdDays: number;
  inSampleSharpe: number;
  realizedSharpe: number;
  rows: {
    name: "Optimizer" | "Equal weight" | "SPY" | "Random order";
    meanSharpe: number | null;
    medianExcess: number | null;
    winReturn: number | null;
    winSharpe: number | null;
    note: string;
  }[];
  perWindow: {
    date: string;
    portfolioReturn: number;
    benchmarkReturn: number;
    portfolioSharpe: number;
    benchmarkSharpe: number;
  }[];
}
