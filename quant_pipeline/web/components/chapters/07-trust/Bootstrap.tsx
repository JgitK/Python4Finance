"use client";

// Chapter 7, steps 2 and 3: bootstrap.svg. The max Sharpe point of 200
// resamples of the days (the scatter), and how much each weight moves (the
// range bars). The points come from useBootstrap in index.tsx.

import * as d3 from "d3";
import { useMemo, useState } from "react";
import { useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import type { BootstrapPoint } from "@/lib/portfolio";
import { useStore } from "@/lib/store";
import { COLORS, num, pct, sectorColor } from "@/lib/theme";
import { quantile, weightSpread } from "./trust";
import s from "./trust.module.css";

export interface BootState {
  points: BootstrapPoint[];
  done: boolean;
  progress: number;
}

function Resampling({ progress }: { progress: number }) {
  return (
    <div role="status" aria-live="polite">
      <div className={s.note}>Resampling the days… {Math.round(progress * 100)}%</div>
      <div className={s.progress}>
        <i style={{ width: `${progress * 100}%` }} />
      </div>
    </div>
  );
}

const MONO = "var(--font-mono), monospace";

export function BootstrapScatter({ boot }: { boot: BootState }) {
  const { portfolios, stats } = useStore();
  const [ref, { width, height }] = useChartSize<HTMLDivElement>();
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);
  const real = portfolios?.maxSharpe.performance ?? null;
  const pts = boot.points;

  const summary = useMemo(() => {
    if (pts.length < 5) return null;
    const r = pts.map((p) => p.ret).sort((a, b) => a - b);
    const v = pts.map((p) => p.risk).sort((a, b) => a - b);
    return { r10: quantile(r, 0.1), r90: quantile(r, 0.9), v10: quantile(v, 0.1), v90: quantile(v, 0.9) };
  }, [pts]);

  if (!stats || !real) return <p className={s.empty}>Pick some stocks in chapter 1 to see the resampling.</p>;

  const L = 44;
  const R = 12;
  const T = 8;
  const B = 34;
  const pw = Math.max(40, width - L - R);
  const ph = Math.max(40, height - T - B);
  const xs = [real.annualVol, ...pts.map((p) => p.risk)];
  const ys = [real.annualReturn, ...pts.map((p) => p.ret)];
  const x = d3.scaleLinear().domain([Math.min(...xs), Math.max(...xs)]).nice().range([0, pw]);
  const y = d3.scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).nice().range([ph, 0]);
  const hv = hover ? pts[hover.i] : null;

  return (
    <div className={s.stack}>
      <p className={s.point}>
        Same stocks, same years, but the days are drawn again with replacement, 200 times. Each dot is the{" "}
        <strong>&ldquo;best&rdquo; mix</strong> that one redraw finds. The best mix moves when the data moves.
      </p>
      {!boot.done ? <Resampling progress={boot.progress} /> : null}
      <div ref={ref} className={s.chartBox}>
        {width > 0 && height > 0 ? (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`Scatter of the max Sharpe point of ${pts.length} bootstrap samples, risk against return. The real max Sharpe point has risk ${pct(real.annualVol)} and return ${pct(real.annualReturn)}.${summary ? ` Samples return from ${pct(summary.r10, 0)} to ${pct(summary.r90, 0)} (10th to 90th percentile).` : ""}`}
            style={{ display: "block", overflow: "hidden" }}
          >
            <g transform={`translate(${L},${T})`}>
              {y.ticks(5).map((t) => (
                <g key={`y${t}`}>
                  <line x1={0} x2={pw} y1={y(t)} y2={y(t)} stroke={COLORS.grid} />
                  <text x={-6} y={y(t)} textAnchor="end" dominantBaseline="central" fontSize={10.5} fill={COLORS.inkSoft} fontFamily={MONO}>
                    {pct(t, 0)}
                  </text>
                </g>
              ))}
              {x.ticks(width < 520 ? 4 : 6).map((t) => (
                <text key={`x${t}`} x={x(t)} y={ph + 15} textAnchor="middle" fontSize={10.5} fill={COLORS.inkSoft} fontFamily={MONO}>
                  {pct(t, 0)}
                </text>
              ))}
              <text x={pw / 2} y={ph + 30} textAnchor="middle" fontSize={10.5} fill={COLORS.tanDeep} fontFamily={MONO}>
                risk (annual volatility)
              </text>
              <text transform={`translate(${-34},${ph / 2}) rotate(-90)`} textAnchor="middle" fontSize={10.5} fill={COLORS.tanDeep} fontFamily={MONO}>
                return
              </text>
              {pts.map((p, i) => (
                <circle
                  key={i}
                  cx={x(p.risk)}
                  cy={y(p.ret)}
                  r={4}
                  fill={COLORS.sage}
                  fillOpacity={0.6}
                  stroke="#fff"
                  strokeWidth={1}
                  onPointerMove={(e) => {
                    const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setHover({ i, x: e.clientX - box.left, y: e.clientY - box.top });
                  }}
                  onPointerLeave={() => setHover(null)}
                />
              ))}
              <g transform={`translate(${x(real.annualVol)},${y(real.annualReturn)})`}>
                <path d="M0,-9 L9,0 L0,9 L-9,0 Z" fill={COLORS.ink} stroke="#fff" strokeWidth={2} />
                <text x={13} y={-8} fontSize={11} fontWeight={600} fill={COLORS.ink} fontFamily={MONO} stroke="#fff" strokeWidth={3} paintOrder="stroke">
                  real max Sharpe
                </text>
              </g>
            </g>
          </svg>
        ) : null}
        <Tooltip x={hover?.x} y={hover?.y} visible={!!hv} containerWidth={width}>
          {hv ? (
            <>
              <strong>One resample</strong>
              <div>
                Risk {pct(hv.risk, 1)} · return {pct(hv.ret, 1)}
              </div>
              <div>Sharpe {num(hv.sharpe)}</div>
            </>
          ) : null}
        </Tooltip>
      </div>
      <div className={s.legend}>
        <span>
          <i className={s.keyDiamond} style={{ background: COLORS.ink }} /> the real best mix
        </span>
        <span>
          <i className={s.key} style={{ background: COLORS.sage, borderRadius: "50%" }} /> best mix of one resample
        </span>
      </div>
      {summary ? (
        <p className={s.note}>
          Across the redraws, the best mix promised anything from {pct(summary.r10, 0)} to {pct(summary.r90, 0)} a
          year (middle 80%), at a risk of {pct(summary.v10, 0)} to {pct(summary.v90, 0)}. Each point also comes from
          a search of 2,000 random mixes, so part of the spread is the search itself.
        </p>
      ) : null}
    </div>
  );
}

export function BootstrapWeights({ boot }: { boot: BootState }) {
  const { stats, portfolios, data } = useStore();
  const [ref, { width, height }] = useChartSize<HTMLDivElement>();
  const sectors = data?.meta.sectors ?? [];
  const spread = useMemo(() => (stats ? weightSpread(boot.points, stats.tickers) : []), [boot.points, stats]);

  if (!stats || !portfolios) return <p className={s.empty}>Pick some stocks in chapter 1 to see the weights move.</p>;

  const real = portfolios.maxSharpe.weights;
  const order = stats.tickers.map((_, i) => i).sort((a, b) => real[b] - real[a]);
  const L = 50;
  const R = 10;
  const T = 4;
  const B = 24;
  const pw = Math.max(40, width - L - R);
  const max = Math.max(0.05, ...spread.map((p) => (Number.isFinite(p.max) ? p.max : 0)), ...real);
  const x = d3.scaleLinear().domain([0, max]).nice().range([0, pw]);
  const rowH = Math.max(16, Math.min(40, (height - T - B) / Math.max(1, order.length)));

  return (
    <div className={s.stack}>
      <p className={s.point}>
        How much does each weight move between redraws? A long bar means the optimizer keeps changing its mind
        about that stock. A <strong>long</strong> bar is a weight you should not trust to the decimal.
      </p>
      {!boot.done ? <Resampling progress={boot.progress} /> : null}
      <div ref={ref} className={s.chartBox} style={{ minHeight: order.length * 18 + 40 }}>
        {width > 0 && height > 0 && spread.length > 0 && boot.points.length >= 5 ? (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`Range of the weight of each stock across ${boot.points.length} bootstrap samples. ${order.map((i) => `${stats.tickers[i]}: real ${pct(real[i], 0)}, middle 80% ${pct(spread[i].p10, 0)} to ${pct(spread[i].p90, 0)}`).join("; ")}.`}
            style={{ display: "block", overflow: "hidden" }}
          >
            <g transform={`translate(${L},${T})`}>
              {x.ticks(width < 520 ? 4 : 6).map((t) => (
                <g key={t}>
                  <line x1={x(t)} x2={x(t)} y1={0} y2={rowH * order.length} stroke={COLORS.grid} />
                  <text x={x(t)} y={rowH * order.length + 15} textAnchor="middle" fontSize={10.5} fill={COLORS.inkSoft} fontFamily={MONO}>
                    {pct(t, 0)}
                  </text>
                </g>
              ))}
              {order.map((i, k) => {
                const p = spread[i];
                const yc = k * rowH + rowH / 2;
                const c = sectorColor(stats.sectors[i], sectors);
                return (
                  <g key={stats.tickers[i]}>
                    <title>{`${stats.tickers[i]}: real ${pct(real[i], 1)}; middle 80% ${pct(p.p10, 1)} to ${pct(p.p90, 1)}; extremes ${pct(p.min, 1)} to ${pct(p.max, 1)}`}</title>
                    <text x={-8} y={yc} textAnchor="end" dominantBaseline="central" fontSize={12} fontWeight={600} fill={COLORS.ink} fontFamily={MONO}>
                      {stats.tickers[i]}
                    </text>
                    <line x1={x(p.min)} x2={x(p.max)} y1={yc} y2={yc} stroke={c} strokeWidth={1.5} opacity={0.6} />
                    <rect x={x(p.p10)} y={yc - 5} width={Math.max(2, x(p.p90) - x(p.p10))} height={10} rx={3} fill={c} opacity={0.75} />
                    <line x1={x(p.median)} x2={x(p.median)} y1={yc - 6} y2={yc + 6} stroke="#fff" strokeWidth={2} />
                    <path d={`M${x(real[i])},${yc - 7} l6,7 l-6,7 l-6,-7 Z`} fill={COLORS.ink} stroke="#fff" strokeWidth={1.5} />
                  </g>
                );
              })}
            </g>
          </svg>
        ) : null}
      </div>
      <div className={s.legend}>
        <span>
          <i className={s.keyDiamond} style={{ background: COLORS.ink }} /> real weight
        </span>
        <span>
          <i className={s.key} style={{ background: COLORS.sage }} /> middle 80% of redraws
        </span>
        <span>─ lowest to highest</span>
      </div>
    </div>
  );
}
