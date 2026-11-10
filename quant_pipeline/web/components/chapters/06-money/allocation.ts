// Pure helpers for chapter 6: turn weights, prices and an amount into the
// rows that the bars and the table draw. No DOM, no React.

import { allocateFractional, allocateWhole, minimumInvestment, type AllocationPlan } from "@/lib/portfolio";

/** What the bars measure. */
export type Unit = "weights" | "dollars" | "shares";

/** One stock, ready to draw. */
export interface MoneyRow {
  ticker: string;
  sector: string;
  weight: number;
  price: number;
  /** amount x weight: the money that the weight asks for. */
  targetDollars: number;
  shares: number;
  /** shares x price: the money that the plan really spends. */
  cost: number;
  actualWeight: number;
  /** True when the weight is above 0 and the plan buys no share. */
  dropped: boolean;
}

export interface MoneyPlan {
  rows: MoneyRow[];
  spent: number;
  cash: number;
  /** The smallest amount that holds every weight with whole shares. */
  minimum: number;
  droppedRows: MoneyRow[];
}

/** Weights below this count as zero in the bars (a weight of 0.04% is noise). */
export const TINY_WEIGHT = 0.0005;

/**
 * Build the plan. `weights` and `prices` are keyed by ticker. The rows are
 * sorted by weight, largest first, then by ticker, so the order is stable
 * when the unit changes.
 */
export function buildMoneyPlan(
  weights: Record<string, number>,
  prices: Record<string, number>,
  sectors: Record<string, string>,
  amount: number,
  fractional: boolean,
): MoneyPlan {
  const usable: Record<string, number> = {};
  for (const t of Object.keys(weights)) {
    if (Number.isFinite(prices[t]) && prices[t] > 0 && Number.isFinite(weights[t])) usable[t] = weights[t];
  }
  const plan: AllocationPlan = fractional
    ? allocateFractional(usable, prices, amount)
    : allocateWhole(usable, prices, amount);
  const rows: MoneyRow[] = plan.rows
    .map((r) => ({
      ticker: r.ticker,
      sector: sectors[r.ticker] ?? "Unknown",
      weight: r.targetWeight,
      price: r.price,
      targetDollars: amount * r.targetWeight,
      shares: r.shares,
      cost: r.cost,
      actualWeight: r.actualWeight,
      dropped: plan.dropped.includes(r.ticker),
    }))
    .sort((a, b) => b.weight - a.weight || a.ticker.localeCompare(b.ticker));
  return {
    rows,
    spent: plan.spent,
    cash: plan.cash,
    minimum: minimumInvestment(usable, prices),
    droppedRows: rows.filter((r) => r.dropped),
  };
}

/** The value that a bar shows for a unit. */
export function barValue(row: MoneyRow, unit: Unit, fractional: boolean): number {
  if (unit === "weights") return row.weight;
  if (unit === "dollars") return fractional ? row.cost : row.targetDollars;
  return row.shares;
}

const q = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);

/** The table as CSV text. Weights are fractions with 4 decimals, money has 2. */
export function toCsv(plan: MoneyPlan): string {
  const head = ["ticker", "sector", "weight", "price", "shares", "cost", "actual_weight"];
  const lines = [head.join(",")];
  for (const r of plan.rows) {
    lines.push(
      [q(r.ticker), q(r.sector), r.weight.toFixed(4), r.price.toFixed(2), String(r.shares), r.cost.toFixed(2), r.actualWeight.toFixed(4)].join(","),
    );
  }
  const w = plan.rows.reduce((s, r) => s + r.weight, 0);
  const a = plan.rows.reduce((s, r) => s + r.actualWeight, 0);
  lines.push(["TOTAL", "", w.toFixed(4), "", "", plan.spent.toFixed(2), a.toFixed(4)].join(","));
  lines.push(["CASH LEFT", "", "", "", "", plan.cash.toFixed(2), ""].join(","));
  return lines.join("\n") + "\n";
}
