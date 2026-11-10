import { describe, expect, it } from "vitest";
import { RAIN_MS, buildGrid, capitalMarketLine, nearestPoint, rainCount, robustDomain } from "./cloud";

describe("rainCount", () => {
  it("shows 10, then 100, then all", () => {
    expect(rainCount(0, 10000)).toBe(10);
    expect(rainCount(500, 10000)).toBe(100);
    expect(rainCount(RAIN_MS, 10000)).toBe(10000);
    expect(rainCount(RAIN_MS * 5, 10000)).toBe(10000);
  });
  it("never goes down as time goes on", () => {
    let last = 0;
    for (let t = 0; t <= RAIN_MS; t += 37) {
      const c = rainCount(t, 10000);
      expect(c).toBeGreaterThanOrEqual(last);
      last = c;
    }
  });
  it("respects a small total", () => {
    expect(rainCount(0, 5)).toBe(5);
    expect(rainCount(1000, 50)).toBeLessThanOrEqual(50);
    expect(rainCount(0, 0)).toBe(0);
  });
});

describe("robustDomain", () => {
  it("ignores the outliers at the ends", () => {
    const v = Array.from({ length: 101 }, (_, i) => i);
    v[100] = 1e6;
    const [a, b] = robustDomain(v);
    expect(a).toBe(2);
    expect(b).toBeLessThan(1e6);
  });
  it("widens a flat domain", () => {
    expect(robustDomain([1, 1, 1])).toEqual([0.5, 1.5]);
  });
});

describe("grid picking", () => {
  const xs = [10, 50, 52, 200];
  const ys = [10, 50, 51, 200];
  it("finds the nearest point within the radius", () => {
    const g = buildGrid(xs, ys, 4, 12);
    expect(nearestPoint(g, xs, ys, 53, 52, 8)).toBe(2);
    expect(nearestPoint(g, xs, ys, 11, 9, 8)).toBe(0);
    expect(nearestPoint(g, xs, ys, 120, 120, 8)).toBe(-1);
  });
  it("only holds the first `count` points", () => {
    const g = buildGrid(xs, ys, 1, 12);
    expect(nearestPoint(g, xs, ys, 50, 50, 8)).toBe(-1);
  });
  it("finds a point across a cell edge", () => {
    const g = buildGrid([11.9], [11.9], 1, 12);
    expect(nearestPoint(g, [11.9], [11.9], 12.1, 12.1, 8)).toBe(0);
  });
});

describe("capitalMarketLine", () => {
  it("passes through the risk-free rate and the tangent point", () => {
    const [a, b] = capitalMarketLine(0.04, 0.2, 0.14, 0.4);
    expect(a).toEqual({ risk: 0, ret: 0.04 });
    expect(b.ret).toBeCloseTo(0.24);
  });
});
