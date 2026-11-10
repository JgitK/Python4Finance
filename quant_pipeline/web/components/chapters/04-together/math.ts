// Pure helpers for chapter 4: the pairs of a correlation matrix and the
// mix of two stocks. No DOM.

export interface Pair {
  i: number;
  j: number;
  value: number;
}

/** The most and the least correlated pair (off the diagonal), and the mean. Null for fewer than 2 assets. */
export function extremePairs(corr: number[][]): { max: Pair; min: Pair; mean: number } | null {
  const n = corr.length;
  if (n < 2) return null;
  let max: Pair = { i: 1, j: 0, value: -Infinity };
  let min: Pair = { i: 1, j: 0, value: Infinity };
  let sum = 0;
  let count = 0;
  for (let i = 1; i < n; i++) {
    for (let j = 0; j < i; j++) {
      const v = corr[i][j];
      if (!Number.isFinite(v)) continue;
      sum += v;
      count++;
      if (v > max.value) max = { i, j, value: v };
      if (v < min.value) min = { i, j, value: v };
    }
  }
  if (!count) return null;
  return { max, min, mean: sum / count };
}

/** Daily covariance × trading days: the annual covariance. */
export function annualCov(covDaily: number[][], tradingDays: number): number[][] {
  return covDaily.map((row) => row.map((v) => v * tradingDays));
}

/** The largest absolute value off the diagonal (for the colour domain of covariance). */
export function maxAbsOffDiagonal(m: number[][]): number {
  let out = 0;
  for (let i = 0; i < m.length; i++) for (let j = 0; j < m.length; j++) if (i !== j && Math.abs(m[i][j]) > out) out = Math.abs(m[i][j]);
  return out;
}

/**
 * The text for one heatmap cell. Short cells drop the leading zero
 * (0.62 -> .62). Very small cells get no text (the tooltip has it).
 */
export function cellText(v: number, mode: "corr" | "cov", cell: number): string {
  if (!Number.isFinite(v) || cell < 18) return "";
  const digits = mode === "corr" ? 2 : 3;
  let s = v.toFixed(digits);
  if (cell < 34 || mode === "cov") s = s.replace(/^(-?)0\./, "$1.");
  return s.replace("-", "−");
}

/** The risk of a mix on the straight line between two stocks: the risk when rho is +1. */
export function straightRisk(w: number, volA: number, volB: number): number {
  return w * volA + (1 - w) * volB;
}

/** The return and risk of a mix with weight `w` in A. */
export function mixPoint(w: number, meanA: number, meanB: number, volA: number, volB: number, rho: number): { ret: number; risk: number } {
  const v = w * w * volA * volA + (1 - w) * (1 - w) * volB * volB + 2 * w * (1 - w) * rho * volA * volB;
  return { ret: w * meanA + (1 - w) * meanB, risk: Math.sqrt(Math.max(0, v)) };
}

/** The weight in A of the mix with the least risk, clamped to [0, 1]. */
export function minVarianceWeight(volA: number, volB: number, rho: number): number {
  const den = volA * volA + volB * volB - 2 * rho * volA * volB;
  if (den <= 1e-12) return volA <= volB ? 1 : 0;
  const w = (volB * volB - rho * volA * volB) / den;
  return Math.min(1, Math.max(0, w));
}
