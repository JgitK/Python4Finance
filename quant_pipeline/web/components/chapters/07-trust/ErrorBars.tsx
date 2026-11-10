"use client";

// Chapter 7, step 1: error-bars.svg. The expected return of each stock as a
// dot with its 95% range. React draws the SVG, D3 makes the scales.

import * as d3 from "d3";
import { useMemo, useState } from "react";
import { useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { useStore } from "@/lib/store";
import { COLORS, pct, sectorColor, signedPct } from "@/lib/theme";
import { buildErrorRows } from "./trust";
import s from "./trust.module.css";

const LEFT = 50;
const TOP = 6;
const BOTTOM = 26;

export function ErrorBars() {
  const { stats, portfolios, data } = useStore();
  const [ref, { width, height }] = useChartSize<HTMLDivElement>();
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);

  const rows = useMemo(
    () => (stats ? buildErrorRows(stats.tickers, stats.sectors, stats.annualReturn, stats.annualVol, stats.years, portfolios?.maxSharpe.weights ?? null) : []),
    [stats, portfolios],
  );
  const sectors = data?.meta.sectors ?? [];
  const crossing = rows.filter((r) => r.spansZero).length;

  if (!stats || rows.length === 0) return <p className={s.empty}>Pick some stocks in chapter 1 to see their error bars.</p>;

  const rightW = width < 520 ? 52 : 68;
  const plotW = Math.max(40, width - LEFT - rightW - 8);
  const lo = Math.min(0, ...rows.map((r) => r.low));
  const hi = Math.max(0, ...rows.map((r) => r.high));
  const x = d3.scaleLinear().domain([lo, hi]).nice().range([0, plotW]);
  const rowH = Math.max(16, Math.min(40, (height - TOP - BOTTOM) / rows.length));
  const ticks = x.ticks(width < 520 ? 4 : 6);
  const hv = hover ? rows[hover.i] : null;

  return (
    <div className={s.stack}>
      <p className={s.point}>
        The optimizer treated each dot as a fact. The bars show how far off it could be:{" "}
        <strong>
          {crossing} of {rows.length}
        </strong>{" "}
        ranges reach zero or below. They are guesses, built from {stats.years.toFixed(1)} years of prices.
      </p>
      <div ref={ref} className={s.chartBox} style={{ minHeight: rows.length * 18 + 40 }}>
        {width > 0 && height > 0 ? (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`Expected annual return of ${rows.length} stocks with a 95% range. ${rows.map((r) => `${r.ticker} ${pct(r.ret, 0)}, range ${pct(r.low, 0)} to ${pct(r.high, 0)}`).join("; ")}.`}
            style={{ display: "block", overflow: "hidden" }}
          >
            <g transform={`translate(${LEFT},${TOP})`}>
              {ticks.map((t) => (
                <g key={t}>
                  <line x1={x(t)} x2={x(t)} y1={0} y2={rowH * rows.length} stroke={COLORS.grid} />
                  <text x={x(t)} y={rowH * rows.length + 16} textAnchor="middle" fontSize={10.5} fill={COLORS.inkSoft} fontFamily="var(--font-mono), monospace">
                    {pct(t, 0)}
                  </text>
                </g>
              ))}
              <line x1={x(0)} x2={x(0)} y1={-2} y2={rowH * rows.length + 2} stroke={COLORS.ink} strokeWidth={1.5} strokeDasharray="4 3" />
              {rows.map((r, i) => {
                const y = i * rowH + rowH / 2;
                const c = sectorColor(r.sector, sectors);
                return (
                  <g
                    key={r.ticker}
                    tabIndex={0}
                    role="img"
                    aria-label={`${r.ticker}: expected return ${signedPct(r.ret, 0)}, 95% range ${signedPct(r.low, 0)} to ${signedPct(r.high, 0)}${r.spansZero ? ", reaches zero" : ""}`}
                    onPointerMove={(e) => {
                      const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                      setHover({ i, x: e.clientX - box.left, y: e.clientY - box.top });
                    }}
                    onPointerLeave={() => setHover(null)}
                    onFocus={() => setHover({ i, x: LEFT + x(r.ret), y: TOP + y })}
                    onBlur={() => setHover(null)}
                  >
                    <rect x={-LEFT} y={i * rowH} width={width} height={rowH} fill="transparent" />
                    <text x={-8} y={y} textAnchor="end" dominantBaseline="central" fontSize={12} fontWeight={600} fill={COLORS.ink} fontFamily="var(--font-mono), monospace">
                      {r.ticker}
                    </text>
                    <line x1={x(r.low)} x2={x(r.high)} y1={y} y2={y} stroke={c} strokeWidth={2} strokeLinecap="round" opacity={0.75} />
                    <line x1={x(r.low)} x2={x(r.low)} y1={y - 4} y2={y + 4} stroke={c} strokeWidth={2} />
                    <line x1={x(r.high)} x2={x(r.high)} y1={y - 4} y2={y + 4} stroke={c} strokeWidth={2} />
                    <circle cx={x(r.ret)} cy={y} r={5} fill={c} stroke="#fff" strokeWidth={2} />
                    <text x={plotW + 10} y={y} dominantBaseline="central" fontSize={11} fill={COLORS.inkSoft} fontFamily="var(--font-mono), monospace">
                      {r.weight !== null ? pct(r.weight, 0) : ""}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        ) : null}
        <Tooltip x={hover?.x} y={hover?.y} visible={!!hv} containerWidth={width} width={200}>
          {hv ? (
            <>
              <strong>{hv.ticker}</strong>
              <div>Guess: {signedPct(hv.ret, 1)} a year</div>
              <div>
                95% range: {signedPct(hv.low, 0)} to {signedPct(hv.high, 0)}
              </div>
              {hv.weight !== null ? <div>Optimizer weight: {pct(hv.weight, 1)}</div> : null}
            </>
          ) : null}
        </Tooltip>
      </div>
      <div className={s.legend}>
        <span>● guess, ─ 95% range</span>
        <span>┆ zero return</span>
        {portfolios ? <span>right column: weight the max Sharpe mix gave it</span> : null}
      </div>
    </div>
  );
}
