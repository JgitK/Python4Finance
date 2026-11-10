"use client";

// The weights of one portfolio, beside the cloud.
//
// Wide: a small bar chart, one row for each stock. The rows keep the
// basket order (by sector), so two portfolios compare row by row. A bar
// width is the weight over the largest weight.
// Compact (a phone): one segmented bar of the whole 100%, with the three
// largest weights in text. The section label lists every weight.

import type { Performance } from "@/lib/portfolio";
import { useStore } from "@/lib/store";
import { pct, sectorColor, sharpeFmt } from "@/lib/theme";
import styles from "../03-risk/core.module.css";

export interface WeightsPanelProps {
  title: string;
  weights: number[] | null;
  performance: Performance | null;
  /** A line under the title. */
  note?: string;
  compact?: boolean;
}

export function WeightsPanel({ title, weights, performance, note, compact = false }: WeightsPanelProps) {
  const { stats, data } = useStore();
  if (!stats) return null;
  const t = stats.tickers;
  const colors = stats.sectors.map((s) => sectorColor(s, data?.meta.sectors));
  const max = weights ? Math.max(...weights, 1e-9) : 1;
  const all = weights ? t.map((x, i) => `${x} ${pct(weights[i])}`).join(", ") : "";
  const perf = performance
    ? `ret ${pct(performance.annualReturn)} · vol ${pct(performance.annualVol)} · Sharpe ${sharpeFmt(performance.sharpe)}`
    : null;

  if (compact) {
    const top = weights
      ? t
          .map((x, i) => ({ x, w: weights[i] }))
          .sort((a, b) => b.w - a.w)
          .slice(0, 3)
      : [];
    return (
      <section className={styles.weights} aria-label={`Weights of ${title}: ${all || "none"}`}>
        <div className={styles.weightsHead}>
          <strong style={{ display: "inline" }}>{title}</strong> {perf ? <span>· {perf}</span> : note ? <span>· {note}</span> : null}
        </div>
        {weights ? (
          <>
            <div className={styles.segBar} aria-hidden="true">
              {t.map((x, i) =>
                weights[i] > 0.002 ? <span key={x} title={`${x} ${pct(weights[i])}`} style={{ flexGrow: weights[i], background: colors[i] }} /> : null,
              )}
            </div>
            <div className={styles.readout}>
              {top.map((d) => `${d.x} ${pct(d.w, 0)}`).join(" · ")}
              {t.length > 3 ? " · …" : ""}
            </div>
          </>
        ) : null}
      </section>
    );
  }

  return (
    <section className={styles.weights} aria-label={`Weights of ${title}`}>
      <div className={styles.weightsHead}>
        <strong>{title}</strong>
        {perf ? <span>{perf}</span> : null}
        {note ? <div>{note}</div> : null}
      </div>
      {weights ? (
        <ul className={styles.weightsList}>
          {t.map((x, i) => (
            <li key={x} className={styles.weightRow}>
              <span className={styles.tick}>
                <span className={styles.dot} style={{ background: colors[i] }} aria-hidden="true" />
                {x}
              </span>
              <span className={styles.track} aria-hidden="true">
                <span className={styles.bar} style={{ width: `${(weights[i] / max) * 100}%`, background: "var(--sage)" }} />
              </span>
              <span className={styles.val}>{pct(weights[i])}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
