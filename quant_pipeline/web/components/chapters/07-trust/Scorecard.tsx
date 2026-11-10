"use client";

// Chapter 7, step 4: scorecard.svg. The rows of scorecard.json compared on
// mean Sharpe, and the other measures in a small table. Every number comes
// from the data. A null cell reads "not measured", never 0.

import { useChartSize } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { COLORS, NEUTRAL, num, pct, signedPct } from "@/lib/theme";
import type { Scorecard } from "@/lib/types";
import { rankByMeanSharpe } from "./trust";
import s from "./trust.module.css";

const MONO = "var(--font-mono), monospace";

/** One colour for each method, so the colour follows the entity. */
const ROW_COLOR: Record<string, string> = {
  Optimizer: COLORS.sageDeep,
  "Equal weight": COLORS.tan,
  SPY: NEUTRAL,
  "Random order": COLORS.clay,
};

const Missing = () => <span className={s.missing}>not measured</span>;

function cell(v: number | null, fmt: (x: number) => string) {
  return v === null || v === undefined || !Number.isFinite(v) ? <Missing /> : fmt(v);
}

function ScoreBars({ rows }: { rows: Scorecard["rows"] }) {
  const [ref, { width }] = useChartSize<HTMLDivElement>();
  const rowH = 34;
  const L = width < 520 ? 92 : 104;
  const R = 8;
  const values = rows.map((r) => r.meanSharpe).filter((v): v is number => v !== null && Number.isFinite(v));
  const lo = Math.min(0, ...values);
  const hi = Math.max(0.0001, ...values);
  const pw = Math.max(40, width - L - R - 56);
  const xOf = (v: number) => ((v - lo) / (hi - lo)) * pw;
  const zero = xOf(0);
  const height = rows.length * rowH + 4;
  return (
    <div ref={ref} className={s.fixed} style={{ height }}>
      {width > 0 ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Mean Sharpe ratio of the walk-forward test. ${rows.map((r) => `${r.name}: ${r.meanSharpe === null ? "not measured" : num(r.meanSharpe)}`).join("; ")}.`}
          style={{ display: "block" }}
        >
          <line x1={L + zero} x2={L + zero} y1={0} y2={height - 2} stroke={COLORS.ink} strokeWidth={1} />
          {rows.map((r, i) => {
            const y = i * rowH + 2;
            const v = r.meanSharpe;
            const ok = v !== null && Number.isFinite(v);
            const x0 = ok ? L + Math.min(zero, xOf(v as number)) : L + zero;
            const w = ok ? Math.max(2, Math.abs(xOf(v as number) - zero)) : 0;
            return (
              <g key={r.name}>
                <text x={L - 8} y={y + rowH / 2 - 1} textAnchor="end" dominantBaseline="central" fontSize={12} fontWeight={600} fill={COLORS.ink} fontFamily={MONO}>
                  {r.name}
                </text>
                {ok ? (
                  <>
                    <rect x={x0} y={y + 6} width={w} height={rowH - 14} rx={3} fill={ROW_COLOR[r.name] ?? NEUTRAL} />
                    <text x={x0 + w + 6} y={y + rowH / 2 - 1} dominantBaseline="central" fontSize={12} fill={COLORS.ink} fontFamily={MONO} fontWeight={600}>
                      {num(v as number)}
                    </text>
                  </>
                ) : (
                  <text x={L + zero + 6} y={y + rowH / 2 - 1} dominantBaseline="central" fontSize={11} fontStyle="italic" fill={COLORS.inkSoft}>
                    not measured
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      ) : null}
    </div>
  );
}

export function ScorecardView() {
  const { data } = useStore();
  const sc = data?.scorecard;
  if (!sc || !Array.isArray(sc.rows) || sc.rows.length === 0) return <p className={s.empty}>The scorecard file did not load.</p>;
  const rank = rankByMeanSharpe(sc.rows);
  const best = rank.order[0];
  const opt = sc.rows.find((r) => r.name === "Optimizer");
  const verdict =
    rank.optimizerRank === null
      ? "The optimizer has no mean Sharpe in the record."
      : rank.optimizerRank === 1
        ? `The optimizer comes first on mean Sharpe (${num(opt!.meanSharpe as number)}), out of ${rank.order.length} methods that were measured.`
        : `The optimizer comes ${rank.optimizerRank} of ${rank.order.length} on mean Sharpe (${num(opt!.meanSharpe as number)}). ${best} comes first.`;
  return (
    <div className={s.stack}>
      <p className={s.point}>
        {verdict} Walk-forward means: choose the mix on old data, then hold it on days that it has never seen
        {sc.holdDays ? ` (${sc.holdDays} days)` : ""}, {sc.windows} times.
      </p>
      <div className={s.caption}>Mean Sharpe ratio over {sc.windows} windows (higher is better)</div>
      <ScoreBars rows={sc.rows} />
      <div className={s.tableScroll} tabIndex={0} role="region" aria-label="Other measures of the scorecard">
        <table className={s.table}>
          <thead>
            <tr>
              <th scope="col">Method</th>
              <th scope="col">Median excess</th>
              <th scope="col">Won on return</th>
              <th scope="col">Won on Sharpe</th>
            </tr>
          </thead>
          <tbody>
            {sc.rows.flatMap((r) => [
              <tr key={r.name}>
                <th scope="row">{r.name}</th>
                <td>{cell(r.medianExcess, (v) => signedPct(v, 1))}</td>
                <td>{cell(r.winReturn, (v) => pct(v, 0))}</td>
                <td>{cell(r.winSharpe, (v) => pct(v, 0))}</td>
              </tr>,
              <tr key={`${r.name}-note`} className={s.noteRow}>
                <td colSpan={4}>{r.note}</td>
              </tr>,
            ])}
          </tbody>
        </table>
      </div>
      <p className={s.note}>
        &ldquo;Won&rdquo; means: beat SPY in a window. Windows overlap, so they are not independent tests and a small
        gap between two methods is inside the noise.
      </p>
    </div>
  );
}

