// Tests for lib/portfolio.ts. The reference values come from
// quant/optimize.py and quant/allocate.py (pandas and numpy), so the page
// and the pipeline agree.
import { describe, expect, it } from "vitest";
import {
  alignReturns,
  allocateFractional,
  allocateWhole,
  bootstrapMaxSharpe,
  correlationMatrix,
  covarianceMatrix,
  equalWeights,
  frontierHull,
  meanVector,
  minimumInvestment,
  monteCarlo,
  mulberry32,
  portfolioPerformance,
  standardErrorRange,
  twoAssetCurve,
} from "./portfolio";
import type { Returns } from "./types";

// Five days, three stocks. The same table as the Python check.
const ROWS = [
  [0.01, 0.002, -0.01],
  [-0.02, 0.01, 0.02],
  [0.015, -0.005, 0.0],
  [0.003, 0.007, 0.004],
  [-0.004, 0.001, 0.006],
];
const PY_MEAN = [0.0008, 0.003, 0.004];
const PY_COV = [
  [0.0001867, -0.0000625, -0.000132],
  [-0.0000625, 0.0000335, 0.0000385],
  [-0.000132, 0.0000385, 0.000118],
];

function close(a: number, b: number, digits = 10) {
  expect(a).toBeCloseTo(b, digits);
}

describe("alignReturns", () => {
  const returns: Returns = {
    dates: ["d1", "d2", "d3", "d4"],
    series: {
      A: [0.01, null, 0.02, 0.03],
      B: [0.0, 0.01, null, 0.04],
      C: [null, null, null, null],
    },
  };

  it("drops each day where a ticker is null", () => {
    const out = alignReturns(returns, ["A", "B"]);
    expect(out.dates).toEqual(["d1", "d4"]);
    expect(out.tickers).toEqual(["A", "B"]);
    expect(out.rows).toEqual([
      [0.01, 0.0],
      [0.03, 0.04],
    ]);
  });

  it("drops a ticker that has no series", () => {
    const out = alignReturns(returns, ["A", "ZZZ"]);
    expect(out.tickers).toEqual(["A"]);
    expect(out.missing).toEqual(["ZZZ"]);
    expect(out.dates).toEqual(["d1", "d3", "d4"]);
  });
});

describe("meanVector and covarianceMatrix", () => {
  it("agree with pandas mean() and cov() (sample, n-1)", () => {
    const m = meanVector(ROWS);
    m.forEach((v, i) => close(v, PY_MEAN[i]));
    const c = covarianceMatrix(ROWS);
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) close(c[i][j], PY_COV[i][j], 12);
  });

  it("gives a symmetric matrix", () => {
    const c = covarianceMatrix(ROWS);
    expect(c[0][2]).toBe(c[2][0]);
  });
});

describe("correlationMatrix", () => {
  it("agrees with pandas corr()", () => {
    const r = correlationMatrix(covarianceMatrix(ROWS));
    close(r[0][0], 1);
    close(r[0][1], -0.7902881225316312);
    close(r[0][2], -0.88932554787166);
    close(r[1][2], 0.6123466162613698);
  });
});

describe("portfolioPerformance", () => {
  it("agrees with portfolio_performance in optimize.py", () => {
    const p = portfolioPerformance([0.5, 0.3, 0.2], PY_MEAN, PY_COV, 252, 0.045);
    close(p.annualReturn, 0.5292);
    close(p.annualVol, 0.05914186334568771);
    close(p.sharpe, 8.187094092213872, 8);
  });

  it("gives NaN for the Sharpe ratio when the volatility is 0", () => {
    const p = portfolioPerformance([1], [0.001], [[0]], 252, 0.045);
    expect(Number.isNaN(p.sharpe)).toBe(true);
  });
});

describe("mulberry32", () => {
  it("repeats for the same seed and stays in [0, 1)", () => {
    const a = mulberry32(42);
    const b = mulberry32(42);
    for (let i = 0; i < 100; i++) {
      const x = a();
      expect(x).toBe(b());
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThan(1);
    }
  });

  it("changes with the seed", () => {
    expect(mulberry32(1)()).not.toBe(mulberry32(2)());
  });
});

describe("monteCarlo", () => {
  const mc = monteCarlo(PY_MEAN, PY_COV, 500, 42);

  it("returns typed arrays of the right length", () => {
    expect(mc.risk).toBeInstanceOf(Float64Array);
    expect(mc.ret).toBeInstanceOf(Float64Array);
    expect(mc.sharpe).toBeInstanceOf(Float64Array);
    expect(mc.weights).toBeInstanceOf(Float64Array);
    expect(mc.risk.length).toBe(500);
    expect(mc.weights.length).toBe(500 * 3);
    expect(mc.n).toBe(500);
    expect(mc.assets).toBe(3);
  });

  it("makes weights that are positive and sum to 1", () => {
    for (let k = 0; k < mc.n; k++) {
      let s = 0;
      for (let i = 0; i < 3; i++) {
        const w = mc.weights[k * 3 + i];
        expect(w).toBeGreaterThan(0);
        s += w;
      }
      close(s, 1);
    }
  });

  it("stores the same values as portfolioPerformance", () => {
    const k = 17;
    const w = Array.from(mc.weights.subarray(k * 3, k * 3 + 3));
    const p = portfolioPerformance(w, PY_MEAN, PY_COV, 252, 0.045);
    close(mc.ret[k], p.annualReturn);
    close(mc.risk[k], p.annualVol);
    close(mc.sharpe[k], p.sharpe);
  });

  it("finds the indexes of the maximum Sharpe and the minimum volatility", () => {
    let best = 0;
    let low = 0;
    for (let k = 0; k < mc.n; k++) {
      if (mc.sharpe[k] > mc.sharpe[best]) best = k;
      if (mc.risk[k] < mc.risk[low]) low = k;
    }
    expect(mc.maxSharpeIndex).toBe(best);
    expect(mc.minVolIndex).toBe(low);
  });

  it("gives the same cloud for the same seed", () => {
    const again = monteCarlo(PY_MEAN, PY_COV, 500, 42);
    expect(Array.from(again.sharpe)).toEqual(Array.from(mc.sharpe));
    const other = monteCarlo(PY_MEAN, PY_COV, 500, 7);
    expect(other.sharpe[0]).not.toBe(mc.sharpe[0]);
  });

  it("runs 10,000 portfolios of 15 assets quickly", () => {
    const n = 15;
    const mean = Array.from({ length: n }, (_, i) => 0.0003 + i * 0.00002);
    const cov = Array.from({ length: n }, (_, i) =>
      Array.from({ length: n }, (_, j) => (i === j ? 0.0004 : 0.0001)),
    );
    const t0 = performance.now();
    const big = monteCarlo(mean, cov, 10000, 42);
    const ms = performance.now() - t0;
    expect(big.risk.length).toBe(10000);
    expect(ms).toBeLessThan(250);
  });
});

describe("frontierHull", () => {
  it("returns the upper-left edge from the least risk to the most return", () => {
    const risk = [0.1, 0.2, 0.3, 0.15, 0.25, 0.12];
    const ret = [0.05, 0.1, 0.12, 0.06, 0.08, 0.02];
    const edge = frontierHull(risk, ret);
    expect(edge.map((p) => p.index)).toEqual([0, 1, 2]);
    expect(edge[0]).toEqual({ risk: 0.1, ret: 0.05, index: 0 });
  });

  it("skips a point under the line of its neighbours", () => {
    const risk = [0.1, 0.2, 0.3];
    const ret = [0.05, 0.06, 0.12];
    expect(frontierHull(risk, ret).map((p) => p.index)).toEqual([0, 2]);
  });

  it("returns no points for no input", () => {
    expect(frontierHull([], [])).toEqual([]);
  });
});

describe("twoAssetCurve", () => {
  it("runs from 100% in B to 100% in A", () => {
    const c = twoAssetCurve(0.1, 0.2, 0.15, 0.3, 0.2, 10);
    expect(c.length).toBe(11);
    expect(c[0]).toMatchObject({ weightA: 0 });
    close(c[0].ret, 0.2);
    close(c[0].risk, 0.3);
    close(c[10].ret, 0.1);
    close(c[10].risk, 0.15);
  });

  it("is a straight line at rho = +1", () => {
    const c = twoAssetCurve(0.1, 0.2, 0.15, 0.3, 1, 4);
    close(c[2].risk, 0.225);
  });

  it("reaches zero risk at rho = -1 for the right mix", () => {
    const c = twoAssetCurve(0.1, 0.2, 0.1, 0.1, -1, 2);
    close(c[1].risk, 0);
  });
});

describe("allocateWhole", () => {
  const w = { AAA: 0.5, BBB: 0.3, CCC: 0.2 };

  it("agrees with allocation_summary: drops a share that costs too much", () => {
    const plan = allocateWhole(w, { AAA: 120, BBB: 45.5, CCC: 900 }, 2000);
    const by = Object.fromEntries(plan.rows.map((r) => [r.ticker, r]));
    expect(by.AAA.shares).toBe(8);
    expect(by.BBB.shares).toBe(13);
    expect(by.CCC.shares).toBe(0);
    close(by.AAA.actualWeight, 0.6187560425394779);
    close(plan.spent, 1551.5);
    close(plan.cash, 448.5);
    expect(plan.dropped).toEqual(["CCC"]);
  });

  it("runs the top-up pass, as allocation_summary does", () => {
    const prices = { AAA: 130, BBB: 47, CCC: 310 };
    const first = allocateWhole(w, prices, 5000, { topUp: false });
    const full = allocateWhole(w, prices, 5000);
    const shares = (p: typeof full) => p.rows.map((r) => r.shares);
    expect(shares(first)).toEqual([19, 31, 3]);
    expect(shares(full)).toEqual([19, 32, 3]);
  });
});

describe("allocateFractional", () => {
  it("agrees with allocate_fractional (6 decimals, rounded down)", () => {
    const plan = allocateFractional(
      { AAA: 0.5, BBB: 0.3, CCC: 0.2 },
      { AAA: 120, BBB: 45.5, CCC: 900 },
      2000,
    );
    expect(plan.rows.map((r) => r.shares)).toEqual([8.333333, 13.186813, 0.444444]);
    expect(plan.dropped).toEqual([]);
    expect(plan.cash).toBeGreaterThanOrEqual(0);
  });
});

describe("minimumInvestment", () => {
  it("is the largest price over its weight", () => {
    expect(
      minimumInvestment({ AAA: 0.5, BBB: 0.3, CCC: 0.2 }, { AAA: 120, BBB: 45.5, CCC: 900 }),
    ).toBe(4500);
  });

  it("ignores a weight of 0", () => {
    expect(minimumInvestment({ A: 1, B: 0 }, { A: 10, B: 1e9 })).toBe(10);
  });
});

describe("equalWeights", () => {
  it("gives 1/n to each", () => {
    expect(equalWeights(4)).toEqual([0.25, 0.25, 0.25, 0.25]);
  });
});

describe("bootstrapMaxSharpe", () => {
  it("returns one point for each draw, the same for the same seed", () => {
    const a = bootstrapMaxSharpe(ROWS, 20, 42, { portfolios: 200 });
    const b = bootstrapMaxSharpe(ROWS, 20, 42, { portfolios: 200 });
    expect(a.length).toBe(20);
    expect(a).toEqual(b);
    for (const p of a) {
      expect(p.weights.length).toBe(3);
      close(p.weights.reduce((s, x) => s + x, 0), 1);
      expect(Number.isFinite(p.risk)).toBe(true);
    }
  });

  it("moves the point when the days change", () => {
    const pts = bootstrapMaxSharpe(ROWS, 30, 42, { portfolios: 200 });
    const unique = new Set(pts.map((p) => p.risk.toFixed(6)));
    expect(unique.size).toBeGreaterThan(1);
  });
});

describe("standardErrorRange", () => {
  it("uses the annual volatility over the square root of the years", () => {
    const r = standardErrorRange(0.12, 0.3, 4);
    close(r.se, 0.15);
    close(r.low, 0.12 - 1.96 * 0.15);
    close(r.high, 0.12 + 1.96 * 0.15);
  });
});
