// Pure helpers for chapter 7: error bars, the spread of bootstrap weights,
// the ranking of the scorecard and the per-window differences.
// No DOM, no React.

import { standardErrorRange } from "@/lib/portfolio";
import type { Scorecard } from "@/lib/types";

// ─── Error bars ──────────────────────────────────────────────────────────────

export interface ErrorRow {
  ticker: string;
  sector: string;
  /** The expected annual return that the optimizer used. */
  ret: number;
  /** The 95% range. */
  low: number;
  high: number;
  /** The weight of the max Sharpe portfolio, or null when unknown. */
  weight: number | null;
  /** True when the 95% range holds 0 or less. */
  spansZero: boolean;
}

/** One row for each ticker, sorted by expected return, highest first. All arrays are in the order of `tickers`. */
export function buildErrorRows(
  tickers: readonly string[],
  sectors: readonly string[],
  annualReturn: readonly number[],
  annualVol: readonly number[],
  years: number,
  weights: readonly number[] | null,
): ErrorRow[] {
  const rows: ErrorRow[] = [];
  tickers.forEach((ticker, i) => {
    const r = annualReturn[i];
    const v = annualVol[i];
    if (!Number.isFinite(r) || !Number.isFinite(v) || !(years > 0)) return;
    const { low, high } = standardErrorRange(r, v, years);
    rows.push({ ticker, sector: sectors[i] ?? "Unknown", ret: r, low, high, weight: weights ? (weights[i] ?? null) : null, spansZero: low <= 0 });
  });
  return rows.sort((a, b) => b.ret - a.ret || a.ticker.localeCompare(b.ticker));
}

// ─── Bootstrap ───────────────────────────────────────────────────────────────

/** The q-quantile (0 to 1) of an ascending array, by linear interpolation. NaN for an empty array. */
export function quantile(sorted: readonly number[], q: number): number {
  const n = sorted.length;
  if (n === 0) return NaN;
  const pos = Math.min(Math.max(q, 0), 1) * (n - 1);
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export interface Spread {
  ticker: string;
  min: number;
  p10: number;
  median: number;
  p90: number;
  max: number;
}

/** How much the weight of each ticker moves across the bootstrap samples. */
export function weightSpread(samples: readonly { weights: number[] }[], tickers: readonly string[]): Spread[] {
  return tickers.map((ticker, i) => {
    const v = samples.map((s) => s.weights[i]).filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
    return { ticker, min: quantile(v, 0), p10: quantile(v, 0.1), median: quantile(v, 0.5), p90: quantile(v, 0.9), max: quantile(v, 1) };
  });
}

// ─── Scorecard ───────────────────────────────────────────────────────────────

export interface Ranking {
  /** The rows with a mean Sharpe, best first. */
  order: string[];
  /** 1 = best. Null when the optimizer has no mean Sharpe. */
  optimizerRank: number | null;
}

export function rankByMeanSharpe(rows: Scorecard["rows"]): Ranking {
  const measured = rows.filter((r) => r.meanSharpe !== null && Number.isFinite(r.meanSharpe));
  const order = measured.sort((a, b) => (b.meanSharpe as number) - (a.meanSharpe as number)).map((r) => r.name);
  const k = order.indexOf("Optimizer");
  return { order, optimizerRank: k >= 0 ? k + 1 : null };
}

export interface WindowDiff {
  date: string;
  portfolio: number;
  benchmark: number;
  /** portfolio - benchmark. */
  diff: number;
}

/** The per-window differences, sorted by date. Any length, also 0. */
export function windowDiffs(perWindow: Scorecard["perWindow"] | undefined | null): WindowDiff[] {
  return (perWindow ?? [])
    .filter((w) => Number.isFinite(w.portfolioReturn) && Number.isFinite(w.benchmarkReturn))
    .map((w) => ({ date: w.date, portfolio: w.portfolioReturn, benchmark: w.benchmarkReturn, diff: w.portfolioReturn - w.benchmarkReturn }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

/** The count of windows where the portfolio beat the benchmark. */
export function winCount(diffs: readonly WindowDiff[]): number {
  return diffs.filter((d) => d.diff > 0).length;
}

/** How many times larger a is than b, or null when b is not above 0. */
export function ratio(a: number, b: number): number | null {
  return b > 0 && Number.isFinite(a) ? a / b : null;
}
