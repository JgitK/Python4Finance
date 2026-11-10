import { describe, expect, it } from "vitest";
import { buildErrorRows, quantile, rankByMeanSharpe, ratio, weightSpread, windowDiffs, winCount } from "./trust";

describe("buildErrorRows", () => {
  it("makes a 95% range of 1.96 standard errors and sorts by return", () => {
    const rows = buildErrorRows(["A", "B"], ["S1", "S2"], [0.1, 0.3], [0.2, 0.4], 4, [0.7, 0.3]);
    expect(rows.map((r) => r.ticker)).toEqual(["B", "A"]);
    const a = rows[1];
    expect(a.high - a.ret).toBeCloseTo(1.96 * (0.2 / 2));
    expect(a.spansZero).toBe(true); // 0.1 - 0.196 < 0
    expect(a.weight).toBe(0.7);
  });
  it("skips a ticker without a finite return", () => {
    expect(buildErrorRows(["A"], ["S"], [NaN], [0.2], 3, null)).toEqual([]);
  });
  it("gives no rows when the years are not above 0", () => {
    expect(buildErrorRows(["A"], ["S"], [0.1], [0.2], 0, null)).toEqual([]);
  });
});

describe("quantile and weightSpread", () => {
  it("interpolates", () => {
    expect(quantile([0, 10], 0.5)).toBe(5);
    expect(quantile([1, 2, 3], 1)).toBe(3);
    expect(Number.isNaN(quantile([], 0.5))).toBe(true);
  });
  it("finds the min, median and max of each weight", () => {
    const s = weightSpread([{ weights: [0.2, 0.8] }, { weights: [0.6, 0.4] }, { weights: [0.4, 0.6] }], ["A", "B"]);
    expect(s[0]).toMatchObject({ ticker: "A", min: 0.2, median: 0.4, max: 0.6 });
    expect(s[1].max).toBe(0.8);
  });
});

describe("scorecard helpers", () => {
  const row = (name: string, meanSharpe: number | null) =>
    ({ name, meanSharpe, medianExcess: null, winReturn: null, winSharpe: null, note: "" }) as never;
  it("ranks the optimizer among the measured rows and skips null", () => {
    const r = rankByMeanSharpe([row("Optimizer", 0.78), row("Equal weight", 0.88), row("SPY", 0.8), row("Random order", null)] as never);
    expect(r.order).toEqual(["Equal weight", "SPY", "Optimizer"]);
    expect(r.optimizerRank).toBe(3);
  });
  it("handles windows of any length, also none", () => {
    expect(windowDiffs(undefined)).toEqual([]);
    const w = windowDiffs([
      { date: "2025-08-12", portfolioReturn: 0.1, benchmarkReturn: 0.05, portfolioSharpe: 0, benchmarkSharpe: 0 },
      { date: "2025-02-10", portfolioReturn: -0.01, benchmarkReturn: 0.13, portfolioSharpe: 0, benchmarkSharpe: 0 },
    ]);
    expect(w.map((x) => x.date)).toEqual(["2025-02-10", "2025-08-12"]);
    expect(w[0].diff).toBeCloseTo(-0.14);
    expect(winCount(w)).toBe(1);
  });
  it("ratio is null when the divisor is not above 0", () => {
    expect(ratio(5.32, 0.88)).toBeCloseTo(6.04, 1);
    expect(ratio(5, -1)).toBeNull();
  });
});
