"use client";

// The bars of chapter 6. One bar for each stock, coloured by sector. The
// bar length and the label change with the unit (weight, dollars, shares).
// React draws the SVG. A CSS transition moves the bars, so a new step
// interrupts the move in progress. Reduced motion turns the transition off.

import * as d3 from "d3";
import { useChartSize, usePrefersReducedMotion } from "@/components/scrolly";
import { COLORS, DURATION, LOSS, dollars, pct, sectorColor, sharesFmt } from "@/lib/theme";
import { barValue, TINY_WEIGHT, type MoneyPlan, type Unit } from "./allocation";

const LEFT = 54;
const TOP = 6;

export interface BarsProps {
  plan: MoneyPlan;
  unit: Unit;
  fractional: boolean;
  sectors: readonly string[];
}

function label(row: MoneyPlan["rows"][number], unit: Unit, fractional: boolean): string {
  if (unit === "weights") return row.weight < TINY_WEIGHT ? "0%" : pct(row.weight);
  if (unit === "dollars") return dollars(fractional ? row.cost : row.targetDollars);
  if (row.dropped) return "0 shares · drops out";
  return `${sharesFmt(row.shares)} × ${dollars(row.price, 2)}`;
}

export function Bars({ plan, unit, fractional, sectors }: BarsProps) {
  const [ref, { width, height }] = useChartSize<HTMLDivElement>();
  const reduced = usePrefersReducedMotion();
  const n = plan.rows.length;
  const rowH = n > 0 ? Math.max(16, Math.min(34, (height - TOP * 2) / n)) : 0;
  const labelW = width < 520 ? (unit === "shares" ? 128 : 66) : unit === "shares" ? 156 : 76;
  const barW = Math.max(20, width - LEFT - labelW - 8);
  const max = Math.max(1e-9, ...plan.rows.map((r) => barValue(r, unit, fractional)));
  const x = d3.scaleLinear().domain([0, max]).range([0, barW]);
  const ms = reduced ? 0 : DURATION.medium;
  const move = `${ms}ms cubic-bezier(0.22, 1, 0.36, 1)`;
  const dollarsFrom = (r: (typeof plan.rows)[number]) => `${r.ticker}, ${label(r, unit, fractional)}`;

  return (
    <div ref={ref} className="pane-fill">
      {width > 0 && height > 0 ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Bars for ${n} stocks, in ${unit === "weights" ? "percent of the money" : unit === "dollars" ? "dollars" : "shares"}. ${plan.rows.map(dollarsFrom).join("; ")}.`}
          style={{ display: "block", overflow: "hidden" }}
        >
          <line x1={LEFT} x2={LEFT} y1={TOP} y2={TOP + rowH * n} stroke={COLORS.paneBorder} />
          {plan.rows.map((r, i) => {
            const v = barValue(r, unit, fractional);
            const w = Math.max(0, x(v));
            const y = TOP + i * rowH;
            const bar = Math.min(22, rowH * 0.64);
            return (
              <g key={r.ticker} style={{ transform: `translate(0px, ${y}px)`, transition: `transform ${move}` }}>
                <title>{`${r.ticker} · ${r.sector}`}</title>
                <text x={LEFT - 8} y={rowH / 2} textAnchor="end" dominantBaseline="central" fontFamily="var(--font-mono), monospace" fontSize={12} fontWeight={600} fill={COLORS.ink}>
                  {r.ticker}
                </text>
                <rect
                  x={LEFT}
                  y={(rowH - bar) / 2}
                  height={bar}
                  rx={3}
                  fill={sectorColor(r.sector, sectors)}
                  style={{ width: Math.max(w, v > 0 ? 2 : 0), transition: `width ${move}` }}
                />
                <text
                  y={rowH / 2}
                  dominantBaseline="central"
                  fontFamily="var(--font-mono), monospace"
                  fontSize={11.5}
                  fill={unit === "shares" && r.dropped ? LOSS : COLORS.inkSoft}
                  fontWeight={unit === "shares" && r.dropped ? 600 : 400}
                  style={{ transform: `translate(${LEFT + Math.max(w, 2) + 6}px, 0px)`, transition: `transform ${move}` }}
                >
                  {unit === "shares" && r.dropped ? "✕ " : ""}
                  {label(r, unit, fractional)}
                </text>
              </g>
            );
          })}
        </svg>
      ) : null}
    </div>
  );
}
