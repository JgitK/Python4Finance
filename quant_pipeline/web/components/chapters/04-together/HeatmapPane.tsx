"use client";

// The pane of the second Scrolly of chapter 4: correlation.csv, with a
// correlation / covariance toggle, a colour bar with the mean, and a note
// for each step. Step 3 switches the table to covariance; an earlier step
// switches it back. The toggle works at every step.

import { useEffect, useId, useMemo, useState } from "react";
import { Pane } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { CORR_MID, CORR_NEG, CORR_POS, num, pct } from "@/lib/theme";
import { usePaneGate } from "../03-risk/kit";
import styles from "../03-risk/core.module.css";
import { HeatmapChart } from "./HeatmapChart";
import { annualCov, extremePairs, maxAbsOffDiagonal } from "./math";

function ColourBar({ mode, mean, covMax, showMean }: { mode: "corr" | "cov"; mean: number; covMax: number; showMean: boolean }) {
  const id = useId().replace(/:/g, "");
  const W = 120;
  const pos = ((Math.max(-1, Math.min(1, mean)) + 1) / 2) * W;
  const lo = mode === "corr" ? "−1" : `−${num(covMax, 3).replace(/^0/, "")}`;
  const hi = mode === "corr" ? "+1" : `+${num(covMax, 3).replace(/^0/, "")}`;
  return (
    <span className={styles.key}>
      <span className="mono">{lo} apart</span>
      <svg width={W} height={18} role="img" aria-label={`Colour scale from ${lo}, sage, to ${hi}, clay${showMean && mode === "corr" ? `. Mean correlation ${num(mean)}` : ""}`}>
        <defs>
          <linearGradient id={id}>
            <stop offset="0%" stopColor={CORR_NEG} />
            <stop offset="50%" stopColor={CORR_MID} />
            <stop offset="100%" stopColor={CORR_POS} />
          </linearGradient>
        </defs>
        <rect x={0} y={5} width={W} height={8} rx={4} fill={`url(#${id})`} />
        {showMean && mode === "corr" ? (
          <g transform={`translate(${pos},0)`}>
            <line y1={1} y2={17} stroke="var(--ink)" strokeWidth={2} />
          </g>
        ) : null}
      </svg>
      <span className="mono">{hi} together</span>
    </span>
  );
}

export function HeatmapPane({ step }: { step: number }) {
  const { stats, data, tradingDays } = useStore();
  const gate = usePaneGate();
  const [mode, setMode] = useState<"corr" | "cov">("corr");

  // Step 3 is about covariance. Leaving it goes back to correlation.
  useEffect(() => {
    setMode(step >= 3 ? "cov" : "corr");
  }, [step]);

  const derived = useMemo(() => {
    if (!stats) return null;
    const ex = extremePairs(stats.correlation);
    if (!ex) return null;
    const cov = annualCov(stats.covDaily, tradingDays);
    return { ex, cov, covMax: maxAbsOffDiagonal(cov) };
  }, [stats, tradingDays]);

  const toggle = (
    <div className={styles.btnRow} role="group" aria-label="Show correlation or covariance">
      <button type="button" className={`chip-btn${mode === "corr" ? " on" : ""}`} aria-pressed={mode === "corr"} onClick={() => setMode("corr")}>
        ρ
      </button>
      <button type="button" className={`chip-btn${mode === "cov" ? " on" : ""}`} aria-pressed={mode === "cov"} onClick={() => setMode("cov")}>
        cov
      </button>
    </div>
  );

  if (gate || !stats || !derived) {
    return (
      <Pane title="correlation.csv">
        <div className={styles.fill} style={{ display: "flex" }}>
          {gate}
        </div>
      </Pane>
    );
  }

  const { ex, cov, covMax } = derived;
  const t = stats.tickers;
  const v = stats.annualVol;
  const n = t.length;
  const twins = `${t[ex.max.i]} & ${t[ex.max.j]}`;
  const opposites = `${t[ex.min.i]} & ${t[ex.min.j]}`;

  let note: React.ReactNode;
  if (step <= 0) {
    note = (
      <>
        {n} stocks · {(n * (n - 1)) / 2} pairs · grouped by sector
      </>
    );
  } else if (step === 1) {
    note = (
      <>
        <span className={styles.key}>
          <span className={styles.keyLine} aria-hidden="true" /> twins: <strong>{twins}</strong>, ρ {num(ex.max.value)}
        </span>
      </>
    );
  } else if (step === 2) {
    note = (
      <>
        <span className={styles.key}>
          <span className={styles.keyLine} aria-hidden="true" /> twins <strong>{num(ex.max.value)}</strong>
        </span>{" "}
        ·{" "}
        <span className={styles.key}>
          <span className={styles.keyDash} aria-hidden="true" /> opposites: <strong>{opposites}</strong>, ρ {num(ex.min.value)}
        </span>{" "}
        · mean ρ <strong>{num(ex.mean)}</strong>
      </>
    );
  } else {
    const { i, j } = ex.max;
    note = (
      <>
        cov = ρ × σ<sub>A</sub> × σ<sub>B</sub>. Twins: {num(ex.max.value)} × {pct(v[i])} × {pct(v[j])} ={" "}
        <strong>{num(cov[i][j], 3)}</strong> a year
      </>
    );
  }

  const footer = (
    <div className={styles.footRow}>
      <ColourBar mode={mode} mean={ex.mean} covMax={covMax} showMean={step >= 2} />
      <span className={styles.footNote} aria-live="polite">
        {note}
      </span>
    </div>
  );

  return (
    <Pane
      title={mode === "corr" ? "correlation.csv" : "covariance.csv"}
      controls={toggle}
      footer={footer}
      ariaLabel="correlation.csv: how each pair of basket stocks moves together"
    >
      <HeatmapChart
        step={step}
        mode={mode}
        tickers={t}
        sectors={stats.sectors}
        allSectors={data?.meta.sectors}
        corr={stats.correlation}
        cov={cov}
        covMax={covMax}
        vols={v}
        max={ex.max}
        min={ex.min}
      />
    </Pane>
  );
}
