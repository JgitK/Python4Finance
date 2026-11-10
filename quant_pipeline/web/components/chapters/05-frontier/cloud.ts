// Pure helpers for the Monte Carlo cloud of chapter 5: the rain schedule,
// a grid index to pick the dot under the pointer, and the colour domain.
// No DOM.

/** The length of the full rain, in ms. */
export const RAIN_MS = 2100;

/**
 * How many dots show `t` ms after the rain starts: 10 dots, a pause, 100
 * dots, a pause, then the rest with an ease-in (slow, then fast).
 */
export function rainCount(t: number, total: number): number {
  if (total <= 0) return 0;
  if (t < 0) return 0;
  const first = Math.min(10, total);
  const second = Math.min(100, total);
  if (t < 350) return first;
  if (t < 800) return second;
  const k = Math.min(1, (t - 800) / (RAIN_MS - 800));
  return Math.min(total, Math.round(second + (total - second) * k * k));
}

/** The 2nd and 98th percentile of the finite values: a colour domain that ignores outliers. */
export function robustDomain(values: ArrayLike<number>, lo = 0.02, hi = 0.98): [number, number] {
  const v: number[] = [];
  for (let i = 0; i < values.length; i++) if (Number.isFinite(values[i])) v.push(values[i]);
  if (!v.length) return [0, 1];
  v.sort((a, b) => a - b);
  const at = (q: number) => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  const a = at(lo);
  const b = at(hi);
  return a === b ? [a - 0.5, b + 0.5] : [a, b];
}

/** A uniform grid of point indices, for a fast nearest-point search. */
export interface PointGrid {
  cell: number;
  buckets: Map<number, number[]>;
}

const keyOf = (cx: number, cy: number) => cx * 100003 + cy;

/** Put the first `count` points into square cells of `cell` pixels. */
export function buildGrid(xs: ArrayLike<number>, ys: ArrayLike<number>, count: number, cell: number): PointGrid {
  const buckets = new Map<number, number[]>();
  const n = Math.min(count, xs.length, ys.length);
  for (let k = 0; k < n; k++) {
    const x = xs[k];
    const y = ys[k];
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const key = keyOf(Math.floor(x / cell), Math.floor(y / cell));
    const b = buckets.get(key);
    if (b) b.push(k);
    else buckets.set(key, [k]);
  }
  return { cell, buckets };
}

/** The index of the nearest point within `radius` pixels, or -1. `radius` must be at most `grid.cell`. */
export function nearestPoint(grid: PointGrid, xs: ArrayLike<number>, ys: ArrayLike<number>, px: number, py: number, radius: number): number {
  const cx = Math.floor(px / grid.cell);
  const cy = Math.floor(py / grid.cell);
  let best = -1;
  let bestD = radius * radius;
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const b = grid.buckets.get(keyOf(cx + dx, cy + dy));
      if (!b) continue;
      for (const k of b) {
        const d = (xs[k] - px) ** 2 + (ys[k] - py) ** 2;
        if (d <= bestD) {
          bestD = d;
          best = k;
        }
      }
    }
  }
  return best;
}

/**
 * The capital market line: from (0, riskFree) through the tangent point
 * (risk, ret), to the risk `xMax`. Returns the two end points.
 */
export function capitalMarketLine(riskFree: number, risk: number, ret: number, xMax: number): [{ risk: number; ret: number }, { risk: number; ret: number }] {
  const slope = risk > 0 ? (ret - riskFree) / risk : 0;
  return [
    { risk: 0, ret: riskFree },
    { risk: xMax, ret: riskFree + slope * xMax },
  ];
}
