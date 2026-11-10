// Pure helpers for chapter 2. No DOM here, so Vitest can test them.

import type { Ichimoku } from "@/lib/types";

export interface CloudPoint {
  /** The x position as a (fractional) index into the date array. */
  x: number;
  a: number;
  b: number;
}

export interface CloudRun {
  /** 1 when span A is above span B (a rising cloud), -1 when below. */
  sign: 1 | -1;
  points: CloudPoint[];
}

/**
 * Split the cloud into runs of one colour. Where span A crosses span B,
 * the run ends at the exact crossing point and the next run starts there.
 * A gap (null in either span) also ends a run.
 */
export function cloudRuns(spanA: (number | null)[], spanB: (number | null)[]): CloudRun[] {
  const runs: CloudRun[] = [];
  let cur: CloudRun | null = null;
  const n = Math.min(spanA.length, spanB.length);
  for (let i = 0; i < n; i++) {
    const a = spanA[i];
    const b = spanB[i];
    if (a == null || b == null) {
      cur = null;
      continue;
    }
    const sign: 1 | -1 = a >= b ? 1 : -1;
    if (!cur) {
      cur = { sign, points: [{ x: i, a, b }] };
      runs.push(cur);
      continue;
    }
    if (sign === cur.sign) {
      cur.points.push({ x: i, a, b });
      continue;
    }
    // The spans cross between i-1 and i.
    const prev = cur.points[cur.points.length - 1];
    const d0 = prev.a - prev.b;
    const d1 = a - b;
    const t = d0 / (d0 - d1);
    const v = prev.a + (a - prev.a) * t;
    const cross: CloudPoint = { x: prev.x + t, a: v, b: v };
    cur.points.push(cross);
    cur = { sign, points: [cross, { x: i, a, b }] };
    runs.push(cur);
  }
  return runs;
}

export interface SignalInfo {
  key: "priceAboveCloud" | "conversionAboveBase" | "laggingAbovePrice";
  label: string;
  short: string;
  on: boolean;
}

/** The three signals of the score, with a plain label for each. */
export function signalList(s: Ichimoku["signals"]): SignalInfo[] {
  return [
    { key: "priceAboveCloud", label: "Price above the cloud", short: "Above cloud", on: s.priceAboveCloud },
    { key: "conversionAboveBase", label: "Fast line above slow line", short: "Fast > slow", on: s.conversionAboveBase },
    { key: "laggingAbovePrice", label: "Lagging line above the price", short: "Lag > price", on: s.laggingAbovePrice },
  ];
}

/** The index of the first date with no close: where the future starts. -1 when none. */
export function firstFutureIndex(close: (number | null)[]): number {
  for (let i = close.length - 1; i >= 0; i--) {
    if (close[i] != null) return i + 1 < close.length ? i + 1 : -1;
  }
  return 0;
}

/** The min and max of all non-null values, padded. */
export function priceDomain(series: (number | null)[][], pad = 0.05): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const s of series) {
    for (const v of s) {
      if (v == null) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
  }
  if (!Number.isFinite(lo)) return [0, 1];
  const p = (hi - lo || Math.abs(hi) || 1) * pad;
  return [lo - p, hi + p];
}

/** The indices where a new month starts, with a label ("Jan 26" for January, "Feb" otherwise). */
export function monthTicks(dates: string[]): { i: number; label: string }[] {
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const out: { i: number; label: string }[] = [];
  let last = "";
  dates.forEach((d, i) => {
    const ym = d.slice(0, 7);
    if (ym === last) return;
    last = ym;
    const m = Number(d.slice(5, 7)) - 1;
    out.push({ i, label: m === 0 ? `Jan ’${d.slice(2, 4)}` : names[m] });
  });
  return out;
}
