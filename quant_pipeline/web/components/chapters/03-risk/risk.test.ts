import { describe, expect, it } from "vitest";
import { monoWidth, placeLabels } from "./labels";
import { dayStats, sparkPaths } from "./spark";

function boxesOverlap(a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

describe("placeLabels", () => {
  it("puts a lone label to the right of its dot", () => {
    const [p] = placeLabels([{ x: 50, y: 50, w: 30 }], { width: 200, height: 200 });
    expect(p.side).toBe("right");
    expect(p.x).toBeGreaterThan(50);
  });

  it("moves a label to the left near the right edge", () => {
    const [p] = placeLabels([{ x: 195, y: 50, w: 30 }], { width: 200, height: 200 });
    expect(p.x + p.w).toBeLessThanOrEqual(200);
    expect(p.side).not.toBe("right");
  });

  it("keeps labels of close dots apart", () => {
    const pts = [
      { x: 100, y: 100, w: 30 },
      { x: 100, y: 104, w: 30 },
      { x: 100, y: 108, w: 30 },
    ];
    const out = placeLabels(pts, { width: 300, height: 300 });
    for (let i = 0; i < out.length; i++) for (let j = i + 1; j < out.length; j++) expect(boxesOverlap(out[i], out[j])).toBe(false);
  });

  it("keeps every label inside the plot", () => {
    const pts = Array.from({ length: 12 }, (_, i) => ({ x: (i * 37) % 120, y: (i * 53) % 90, w: monoWidth("ABCD") }));
    for (const p of placeLabels(pts, { width: 120, height: 90 })) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.x + p.w).toBeLessThanOrEqual(120);
      expect(p.y + p.h).toBeLessThanOrEqual(90);
    }
  });
});

describe("sparkPaths", () => {
  it("splits gains and losses around a centred zero line", () => {
    const s = sparkPaths([0.01, -0.02, 0, 0.02], 30, 40);
    expect(s.zeroY).toBe(20);
    expect(s.maxAbs).toBeCloseTo(0.02);
    expect(s.up).toBe("M0,20V10M30,20V0");
    expect(s.down).toBe("M10,20V40");
  });

  it("clips one freak day to the box", () => {
    const vals: number[] = Array.from({ length: 400 }, (_, i) => (i % 2 ? 0.01 : -0.01));
    vals[10] = 1.5;
    const s = sparkPaths(vals, 100, 40);
    expect(s.maxAbs).toBeCloseTo(0.01);
    expect(s.up).toContain("V0");
    expect(s.up).not.toMatch(/V-/);
  });

  it("gives empty paths for empty or flat input", () => {
    expect(sparkPaths([], 10, 10).up).toBe("");
    expect(sparkPaths([0, 0], 10, 10).down).toBe("");
  });
});

describe("dayStats", () => {
  it("finds the worst day, the best day and the up share", () => {
    const d = dayStats([0.01, -0.03, NaN, 0.02, -0.01]);
    expect(d.worst).toBeCloseTo(-0.03);
    expect(d.best).toBeCloseTo(0.02);
    expect(d.upShare).toBeCloseTo(0.5);
  });
});
