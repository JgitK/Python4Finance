// The sparkline of daily returns: one thin vertical tick for each day,
// up from a zero line for a gain, down for a loss. Pure functions, no DOM.

export interface SparkPaths {
  /** The path of the gain days (draw it in the gain colour). */
  up: string;
  /** The path of the loss days (draw it in the loss colour). */
  down: string;
  /** The y of the zero line, in pixels. */
  zeroY: number;
  /** The largest absolute return: the half height of the chart. */
  maxAbs: number;
}

/**
 * Make the two paths for a sparkline of `values` in a box of `width` ×
 * `height` pixels. The y scale is symmetric around 0, so a gain and a
 * loss of the same size have the same length. Non-finite values are
 * skipped.
 */
export function sparkPaths(values: ArrayLike<number>, width: number, height: number, clipQuantile = 0.995): SparkPaths {
  const n = values.length;
  // The half height is the `clipQuantile` of the absolute returns, so one
  // freak day does not flatten all other days. A longer tick is clipped.
  const abs: number[] = [];
  for (let i = 0; i < n; i++) {
    const v = values[i];
    if (Number.isFinite(v)) abs.push(Math.abs(v));
  }
  abs.sort((a, b) => a - b);
  const maxAbs = abs.length ? abs[Math.min(abs.length - 1, Math.ceil(clipQuantile * (abs.length - 1)))] : 0;
  const zeroY = height / 2;
  if (n === 0 || maxAbs === 0) return { up: "", down: "", zeroY, maxAbs };
  const step = n > 1 ? width / (n - 1) : 0;
  const k = (height / 2) / maxAbs;
  let up = "";
  let down = "";
  for (let i = 0; i < n; i++) {
    const v = values[i];
    if (!Number.isFinite(v) || v === 0) continue;
    const x = +(i * step).toFixed(2);
    const y = +Math.min(height, Math.max(0, zeroY - v * k)).toFixed(2);
    const seg = `M${x},${zeroY}V${y}`;
    if (v > 0) up += seg;
    else down += seg;
  }
  return { up, down, zeroY, maxAbs };
}

/** The worst day, the best day, and the share of up days. */
export function dayStats(values: ArrayLike<number>): { worst: number; best: number; upShare: number } {
  let worst = Infinity;
  let best = -Infinity;
  let up = 0;
  let n = 0;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (!Number.isFinite(v)) continue;
    n++;
    if (v > 0) up++;
    if (v < worst) worst = v;
    if (v > best) best = v;
  }
  return n ? { worst, best, upShare: up / n } : { worst: NaN, best: NaN, upShare: NaN };
}
