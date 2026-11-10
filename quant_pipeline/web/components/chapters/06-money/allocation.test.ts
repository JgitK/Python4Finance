import { describe, expect, it } from "vitest";
import { barValue, buildMoneyPlan, toCsv } from "./allocation";

const weights = { AAA: 0.6, BBB: 0.3, CCC: 0.1 };
const prices = { AAA: 100, BBB: 50, CCC: 2000 };
const sectors = { AAA: "Energy", BBB: "Utilities", CCC: "Tech" };

describe("buildMoneyPlan", () => {
  it("drops a stock when one share costs more than its target", () => {
    const p = buildMoneyPlan(weights, prices, sectors, 1000, false);
    expect(p.droppedRows.map((r) => r.ticker)).toEqual(["CCC"]);
    expect(p.droppedRows[0].targetDollars).toBeCloseTo(100);
    expect(p.minimum).toBeCloseTo(20000); // 2000 / 0.1
    expect(p.spent + p.cash).toBeCloseTo(1000);
  });
  it("sorts by weight, largest first", () => {
    const p = buildMoneyPlan(weights, prices, sectors, 1000, false);
    expect(p.rows.map((r) => r.ticker)).toEqual(["AAA", "BBB", "CCC"]);
  });
  it("buys parts of a share when fractional", () => {
    const p = buildMoneyPlan(weights, prices, sectors, 1000, true);
    expect(p.droppedRows).toHaveLength(0);
    expect(p.rows.find((r) => r.ticker === "CCC")!.shares).toBeCloseTo(0.05);
    expect(p.cash).toBeLessThan(0.01);
  });
  it("skips a stock with no usable price", () => {
    const p = buildMoneyPlan({ AAA: 0.5, ZZZ: 0.5 }, { AAA: 10 }, sectors, 1000, true);
    expect(p.rows.map((r) => r.ticker)).toEqual(["AAA"]);
  });
});

describe("barValue", () => {
  it("picks the number for each unit", () => {
    const r = buildMoneyPlan(weights, prices, sectors, 1000, false).rows[0];
    expect(barValue(r, "weights", false)).toBe(0.6);
    expect(barValue(r, "dollars", false)).toBeCloseTo(600);
    expect(barValue(r, "shares", false)).toBe(r.shares);
  });
});

describe("toCsv", () => {
  it("writes a header, a row for each stock, a total and the cash", () => {
    const csv = toCsv(buildMoneyPlan(weights, prices, sectors, 1000, false));
    const lines = csv.trim().split("\n");
    expect(lines[0]).toBe("ticker,sector,weight,price,shares,cost,actual_weight");
    expect(lines).toHaveLength(1 + 3 + 2);
    expect(lines[1].startsWith("AAA,Energy,0.6000,100.00,")).toBe(true);
    expect(lines[4].startsWith("TOTAL")).toBe(true);
  });
  it("quotes a sector with a comma", () => {
    const csv = toCsv(buildMoneyPlan({ AAA: 1 }, { AAA: 10 }, { AAA: "Real Estate, other" }, 100, true));
    expect(csv).toContain('"Real Estate, other"');
  });
});
