// The portfolio math of the page. Pure functions. No DOM.
//
// These functions follow quant/optimize.py and quant/allocate.py, so the
// page and the pipeline give the same answers:
// - sample covariance (divide by n - 1), as pandas DataFrame.cov()
// - annual values: multiply the daily mean by 252, the daily variance by 252
// - risk-free rate 0.045
// - random weights: uniform numbers divided by their sum (random_weights)
//
// The random source is mulberry32, not numpy. Thus the clouds have the same
// method but not the same points as the Python run.

import type { Returns } from "./types";

export const TRADING_DAYS = 252;
export const RISK_FREE = 0.045;
export const DEFAULT_SEED = 42;

// ─── Returns ─────────────────────────────────────────────────────────────────

/** The daily returns of a basket, with only the days where all tickers have a value. */
export interface AlignedReturns {
  /** The kept dates. */
  dates: string[];
  /** The kept tickers, in the input order. */
  tickers: string[];
  /** The tickers with no series in returns.json. They are not in `tickers`. */
  missing: string[];
  /** rows[day][asset]: daily simple returns. */
  rows: number[][];
}

/** Keep the tickers that have a series. Drop each day where one of them is null. */
export function alignReturns(returns: Returns, tickers: string[]): AlignedReturns {
  const kept = tickers.filter((t) => Array.isArray(returns.series[t]));
  const missing = tickers.filter((t) => !Array.isArray(returns.series[t]));
  const cols = kept.map((t) => returns.series[t]);
  const dates: string[] = [];
  const rows: number[][] = [];
  for (let d = 0; d < returns.dates.length; d++) {
    const row: number[] = new Array(cols.length);
    let ok = true;
    for (let i = 0; i < cols.length; i++) {
      const v = cols[i][d];
      if (v === null || v === undefined || !Number.isFinite(v)) {
        ok = false;
        break;
      }
      row[i] = v;
    }
    if (ok && cols.length > 0) {
      dates.push(returns.dates[d]);
      rows.push(row);
    }
  }
  return { dates, tickers: kept, missing, rows };
}

/** The mean of each column. */
export function meanVector(rows: number[][]): number[] {
  const n = rows.length;
  const k = n > 0 ? rows[0].length : 0;
  const m = new Array<number>(k).fill(0);
  for (const row of rows) for (let i = 0; i < k; i++) m[i] += row[i];
  return m.map((s) => (n > 0 ? s / n : NaN));
}

/** The sample covariance matrix (divide by n - 1), as pandas cov(). */
export function covarianceMatrix(rows: number[][], mean: number[] = meanVector(rows)): number[][] {
  const n = rows.length;
  const k = mean.length;
  const c = Array.from({ length: k }, () => new Array<number>(k).fill(0));
  for (const row of rows) {
    for (let i = 0; i < k; i++) {
      const di = row[i] - mean[i];
      for (let j = i; j < k; j++) c[i][j] += di * (row[j] - mean[j]);
    }
  }
  const denom = n - 1;
  for (let i = 0; i < k; i++) {
    for (let j = i; j < k; j++) {
      const v = denom > 0 ? c[i][j] / denom : NaN;
      c[i][j] = v;
      c[j][i] = v;
    }
  }
  return c;
}

/** The correlation matrix from a covariance matrix. */
export function correlationMatrix(cov: number[][]): number[][] {
  const sd = cov.map((row, i) => Math.sqrt(row[i]));
  return cov.map((row, i) => row.map((v, j) => (i === j ? 1 : v / (sd[i] * sd[j]))));
}

// ─── One portfolio ───────────────────────────────────────────────────────────

/** Annual figures of one portfolio. */
export interface Performance {
  annualReturn: number;
  annualVol: number;
  /** NaN when the volatility is 0, as in optimize.py. */
  sharpe: number;
}

/** Measure one portfolio, as portfolio_performance in optimize.py. */
export function portfolioPerformance(
  weights: ArrayLike<number>,
  meanDaily: ArrayLike<number>,
  covDaily: number[][],
  tradingDays: number = TRADING_DAYS,
  riskFree: number = RISK_FREE,
): Performance {
  const k = meanDaily.length;
  let r = 0;
  let v = 0;
  for (let i = 0; i < k; i++) {
    r += weights[i] * meanDaily[i];
    const ci = covDaily[i];
    let s = 0;
    for (let j = 0; j < k; j++) s += ci[j] * weights[j];
    v += weights[i] * s;
  }
  const annualReturn = r * tradingDays;
  const annualVol = Math.sqrt(Math.max(0, v * tradingDays));
  const sharpe = annualVol === 0 ? NaN : (annualReturn - riskFree) / annualVol;
  return { annualReturn, annualVol, sharpe };
}

/** n weights of 1/n each. */
export function equalWeights(n: number): number[] {
  return new Array<number>(n).fill(1 / n);
}

// ─── Random source ───────────────────────────────────────────────────────────

/** A seeded random source. Each call gives a number in [0, 1). */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ─── Monte Carlo ─────────────────────────────────────────────────────────────

/** The random cloud. Index k is one portfolio. */
export interface MonteCarloResult {
  /** The count of portfolios. */
  n: number;
  /** The count of assets. */
  assets: number;
  /** Annual volatility of each portfolio. */
  risk: Float64Array;
  /** Annual return of each portfolio. */
  ret: Float64Array;
  /** Sharpe ratio of each portfolio. */
  sharpe: Float64Array;
  /** Flat weights: the weight of asset i in portfolio k is weights[k * assets + i]. */
  weights: Float64Array;
  /** The index of the highest Sharpe ratio. -1 when n is 0. */
  maxSharpeIndex: number;
  /** The index of the lowest volatility. -1 when n is 0. */
  minVolIndex: number;
}

export interface MonteCarloOptions {
  tradingDays?: number;
  riskFree?: number;
}

/** Fill a flat array with n sets of uniform random weights, each divided by its sum. */
export function randomWeights(n: number, assets: number, seed: number = DEFAULT_SEED): Float64Array {
  const rand = mulberry32(seed);
  const w = new Float64Array(n * assets);
  for (let k = 0; k < n; k++) {
    const o = k * assets;
    let s = 0;
    for (let i = 0; i < assets; i++) {
      // Keep each weight above 0, as numpy random() almost always does.
      const x = rand() || Number.EPSILON;
      w[o + i] = x;
      s += x;
    }
    for (let i = 0; i < assets; i++) w[o + i] /= s;
  }
  return w;
}

/** Measure each portfolio of a flat weight array. */
export function scoreWeights(
  weights: Float64Array,
  assets: number,
  meanDaily: ArrayLike<number>,
  covDaily: number[][],
  options: MonteCarloOptions = {},
): MonteCarloResult {
  const tradingDays = options.tradingDays ?? TRADING_DAYS;
  const riskFree = options.riskFree ?? RISK_FREE;
  const n = assets > 0 ? Math.floor(weights.length / assets) : 0;
  const cov = new Float64Array(assets * assets);
  for (let i = 0; i < assets; i++) for (let j = 0; j < assets; j++) cov[i * assets + j] = covDaily[i][j];
  const risk = new Float64Array(n);
  const ret = new Float64Array(n);
  const sharpe = new Float64Array(n);
  let maxSharpeIndex = -1;
  let minVolIndex = -1;
  for (let k = 0; k < n; k++) {
    const o = k * assets;
    let r = 0;
    let v = 0;
    for (let i = 0; i < assets; i++) {
      const wi = weights[o + i];
      r += wi * meanDaily[i];
      const ro = i * assets;
      let s = 0;
      for (let j = 0; j < assets; j++) s += cov[ro + j] * weights[o + j];
      v += wi * s;
    }
    const annualReturn = r * tradingDays;
    const annualVol = Math.sqrt(Math.max(0, v * tradingDays));
    const sr = annualVol === 0 ? NaN : (annualReturn - riskFree) / annualVol;
    ret[k] = annualReturn;
    risk[k] = annualVol;
    sharpe[k] = sr;
    if (!Number.isNaN(sr) && (maxSharpeIndex < 0 || sr > sharpe[maxSharpeIndex])) maxSharpeIndex = k;
    if (minVolIndex < 0 || annualVol < risk[minVolIndex]) minVolIndex = k;
  }
  return { n, assets, risk, ret, sharpe, weights, maxSharpeIndex, minVolIndex };
}

/**
 * Try n random portfolios, as monte_carlo_frontier in optimize.py.
 * The same inputs and seed give the same cloud.
 */
export function monteCarlo(
  meanDaily: ArrayLike<number>,
  covDaily: number[][],
  n: number = 10000,
  seed: number = DEFAULT_SEED,
  options: MonteCarloOptions = {},
): MonteCarloResult {
  const assets = meanDaily.length;
  return scoreWeights(randomWeights(n, assets, seed), assets, meanDaily, covDaily, options);
}

/** The weights of portfolio k of a Monte Carlo result, as a plain array. */
export function weightsAt(mc: MonteCarloResult, k: number): number[] {
  return Array.from(mc.weights.subarray(k * mc.assets, (k + 1) * mc.assets));
}

// ─── Frontier ────────────────────────────────────────────────────────────────

export interface FrontierPoint {
  risk: number;
  ret: number;
  /** The index of the point in the input arrays. */
  index: number;
}

/**
 * The upper-left edge of a cloud: the upper convex hull, from the point of
 * least risk to the point of most return. Sorted by risk.
 */
export function frontierHull(risk: ArrayLike<number>, ret: ArrayLike<number>): FrontierPoint[] {
  const idx: number[] = [];
  for (let k = 0; k < risk.length; k++) if (Number.isFinite(risk[k]) && Number.isFinite(ret[k])) idx.push(k);
  if (idx.length === 0) return [];
  idx.sort((a, b) => risk[a] - risk[b] || ret[b] - ret[a]);
  let top = idx[0];
  for (const k of idx) if (ret[k] > ret[top]) top = k;
  const hull: number[] = [];
  for (const k of idx) {
    if (hull.length > 0 && risk[k] === risk[hull[hull.length - 1]]) continue;
    while (hull.length >= 2) {
      const a = hull[hull.length - 2];
      const b = hull[hull.length - 1];
      // Remove b when it is on or under the line from a to k.
      const cross = (risk[b] - risk[a]) * (ret[k] - ret[a]) - (ret[b] - ret[a]) * (risk[k] - risk[a]);
      if (cross >= 0) hull.pop();
      else break;
    }
    hull.push(k);
    if (k === top) break;
  }
  return hull.map((k) => ({ risk: risk[k], ret: ret[k], index: k }));
}

// ─── Two assets ──────────────────────────────────────────────────────────────

export interface CurvePoint {
  /** The weight of asset A, from 0 to 1. */
  weightA: number;
  risk: number;
  ret: number;
}

/**
 * All mixes of two assets, from 100% in B (weightA 0) to 100% in A.
 * Give annual means and annual volatilities. rho is the correlation.
 */
export function twoAssetCurve(
  meanA: number,
  meanB: number,
  volA: number,
  volB: number,
  rho: number,
  steps: number = 50,
): CurvePoint[] {
  const out: CurvePoint[] = [];
  for (let s = 0; s <= steps; s++) {
    const w = s / steps;
    const v = w * w * volA * volA + (1 - w) * (1 - w) * volB * volB + 2 * w * (1 - w) * rho * volA * volB;
    out.push({ weightA: w, ret: w * meanA + (1 - w) * meanB, risk: Math.sqrt(Math.max(0, v)) });
  }
  return out;
}

// ─── Money ───────────────────────────────────────────────────────────────────

export interface AllocationRow {
  ticker: string;
  targetWeight: number;
  price: number;
  shares: number;
  cost: number;
  /** cost / total cost. 0 when the plan buys nothing. */
  actualWeight: number;
}

export interface AllocationPlan {
  /** In the order of the weights object. */
  rows: AllocationRow[];
  spent: number;
  /** The money that the plan does not spend. */
  cash: number;
  /** Tickers with a weight above 0 and no shares, sorted. */
  dropped: string[];
}

type Plan = Record<string, { shares: number; cost: number }>;

function summarise(weights: Record<string, number>, prices: Record<string, number>, amount: number, plan: Plan): AllocationPlan {
  const tickers = Object.keys(weights);
  const spent = tickers.reduce((s, t) => s + plan[t].cost, 0);
  const rows = tickers.map((t) => ({
    ticker: t,
    targetWeight: weights[t],
    price: prices[t],
    shares: plan[t].shares,
    cost: plan[t].cost,
    actualWeight: spent > 0 ? plan[t].cost / spent : 0,
  }));
  const dropped = tickers.filter((t) => weights[t] > 0 && plan[t].shares === 0).sort();
  return { rows, spent, cash: amount - spent, dropped };
}

function weightError(plan: Plan, weights: Record<string, number>, amount: number): number {
  let e = 0;
  for (const t of Object.keys(weights)) e += (plan[t].cost / amount - weights[t]) ** 2;
  return e;
}

/** Spend the cash that the first pass leaves, as top_up_shares in allocate.py. */
function topUp(plan: Plan, weights: Record<string, number>, prices: Record<string, number>, amount: number): Plan {
  const p: Plan = {};
  for (const t of Object.keys(plan)) p[t] = { ...plan[t] };
  const order = Object.keys(weights).sort();
  for (;;) {
    const spent = order.reduce((s, t) => s + p[t].cost, 0);
    const cash = amount - spent;
    let bestTicker: string | null = null;
    let bestError = weightError(p, weights, amount);
    for (const t of order) {
      if (prices[t] > cash) continue;
      const shares = p[t].shares + 1;
      const trial: Plan = { ...p, [t]: { shares, cost: shares * prices[t] } };
      const error = weightError(trial, weights, amount);
      if (error < bestError - 1e-15) {
        bestTicker = t;
        bestError = error;
      }
    }
    if (bestTicker === null) return p;
    p[bestTicker].shares += 1;
    p[bestTicker].cost = p[bestTicker].shares * prices[bestTicker];
  }
}

/**
 * Buy whole shares, as allocation_summary in allocate.py: round down, then
 * (by default) the top-up pass spends the cash where it helps the weights most.
 */
export function allocateWhole(
  weights: Record<string, number>,
  prices: Record<string, number>,
  amount: number,
  options: { topUp?: boolean } = {},
): AllocationPlan {
  let plan: Plan = {};
  for (const t of Object.keys(weights)) {
    const shares = Math.floor((amount * weights[t]) / prices[t]);
    plan[t] = { shares, cost: shares * prices[t] };
  }
  if (options.topUp ?? true) plan = topUp(plan, weights, prices, amount);
  return summarise(weights, prices, amount, plan);
}

/** Buy parts of a share, as allocate_fractional in allocate.py (round down to `decimals`). */
export function allocateFractional(
  weights: Record<string, number>,
  prices: Record<string, number>,
  amount: number,
  decimals: number = 6,
): AllocationPlan {
  if (decimals < 0) throw new Error("The count of decimals must not be below 0.");
  const scale = 10 ** decimals;
  const plan: Plan = {};
  for (const t of Object.keys(weights)) {
    const exact = (amount * weights[t]) / prices[t];
    // First round the scaled value to 3 decimals, then round it down. This
    // stops 28.999999999999996 from becoming 28.999999.
    const shares = Math.floor(Math.round(exact * scale * 1000) / 1000) / scale;
    plan[t] = { shares, cost: shares * prices[t] };
  }
  return summarise(weights, prices, amount, plan);
}

/** The smallest amount that can hold every weight with whole shares: max(price / weight). */
export function minimumInvestment(weights: Record<string, number>, prices: Record<string, number>): number {
  let m = 0;
  for (const t of Object.keys(weights)) if (weights[t] > 0) m = Math.max(m, prices[t] / weights[t]);
  return m;
}

// ─── Trust ───────────────────────────────────────────────────────────────────

export interface BootstrapPoint {
  risk: number;
  ret: number;
  sharpe: number;
  weights: number[];
}

export interface BootstrapOptions extends MonteCarloOptions {
  /** The count of random portfolios to search in each draw. Default 2000. */
  portfolios?: number;
}

/**
 * Resample the days with replacement `draws` times. For each sample, find
 * the maximum Sharpe portfolio in one fixed set of random weights. Each
 * point is measured with the statistics of its own sample.
 */
export function bootstrapMaxSharpe(
  rows: number[][],
  draws: number = 200,
  seed: number = DEFAULT_SEED,
  options: BootstrapOptions = {},
): BootstrapPoint[] {
  const T = rows.length;
  const assets = T > 0 ? rows[0].length : 0;
  if (T < 2 || assets === 0) return [];
  const weights = randomWeights(options.portfolios ?? 2000, assets, seed);
  const rand = mulberry32(seed + 1);
  const out: BootstrapPoint[] = [];
  const sample: number[][] = new Array(T);
  for (let d = 0; d < draws; d++) {
    for (let t = 0; t < T; t++) sample[t] = rows[Math.floor(rand() * T)];
    const mean = meanVector(sample);
    const cov = covarianceMatrix(sample, mean);
    const mc = scoreWeights(weights, assets, mean, cov, options);
    const k = mc.maxSharpeIndex >= 0 ? mc.maxSharpeIndex : 0;
    out.push({ risk: mc.risk[k], ret: mc.ret[k], sharpe: mc.sharpe[k], weights: weightsAt(mc, k) });
  }
  return out;
}

/** The 95% range of an annual return: se = annualVol / sqrt(years). */
export function standardErrorRange(
  annualReturn: number,
  annualVol: number,
  years: number,
  z: number = 1.96,
): { low: number; high: number; se: number } {
  const se = annualVol / Math.sqrt(years);
  return { low: annualReturn - z * se, high: annualReturn + z * se, se };
}
