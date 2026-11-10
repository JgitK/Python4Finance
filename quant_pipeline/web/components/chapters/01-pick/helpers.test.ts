import { describe, expect, it } from "vitest";
import type { Leader } from "@/lib/types";
import { basketHint, clipRange, pickForMe, pinX, sectorCounts, xDomain } from "./helpers";

const L = (ticker: string, sector: string, rank: number, cumReturn: number): Leader => ({
  ticker, sector, rank, cumReturn, annualVol: 0.3, rangeLow: cumReturn - 1, rangeHigh: cumReturn + 1, stable: false,
});

describe("xDomain", () => {
  it("holds zero and all dots", () => {
    const [a, b] = xDomain([L("A", "X", 1, 0.5), L("B", "X", 2, 0.2)]);
    expect(a).toBeLessThan(0);
    expect(b).toBeGreaterThan(0.5);
  });
  it("ignores a few big outliers", () => {
    const ls = Array.from({ length: 30 }, (_, i) => L(`T${i}`, "X", 1, i / 100));
    ls.push(L("BIG", "X", 1, 9));
    expect(xDomain(ls)[1]).toBeLessThan(1);
  });
  it("handles an empty window", () => {
    const [a, b] = xDomain([]);
    expect(b).toBeGreaterThan(a);
  });
});

describe("clipRange", () => {
  it("cuts at the edge and flags the cut", () => {
    expect(clipRange(-0.7, 1.4, [-0.1, 1])).toEqual({ from: -0.1, to: 1, clipLow: true, clipHigh: true });
  });
  it("keeps a range that fits", () => {
    expect(clipRange(0, 0.5, [-0.1, 1])).toEqual({ from: 0, to: 0.5, clipLow: false, clipHigh: false });
  });
});

describe("pickForMe", () => {
  it("takes rank 1, best first, up to max", () => {
    const ls = [L("A", "S1", 1, 0.1), L("B", "S1", 2, 0.9), L("C", "S2", 1, 0.3), L("D", "S3", 1, 0.2)];
    expect(pickForMe(ls, 2)).toEqual(["C", "D"]);
    expect(pickForMe([], 5)).toEqual([]);
  });
});

describe("sectorCounts", () => {
  it("counts by sector", () => {
    const m: Record<string, string> = { A: "S1", B: "S1", C: "S2" };
    expect(sectorCounts(["A", "B", "C"], (t) => m[t])).toEqual({ S1: 2, S2: 1 });
  });
});

describe("basketHint", () => {
  it("explains the limits", () => {
    expect(basketHint(15, 2, 15)).toMatch(/full/);
    expect(basketHint(1, 2, 15)).toMatch(/at least 2/);
    expect(basketHint(8, 2, 15)).toBeNull();
  });
});

describe("pinX", () => {
  it("clamps to the domain", () => {
    expect(pinX(5, [0, 1])).toBe(1);
    expect(pinX(-5, [0, 1])).toBe(0);
    expect(pinX(0.5, [0, 1])).toBe(0.5);
  });
});
