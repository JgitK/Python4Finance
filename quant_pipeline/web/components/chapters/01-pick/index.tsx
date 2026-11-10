"use client";

// Chapter 1: pick the winners.
// Pane: leaders.svg. Five steps change what the chart shows. The window
// control, the dots and the buttons work at every step.

import { useEffect, useRef, useState } from "react";
import { Chapter, Pane, Scrolly, Step } from "@/components/scrolly";
import { BASKET_MAX, BASKET_MIN, WINDOW_KEYS, useStore } from "@/lib/store";
import type { WindowKey } from "@/lib/types";
import { basketHint, pickForMe } from "./helpers";
import { LeadersChart } from "./LeadersChart";

const NO_DATA_REASON = "Needs 5 years of prices. The data starts in 2022.";

function WindowControl() {
  const { windowKey, setWindowKey, data } = useStore();
  const disabled = (k: WindowKey) => (data?.leaders[k]?.length ?? 1) === 0;
  const move = (dir: 1 | -1) => {
    let i = WINDOW_KEYS.indexOf(windowKey);
    for (let n = 0; n < WINDOW_KEYS.length; n++) {
      i = (i + dir + WINDOW_KEYS.length) % WINDOW_KEYS.length;
      if (!disabled(WINDOW_KEYS[i])) return setWindowKey(WINDOW_KEYS[i]);
    }
  };
  return (
    <div
      className="seg"
      role="radiogroup"
      aria-label="Ranking window"
      onKeyDown={(e) => {
        if (e.key === "ArrowRight" || e.key === "ArrowDown") (e.preventDefault(), move(1));
        if (e.key === "ArrowLeft" || e.key === "ArrowUp") (e.preventDefault(), move(-1));
      }}
    >
      {WINDOW_KEYS.map((k) => (
        <button
          key={k}
          type="button"
          role="radio"
          aria-checked={k === windowKey}
          aria-disabled={disabled(k) || undefined}
          tabIndex={k === windowKey ? 0 : -1}
          title={disabled(k) ? NO_DATA_REASON : undefined}
          className={`seg-btn${k === windowKey ? " on" : ""}`}
          style={disabled(k) ? { opacity: 0.4, cursor: "not-allowed", textDecoration: "line-through" } : undefined}
          onClick={() => !disabled(k) && setWindowKey(k)}
        >
          {k}
        </button>
      ))}
    </div>
  );
}

function PickPane({ step }: { step: number }) {
  const { leaders, windowKey, data, basket, setBasket, resetBasket, canAdd } = useStore();
  const [notice, setNotice] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);
  const say = (m: string) => {
    setNotice(m);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setNotice(null), 4000);
  };

  const info = data?.meta.windows.find((w) => w.key === windowKey);
  const empty = leaders.length === 0;
  const hint = basketHint(basket.length, BASKET_MIN, BASKET_MAX);
  const status = notice ?? hint;

  return (
    <Pane
      title="leaders.svg"
      controls={<WindowControl />}
      ariaLabel="leaders.svg: the top stocks of each sector"
      footer={
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 10px", alignItems: "center" }}>
          <button
            type="button"
            className="pane-btn"
            disabled={empty}
            onClick={() => setBasket(pickForMe(leaders, BASKET_MAX))}
            title="Fill the basket with the best stock of each sector"
          >
            Pick for me
          </button>
          <button type="button" className="pane-btn" onClick={resetBasket} title="Back to the starter basket">
            Reset
          </button>
          <span className="mono" aria-live="polite" style={{ fontSize: 11.5 }}>
            {basket.length} picked
            {status ? <span style={{ color: canAdd && !notice ? "var(--tan-deep)" : "var(--loss)" }}> · {status}</span> : null}
          </span>
        </div>
      }
    >
      {step >= 1 && info ? (
        <p className="mono" style={{ fontSize: 11.5, color: "var(--tan-deep)", margin: "0 0 4px", minHeight: 16 }}>
          {windowKey}: {info.label}. {info.effect}.
        </p>
      ) : (
        <p style={{ fontSize: 11.5, color: "var(--ink-soft)", margin: "0 0 4px", minHeight: 16 }} className="mono">
          Return over the window · top 5 of each sector
        </p>
      )}
      <LeadersChart step={step} leaders={leaders} sectors={data?.meta.sectors ?? []} onBlocked={say} />
      {empty && data ? (
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", padding: 24, pointerEvents: "none" }}>
          <p
            className="mono"
            style={{ margin: 0, maxWidth: 300, textAlign: "center", fontSize: 12.5, color: "var(--ink-soft)", background: "var(--paper)", border: "1px solid var(--pane-border)", borderRadius: 6, padding: "10px 14px", boxShadow: "3px 3px 6px var(--peach)" }}
          >
            No stocks for {windowKey}. {NO_DATA_REASON} Pick another window.
          </p>
        </div>
      ) : null}
    </Pane>
  );
}

export default function PickChapter() {
  return (
    <Chapter
      id="ch-01"
      number={1}
      title={<>Pick the <em>winners</em></>}
      intro="Every portfolio starts with a list of candidates. Here are the best stocks of each sector, by how much they went up."
    >
      <Scrolly pane={(active) => <PickPane step={active} />} paneLabel="Leaders chart">
        <Step>
          Start where most people start: with <em>what went up</em>. Each row is a sector. Each grey dot is one of its five
          best stocks, placed by its return.
        </Step>
        <Step label="Change the window">
          Pick a window (1M, 3M, 6M, 1Y, 2Y) and watch the dots slide. Each window measures a different effect. Over a month,
          winners tend to fall back. Over three months to a year, they tend to keep going. Over two years, they fall back
          again. 5Y is greyed out: the data starts in 2022.
        </Step>
        <Step label="Luck or skill?">
          A return of +18% over 3 months can be luck. The thin line is the range the true return probably sits in (95%).
          It is very wide. A line that runs off the chart ends in an arrow.
        </Step>
        <Step label="Your turn">
          Now pick. Click 6 to 12 stocks, spread across sectors. The bar on the right of each row counts your picks. Not
          sure? Press <em>Pick for me</em> for the best stock of each sector.
        </Step>
        <Step label="A steadier lead">
          A dashed ring marks a stock that stayed in its sector&apos;s top five on 3M, 6M and 1Y. Leading once is easy.
          Leading again and again is rarer, though still no promise.
        </Step>
      </Scrolly>
    </Chapter>
  );
}
