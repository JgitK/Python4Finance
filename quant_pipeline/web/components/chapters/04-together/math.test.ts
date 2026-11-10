import { describe, expect, it } from "vitest";
import { twoAssetCurve } from "@/lib/portfolio";
import { annualCov, cellText, extremePairs, maxAbsOffDiagonal, minVarianceWeight, mixPoint, straightRisk } from "./math";

const corr = [
  [1, 0.8, 0.1],
  [0.8, 1, -0.2],
  [0.1, -0.2, 1],
];

describe("extremePairs", () => {
  it("finds the most and least correlated pair and the mean", () => {
    const p = extremePairs(corr)!;
    expect(p.max).toEqual({ i: 1, j: 0, value: 0.8 });
    expect(p.min).toEqual({ i: 2, j: 1, value: -0.2 });
    expect(p.mean).toBeCloseTo((0.8 + 0.1 - 0.2) / 3);
  });

  it("gives null for one asset", () => {
    expect(extremePairs([[1]])).toBeNull();
  });
});

describe("annualCov and maxAbsOffDiagonal", () => {
  it("scales by the trading days and skips the diagonal", () => {
    const c = annualCov([[0.0004, -0.0001], [-0.0001, 0.0009]], 252);
    expect(c[0][1]).toBeCloseTo(-0.0252);
    expect(maxAbsOffDiagonal(c)).toBeCloseTo(0.0252);
  });
});

describe("cellText", () => {
  it("prints two digits for a wide correlation cell", () => {
    expect(cellText(0.623, "corr", 40)).toBe("0.62");
    expect(cellText(-0.05, "corr", 40)).toBe("−0.05");
  });
  it("drops the leading zero in a narrow cell", () => {
    expect(cellText(0.623, "corr", 24)).toBe(".62");
    expect(cellText(-0.05, "corr", 24)).toBe("−.05");
  });
  it("prints nothing in a tiny cell", () => {
    expect(cellText(0.5, "corr", 12)).toBe("");
  });
  it("prints three digits for covariance", () => {
    expect(cellText(0.0341, "cov", 40)).toBe(".034");
  });
});

describe("two-stock mix", () => {
  it("agrees with twoAssetCurve", () => {
    const curve = twoAssetCurve(0.2, 0.1, 0.3, 0.2, 0.3, 10);
    const p = mixPoint(0.4, 0.2, 0.1, 0.3, 0.2, 0.3);
    expect(p.risk).toBeCloseTo(curve[4].risk);
    expect(p.ret).toBeCloseTo(curve[4].ret);
  });

  it("lies on the straight line when rho is +1", () => {
    expect(mixPoint(0.3, 0.2, 0.1, 0.3, 0.2, 1).risk).toBeCloseTo(straightRisk(0.3, 0.3, 0.2));
  });

  it("finds the weight of least risk", () => {
    const w = minVarianceWeight(0.3, 0.2, 0.1);
    const at = (x: number) => mixPoint(x, 0, 0, 0.3, 0.2, 0.1).risk;
    expect(at(w)).toBeLessThanOrEqual(at(w + 0.01));
    expect(at(w)).toBeLessThanOrEqual(at(w - 0.01));
    // At rho -1 the least risk is zero.
    expect(mixPoint(minVarianceWeight(0.3, 0.2, -1), 0, 0, 0.3, 0.2, -1).risk).toBeCloseTo(0);
  });
});
