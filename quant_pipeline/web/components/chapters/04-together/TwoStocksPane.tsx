"use client";

// The pane of the first Scrolly of chapter 4: two-stocks.svg with its
// controls (the pair, the weight slider, the pretend correlation dial).
//
// Each step sets a start state for the sliders. The reader can move a
// slider at any step; a hand on a slider stops the step animation.
//   0  100% in A, the real correlation.
//   1  The weight slides to the mix of least risk.
//   2  The dial sweeps from +1 to -1, then snaps back to the real value.

import { useEffect, useMemo, useRef, useState } from "react";
import { Pane } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { pct, sectorColor, signed } from "@/lib/theme";
import { usePaneGate } from "../03-risk/kit";
import styles from "../03-risk/core.module.css";
import { extremePairs, minVarianceWeight, mixPoint, straightRisk } from "./math";
import { TwoStocksChart, type Stock } from "./TwoStocksChart";
import { useTween } from "./useTween";
import { usePrefersReducedMotion } from "@/components/scrolly";

export function TwoStocksPane({ step }: { step: number }) {
  const { stats, data } = useStore();
  const gate = usePaneGate();
  const reduced = usePrefersReducedMotion();
  const [chosen, setChosen] = useState<[string, string] | null>(null);
  const [w, setW] = useState(1);
  const [pretend, setPretend] = useState<number | null>(null);
  const tween = useTween();

  // The pair: the reader's pick when both are still in the basket, else
  // the least correlated pair (it bends most), with the higher payer as A.
  const pair = useMemo<[number, number] | null>(() => {
    if (!stats) return null;
    const t = stats.tickers;
    if (chosen) {
      const i = t.indexOf(chosen[0]);
      const j = t.indexOf(chosen[1]);
      if (i >= 0 && j >= 0 && i !== j) return [i, j];
    }
    const ex = extremePairs(stats.correlation);
    if (!ex) return [0, 1];
    const { i, j } = ex.min;
    return stats.annualReturn[i] >= stats.annualReturn[j] ? [i, j] : [j, i];
  }, [stats, chosen]);

  const [a, b] = useMemo<[Stock | null, Stock | null]>(() => {
    if (!stats || !pair) return [null, null];
    const stock = (k: number): Stock => ({
      ticker: stats.tickers[k],
      ret: stats.annualReturn[k],
      vol: stats.annualVol[k],
      color: sectorColor(stats.sectors[k], data?.meta.sectors),
    });
    return [stock(pair[0]), stock(pair[1])];
  }, [stats, pair, data]);
  const realRho = stats && pair ? stats.correlation[pair[0]][pair[1]] : 0;
  const rho = pretend ?? realRho;

  // A ref for the step effect, so it reads the current values. It is
  // set before the step effect runs (effects run in order).
  const live = useRef({ w, rho, realRho, a, b });
  useEffect(() => {
    live.current = { w, rho, realRho, a, b };
  });

  // The step sets the start state of the sliders.
  useEffect(() => {
    const cur = live.current;
    tween.cancel();
    if (step <= 0) {
      setW(1);
      setPretend(null);
    } else if (step === 1) {
      setPretend(null);
      const target = cur.a && cur.b ? minVarianceWeight(cur.a.vol, cur.b.vol, cur.realRho) : 0.5;
      tween.run(cur.w, [{ to: target, ms: reduced ? 0 : 1600 }], setW);
    } else if (step === 2) {
      if (reduced) {
        setPretend(null);
        return;
      }
      // The dial demo: up to +1 (a straight line), down to -1 (most bend), back to the real value.
      tween.run(
        cur.rho,
        [
          { to: 1, ms: 700 },
          { to: 1, ms: 500 },
          { to: -1, ms: 1800 },
          { to: -1, ms: 600 },
          { to: cur.realRho, ms: 900 },
        ],
        setPretend,
        () => setPretend(null),
      );
    }
    // Only a new step starts this. The sliders do not.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, reduced]);

  if (gate || !stats || !a || !b || !pair) {
    return (
      <Pane title="two-stocks.svg">
        <div className={styles.fill} style={{ display: "flex" }}>
          {gate}
        </div>
      </Pane>
    );
  }

  const choose = (slot: 0 | 1, ticker: string) => {
    tween.cancel();
    const cur: [string, string] = [a.ticker, b.ticker];
    const other = cur[1 - slot];
    const next: [string, string] = slot === 0 ? [ticker, other] : [other, ticker];
    // The same stock twice: swap the pair.
    setChosen(ticker === other ? [cur[1], cur[0]] : next);
  };

  const p = mixPoint(w, a.ret, b.ret, a.vol, b.vol, rho);
  const straight = straightRisk(w, a.vol, b.vol);
  const saved = straight - p.risk;
  const wPct = Math.round(w * 100);

  const footer = (
    <div>
      <label className={styles.slider}>
        <span className={styles.sliderLabel}>weight</span>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={wPct}
          onChange={(e) => {
            tween.cancel();
            setW(Number(e.target.value) / 100);
          }}
          aria-valuetext={`${wPct}% ${a.ticker}, ${100 - wPct}% ${b.ticker}`}
          aria-label={`Weight of ${a.ticker} in the mix`}
        />
        <span className={styles.sliderValue}>
          {wPct}/{100 - wPct}
        </span>
      </label>
      <div className={styles.slider}>
        <label htmlFor="ch4-rho" className={styles.sliderLabel}>
          pretend ρ
        </label>
        <input
          id="ch4-rho"
          type="range"
          min={-100}
          max={100}
          step={1}
          value={Math.round(rho * 100)}
          onChange={(e) => {
            tween.cancel();
            setPretend(Number(e.target.value) / 100);
          }}
          aria-valuetext={`Correlation ${signed(rho)}${pretend === null ? ", the real value" : ""}`}
        />
        <span className={styles.sliderValue}>
          {pretend === null ? (
            <>real {signed(rho)}</>
          ) : (
            <button
              type="button"
              className="pane-btn"
              onClick={() => {
                tween.run(rho, [{ to: realRho, ms: reduced ? 0 : 400 }], setPretend, () => setPretend(null));
              }}
              title={`Snap back to the real correlation, ${signed(realRho)}`}
            >
              {signed(rho)} ↺
            </button>
          )}
        </span>
      </div>
      <p className={styles.readout} aria-live="polite" style={{ marginTop: 6 }}>
        mix: return <strong>{pct(p.ret)}</strong> · volatility <strong>{pct(p.risk)}</strong>
        {saved > 0.0005 ? (
          <>
            {" "}
            · the bend saves <strong>{pct(saved)}</strong>
          </>
        ) : null}
      </p>
    </div>
  );

  return (
    <Pane title="two-stocks.svg" footer={footer} ariaLabel="two-stocks.svg: all the mixes of two stocks">
      <div className={styles.controls}>
        <label>
          A
          <select className="pane-select" value={a.ticker} onChange={(e) => choose(0, e.target.value)} aria-label="Stock A">
            {stats.tickers.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          B
          <select className="pane-select" value={b.ticker} onChange={(e) => choose(1, e.target.value)} aria-label="Stock B">
            {stats.tickers.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <span>
          real ρ <strong style={{ color: "var(--ink)" }}>{signed(realRho)}</strong>
        </span>
      </div>
      <TwoStocksChart step={step} a={a} b={b} w={w} rho={rho} />
    </Pane>
  );
}
