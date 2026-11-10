"use client";

// Chapter 7, step 5: the gap between in-sample and realized Sharpe, and the
// per-window chart (portfolio return minus SPY return). The per-window
// chart takes any count of windows.

import * as d3 from "d3";
import { useMemo, useState } from "react";
import { useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { useStore } from "@/lib/store";
import { COLORS, GAIN, LOSS, num, pct, signedPct } from "@/lib/theme";
import { ratio, windowDiffs, winCount } from "./trust";
import s from "./trust.module.css";

const MONO = "var(--font-mono), monospace";

function SharpeGap({ inSample, realized }: { inSample: number; realized: number }) {
  const [ref, { width }] = useChartSize<HTMLDivElement>();
  const rowH = 30;
  const L = width < 520 ? 82 : 96;
  const hi = Math.max(inSample, realized, 0.0001);
  const lo = Math.min(0, inSample, realized);
  const pw = Math.max(40, width - L - 60);
  const xOf = (v: number) => ((v - lo) / (hi - lo)) * pw;
  const items = [
    { name: "In-sample", v: inSample, c: COLORS.stone, hint: "on the days it was fitted to" },
    { name: "Realized", v: realized, c: COLORS.sageDeep, hint: "on days it never saw" },
  ];
  const k = ratio(inSample, realized);
  return (
    <div className={s.stack} style={{ flex: "none" }}>
      <div ref={ref} className={s.fixed} style={{ height: rowH * 2 + 4 }}>
        {width > 0 ? (
          <svg width={width} height={rowH * 2 + 4} role="img" aria-label={`Sharpe ratio in-sample ${num(inSample)}, realized ${num(realized)}.`} style={{ display: "block" }}>
            <line x1={L + xOf(0)} x2={L + xOf(0)} y1={0} y2={rowH * 2} stroke={COLORS.ink} />
            {items.map((it, i) => {
              const x0 = L + Math.min(xOf(0), xOf(it.v));
              const w = Math.max(2, Math.abs(xOf(it.v) - xOf(0)));
              return (
                <g key={it.name}>
                  <text x={L - 8} y={i * rowH + rowH / 2} textAnchor="end" dominantBaseline="central" fontSize={12} fontWeight={600} fill={COLORS.ink} fontFamily={MONO}>
                    {it.name}
                  </text>
                  <rect x={x0} y={i * rowH + 5} width={w} height={rowH - 10} rx={3} fill={it.c} />
                  <text x={x0 + w + 6} y={i * rowH + rowH / 2} dominantBaseline="central" fontSize={12} fontWeight={600} fill={COLORS.ink} fontFamily={MONO}>
                    {num(it.v)}
                  </text>
                </g>
              );
            })}
          </svg>
        ) : null}
      </div>
      <p className={s.point}>
        <strong>The gap: {num(inSample - realized)} Sharpe points.</strong> On the days it was fitted to, the mix
        scored {num(inSample)}.{" "}
        {k !== null ? `On new days it scored ${num(realized)}, about ${num(k, 1)} times less. ` : `On new days it scored ${num(realized)}. `}
        The optimizer finds the luck in old prices and calls it skill.
      </p>
    </div>
  );
}

function PerWindow() {
  const { data } = useStore();
  const sc = data?.scorecard;
  const diffs = useMemo(() => windowDiffs(sc?.perWindow), [sc?.perWindow]);
  const [ref, { width, height }] = useChartSize<HTMLDivElement>();
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);
  if (!sc) return null;
  if (diffs.length === 0) return <p className={s.note}>No per-window results in the file.</p>;

  const L = 44;
  const R = 6;
  const T = 6;
  const B = 22;
  const pw = Math.max(40, width - L - R);
  const ph = Math.max(30, height - T - B);
  const m = Math.max(0.01, ...diffs.map((d) => Math.abs(d.diff)));
  const y = d3.scaleLinear().domain([-m, m]).nice().range([ph, 0]);
  const band = d3.scaleBand<number>().domain(diffs.map((_, i) => i)).range([0, pw]).paddingInner(diffs.length > 40 ? 0.15 : 0.3).paddingOuter(0.1);
  const wins = winCount(diffs);
  const hv = hover ? diffs[hover.i] : null;
  // Date labels: evenly spaced, the first and the last included.
  const nLabels = Math.min(diffs.length, Math.max(2, Math.floor(pw / 80)));
  const trimmed = Array.from(new Set(Array.from({ length: nLabels }, (_, k) => Math.round((k * (diffs.length - 1)) / Math.max(1, nLabels - 1)))));

  return (
    <div className={s.stack}>
      <div className={s.caption}>
        Each window: portfolio return minus SPY return · beat SPY in {wins} of {diffs.length}
      </div>
      <div ref={ref} className={s.chartBox}>
        {width > 0 && height > 0 ? (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`Portfolio return minus SPY return in each of ${diffs.length} windows. The portfolio beat SPY in ${wins} of them.`}
            style={{ display: "block", overflow: "hidden" }}
          >
            <g transform={`translate(${L},${T})`}>
              {y.ticks(4).map((t) => (
                <g key={t}>
                  <line x1={0} x2={pw} y1={y(t)} y2={y(t)} stroke={t === 0 ? COLORS.ink : COLORS.grid} />
                  <text x={-6} y={y(t)} textAnchor="end" dominantBaseline="central" fontSize={10.5} fill={COLORS.inkSoft} fontFamily={MONO}>
                    {signedPct(t, 0)}
                  </text>
                </g>
              ))}
              {diffs.map((d, i) => {
                const bw = Math.min(band.bandwidth(), 28);
                const x0 = (band(i) ?? 0) + (band.bandwidth() - bw) / 2;
                const up = d.diff >= 0;
                return (
                  <rect
                    key={d.date}
                    x={x0}
                    width={Math.max(1.5, bw)}
                    y={up ? y(d.diff) : y(0)}
                    height={Math.max(1, Math.abs(y(d.diff) - y(0)))}
                    fill={up ? GAIN : LOSS}
                    onPointerMove={(e) => {
                      const box = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                      setHover({ i, x: e.clientX - box.left, y: e.clientY - box.top });
                    }}
                    onPointerLeave={() => setHover(null)}
                  />
                );
              })}
              {trimmed.map((i) => (
                <text key={i} x={(band(i) ?? 0) + band.bandwidth() / 2} y={ph + 15} textAnchor={i === 0 ? "start" : i === diffs.length - 1 ? "end" : "middle"} fontSize={10} fill={COLORS.inkSoft} fontFamily={MONO}>
                  {diffs[i].date.slice(0, 7)}
                </text>
              ))}
            </g>
          </svg>
        ) : null}
        <Tooltip x={hover?.x} y={hover?.y} visible={!!hv} containerWidth={width}>
          {hv ? (
            <>
              <strong>{hv.date}</strong>
              <div>Portfolio {signedPct(hv.portfolio, 1)}</div>
              <div>SPY {signedPct(hv.benchmark, 1)}</div>
              <div>
                {hv.diff >= 0 ? "▲ Beat SPY by" : "▼ Behind SPY by"} {pct(Math.abs(hv.diff), 1)}
              </div>
            </>
          ) : null}
        </Tooltip>
      </div>
      <div className={s.legend}>
        <span>
          <i className={s.key} style={{ background: GAIN }} /> + beat SPY
        </span>
        <span>
          <i className={s.key} style={{ background: LOSS }} /> − behind SPY
        </span>
        <span>holds overlap, so neighbours are not independent</span>
      </div>
    </div>
  );
}

export function GapView() {
  const { data } = useStore();
  const sc = data?.scorecard;
  if (!sc) return <p className={s.empty}>The scorecard file did not load.</p>;
  return (
    <div className={s.stack}>
      <SharpeGap inSample={sc.inSampleSharpe} realized={sc.realizedSharpe} />
      <PerWindow />
    </div>
  );
}
