import { describe, expect, it } from "vitest";
import { cloudRuns, firstFutureIndex, monthTicks, priceDomain, signalList } from "./helpers";

describe("cloudRuns", () => {
  it("keeps one run when A stays above B", () => {
    const r = cloudRuns([2, 3, 4], [1, 1, 1]);
    expect(r).toHaveLength(1);
    expect(r[0].sign).toBe(1);
    expect(r[0].points).toHaveLength(3);
  });
  it("splits at a crossing, at the exact point", () => {
    const r = cloudRuns([2, 0], [0, 2]);
    expect(r).toHaveLength(2);
    expect(r[0].sign).toBe(1);
    expect(r[1].sign).toBe(-1);
    const cross = r[0].points[r[0].points.length - 1];
    expect(cross.x).toBeCloseTo(0.5);
    expect(cross.a).toBeCloseTo(1);
    expect(cross.b).toBeCloseTo(1);
    expect(r[1].points[0]).toEqual(cross);
  });
  it("breaks on a gap", () => {
    expect(cloudRuns([1, null, 1], [0, 0, 0])).toHaveLength(2);
  });
  it("handles empty input", () => {
    expect(cloudRuns([], [])).toEqual([]);
  });
});

describe("signalList", () => {
  it("names three signals", () => {
    const s = signalList({ priceAboveCloud: true, conversionAboveBase: false, laggingAbovePrice: true });
    expect(s.map((x) => x.on)).toEqual([true, false, true]);
    expect(s[0].label).toMatch(/cloud/);
  });
});

describe("firstFutureIndex", () => {
  it("finds the first null after the last close", () => {
    expect(firstFutureIndex([1, 2, 3, null, null])).toBe(3);
  });
  it("returns -1 when no future", () => {
    expect(firstFutureIndex([1, 2])).toBe(-1);
  });
});

describe("priceDomain", () => {
  it("skips nulls and pads", () => {
    const [lo, hi] = priceDomain([[10, null], [20]], 0.1);
    expect(lo).toBeCloseTo(9);
    expect(hi).toBeCloseTo(21);
  });
});

describe("monthTicks", () => {
  it("marks each new month", () => {
    const t = monthTicks(["2025-12-30", "2025-12-31", "2026-01-02", "2026-02-02"]);
    expect(t.map((x) => x.i)).toEqual([0, 2, 3]);
    expect(t[1].label).toBe("Jan ’26");
    expect(t[2].label).toBe("Feb");
  });
});
