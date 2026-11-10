"use client";

// The pane of chapter 5: frontier.canvas, the weights beside it, the
// three portfolio buttons in the title bar, and the legend in the footer.
//
// The weights panel shows:
//   step 0   a hint (no portfolio yet)
//   step 1   portfolio #1, the one random mix
//   step 2+  the dot under the pointer, else the selected portfolio

import { useCallback, useMemo, useState } from "react";
import { Pane, useChartSize } from "@/components/scrolly";
import { weightsAt, portfolioPerformance } from "@/lib/portfolio";
import { useStore, type PortfolioKey } from "@/lib/store";
import { SHARPE_RANGE } from "@/lib/theme";
import { usePaneGate } from "../03-risk/kit";
import styles from "../03-risk/core.module.css";
import { FrontierChart } from "./FrontierChart";
import { WeightsPanel } from "./WeightsPanel";

const BUTTONS: { key: PortfolioKey; label: string; glyph: string }[] = [
  { key: "maxSharpe", label: "max Sharpe", glyph: "★" },
  { key: "minVol", label: "min vol", glyph: "▲" },
  { key: "equal", label: "equal", glyph: "■" },
];

export function FrontierPane({ step }: { step: number }) {
  const { stats, mc, selected, selectedPortfolio, setSelectedPortfolio, riskFree, tradingDays } = useStore();
  const gate = usePaneGate();
  const [hover, setHoverRaw] = useState(-1);
  const setHover = useCallback((k: number) => setHoverRaw((p) => (p === k ? p : k)), []);
  const [outer, { width }] = useChartSize();
  const stack = width > 0 && width < 600;

  const shown = useMemo(() => {
    if (!stats || !mc) return null;
    const pick = (k: number, title: string, note?: string) => {
      const w = weightsAt(mc, k);
      return { title, note, weights: w, performance: portfolioPerformance(w, stats.meanDaily, stats.covDaily, tradingDays, riskFree) };
    };
    if (step <= 0) return { title: "No mix yet", note: "Each dot is one stock: 100% of the money in it.", weights: null, performance: null };
    if (step === 1) return pick(0, "One random mix", "Portfolio #1: a random share for each stock.");
    if (hover >= 0 && hover < mc.n) return pick(hover, `Portfolio #${hover + 1}`, "Under the pointer. Click to keep it.");
    if (selected) return { title: selected.label, note: undefined, weights: selected.weights, performance: selected.performance };
    return null;
  }, [stats, mc, step, hover, selected, riskFree, tradingDays]);

  const controls = (
    <div className={styles.btnRow} role="group" aria-label="Pick a named portfolio">
      {BUTTONS.map((b) => (
        <button
          key={b.key}
          type="button"
          className={`chip-btn${selectedPortfolio === b.key ? " on" : ""}`}
          aria-pressed={selectedPortfolio === b.key}
          aria-label={b.label}
          title={b.label}
          onClick={() => setSelectedPortfolio(b.key)}
        >
          <span aria-hidden="true">{b.glyph}</span>
          <span className={styles.wideOnly} aria-hidden="true">
            {` ${b.label}`}
          </span>
        </button>
      ))}
    </div>
  );

  const footer = (
    <div className={styles.footRow}>
      <span className={styles.key}>
        Sharpe low
        <span className={styles.gradient} style={{ background: `linear-gradient(90deg, ${SHARPE_RANGE.join(", ")})` }} aria-hidden="true" />
        high
      </span>
      {step >= 3 ? (
        <span className={styles.key}>
          <span className={styles.keyLine} style={{ color: "var(--ink)" }} aria-hidden="true" /> efficient frontier
        </span>
      ) : null}
      {step >= 4 ? (
        <span className={styles.wideOnly}>
          <span className={styles.key}>
            <span className={styles.keyDash} style={{ color: "var(--tan-deep)" }} aria-hidden="true" /> capital market line
          </span>
          <span>★ max Sharpe · ▲ min vol · ■ equal</span>
        </span>
      ) : null}
      {step >= 5 ? <span>seed 42: the same basket always gives the same cloud</span> : null}
    </div>
  );

  return (
    <Pane title="frontier.canvas" controls={controls} footer={footer} ariaLabel="frontier.canvas: ten thousand random portfolios">
      {gate ? (
        <div className={styles.fill} style={{ display: "flex" }}>
          {gate}
        </div>
      ) : (
        <div ref={outer} className={`${styles.split}${stack ? ` ${styles.stack}` : ""}`}>
          <FrontierChart step={step} hover={hover} onHover={setHover} />
          {shown ? (
            <WeightsPanel title={shown.title} note={shown.note} weights={shown.weights} performance={shown.performance} compact={stack} />
          ) : null}
        </div>
      )}
    </Pane>
  );
}
