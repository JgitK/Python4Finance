// Pure helpers for chapter 1. No DOM here, so Vitest can test them.

import type { Leader } from "@/lib/types";

/** The value at fraction q of a sorted array (linear steps). */
function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return 0;
  const p = (sorted.length - 1) * q;
  const i = Math.floor(p);
  return sorted[i] + (sorted[Math.min(i + 1, sorted.length - 1)] - sorted[i]) * (p - i);
}

/**
 * The x domain of the chart: zero and most of the dots, with a small margin.
 * A few big winners would squash all other dots, so the domain stops at the
 * 93rd percentile. A dot past the edge is pinned to the edge (see `pinX`).
 */
export function xDomain(leaders: Leader[]): [number, number] {
  const v = leaders.map((l) => l.cumReturn).sort((a, b) => a - b);
  let lo = Math.min(0, quantile(v, 0.03));
  let hi = Math.max(0, quantile(v, 0.93));
  if (hi - lo < 0.02) hi = lo + 0.1;
  const pad = (hi - lo) * 0.08;
  return [lo - pad, hi + pad];
}

/** Keep a value inside the domain (a dot past the edge sits on the edge). */
export function pinX(v: number, domain: [number, number]): number {
  return Math.min(Math.max(v, domain[0]), domain[1]);
}

export interface ClippedRange {
  /** The start of the line, inside the domain. */
  from: number;
  /** The end of the line, inside the domain. */
  to: number;
  /** True when the true range runs past the left edge. */
  clipLow: boolean;
  /** True when the true range runs past the right edge. */
  clipHigh: boolean;
}

/** Cut a range at the plot edge and say which ends were cut. */
export function clipRange(low: number, high: number, domain: [number, number]): ClippedRange {
  return {
    from: Math.max(low, domain[0]),
    to: Math.min(high, domain[1]),
    clipLow: low < domain[0],
    clipHigh: high > domain[1],
  };
}

/** "Pick for me": the rank-1 stock of each sector, best return first, up to `max`. */
export function pickForMe(leaders: Leader[], max: number): string[] {
  return leaders
    .filter((l) => l.rank === 1)
    .sort((a, b) => b.cumReturn - a.cumReturn)
    .slice(0, max)
    .map((l) => l.ticker);
}

/** The count of picked tickers in each sector. */
export function sectorCounts(basket: string[], sectorOf: (t: string) => string | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  for (const t of basket) {
    const s = sectorOf(t);
    if (s) out[s] = (out[s] ?? 0) + 1;
  }
  return out;
}

/** Why a click cannot add or remove a stock, or null when it can. */
export function basketHint(count: number, min: number, max: number): string | null {
  if (count >= max) return `The basket is full (${max} stocks). Remove one to add another.`;
  if (count < min) return `Pick at least ${min} stocks to build a portfolio.`;
  return null;
}
