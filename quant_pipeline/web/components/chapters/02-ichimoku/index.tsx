"use client";

// Chapter 2: test the timing with Ichimoku.
// Pane: ichimoku.svg for one stock of the basket. Each step adds a layer.

import { useEffect, useState } from "react";
import { Chapter, Pane, Scrolly, Step } from "@/components/scrolly";
import { useIchimoku, useStore } from "@/lib/store";
import { COLORS } from "@/lib/theme";
import { CLOUD_DOWN, CLOUD_UP, IchimokuChart, SERIES } from "./IchimokuChart";
import { signalList } from "./helpers";

/** True under 640px wide: the pane is short there, so use short labels. */
function useCompact(): boolean {
  const [c, setC] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    const on = () => setC(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return c;
}

function Swatch({ color, dash, box }: { color: string; dash?: boolean; box?: boolean }) {
  return box ? (
    <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 2, background: color, opacity: 0.7, flexShrink: 0 }} />
  ) : (
    <svg width="18" height="8" aria-hidden="true" style={{ flexShrink: 0 }}>
      <line x1="0" y1="4" x2="18" y2="4" stroke={color} strokeWidth="2" strokeDasharray={dash ? "4 3" : undefined} />
    </svg>
  );
}

function Legend({ step }: { step: number }) {
  const item: React.CSSProperties = { display: "inline-flex", alignItems: "center", gap: 5 };
  return (
    <ul className="mono" aria-label="Legend" style={{ listStyle: "none", margin: "0 0 4px", padding: 0, display: "flex", flexWrap: "wrap", gap: "2px 12px", fontSize: 11, color: "var(--ink-soft)", minHeight: 16 }}>
      {SERIES.filter((s) => step >= s.minStep).map((s) => (
        <li key={s.key} style={item}>
          <Swatch color={s.color} dash={!!s.dash} />
          {s.label}
        </li>
      ))}
      {step >= 2 ? (
        <li style={item}>
          <Swatch color={CLOUD_UP} box />
          <Swatch color={CLOUD_DOWN} box />
          Cloud: rising / falling
        </li>
      ) : null}
    </ul>
  );
}

function IchimokuPane({ step }: { step: number }) {
  const { basket, removeTicker, canRemove } = useStore();
  const [pick, setPick] = useState<string | null>(null);
  const ticker = pick && basket.includes(pick) ? pick : basket[0];
  const { data, loading } = useIchimoku(ticker);
  const signals = data ? signalList(data.signals) : [];
  const compact = useCompact();
  const index = ticker ? basket.indexOf(ticker) : -1;

  const go = (d: 1 | -1) => {
    if (!basket.length) return;
    setPick(basket[(index + d + basket.length) % basket.length]);
  };
  const remove = () => {
    if (!ticker) return;
    // Show the next stock after the removed one.
    setPick(basket[(index + 1) % basket.length] === ticker ? null : basket[(index + 1) % basket.length]);
    removeTicker(ticker);
  };

  const footer =
    step >= 3 && data ? (
      <div style={{ display: "grid", gap: 6 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 8px", alignItems: "center" }}>
          <span className="mono" style={{ fontWeight: 700, color: "var(--ink)", fontSize: 12.5 }} aria-label={`Score ${data.score} out of 3`}>
            Score {data.score}/3
          </span>
          {signals.map((s) => (
            <span
              key={s.key}
              className="mono"
              title={s.label}
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 999,
                border: `1px solid ${s.on ? "var(--sage-deep)" : "var(--pane-border)"}`,
                background: s.on ? "var(--sage-deep)" : "var(--paper)",
                color: s.on ? "#fff" : "var(--ink-soft)",
              }}
            >
              {s.on ? "✓" : "✗"} {compact ? s.short : s.label}
            </span>
          ))}
        </div>
        {step >= 4 ? (
          <p style={{ margin: 0, fontSize: 11.5, color: "var(--tan-deep)", lineHeight: 1.35 }}>
            {compact
              ? "Honest note: in our tests (D24) an Ichimoku gate lowered the result. Timing info, not a filter."
              : "Honest note: in this project's tests, an Ichimoku gate lowered the result (D24). Use the chart for timing, not as a filter."}
          </p>
        ) : null}
      </div>
    ) : undefined;

  return (
    <Pane title="ichimoku.svg" ariaLabel="ichimoku.svg: the Ichimoku chart of one stock" footer={footer}>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start", flexShrink: 0 }}>
      {step >= 4 ? (
        <div style={{ display: "flex", gap: 4, alignItems: "center", paddingBottom: 6, flexShrink: 0 }}>
          <button type="button" className="pane-btn" onClick={() => go(-1)} aria-label="Previous stock">
            ←
          </button>
          <button type="button" className="pane-btn" onClick={() => go(1)} aria-label="Next stock">
            →
          </button>
          <button
            type="button"
            className="pane-btn"
            onClick={remove}
            disabled={!canRemove || !ticker}
            title={canRemove ? `Take ${ticker} out of the basket` : "A basket needs at least 2 stocks"}
          >
            {canRemove ? `Remove ${ticker}` : "2 is the minimum"}
          </button>
        </div>
      ) : null}
      <div role="tablist" aria-label="Stocks in your basket" style={{ display: "flex", gap: 4, overflowX: "auto", scrollbarWidth: "thin", paddingBottom: 6, flex: 1, minWidth: 0 }}>
        {basket.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={t === ticker}
            className={`chip-btn${t === ticker ? " on" : ""}`}
            onClick={() => setPick(t)}
            style={{ flexShrink: 0 }}
          >
            {t}
          </button>
        ))}
      </div>
      </div>
      <Legend step={step} />
      <IchimokuChart step={step} data={data} loading={loading} ticker={ticker} />
    </Pane>
  );
}

export default function IchimokuChapter() {
  return (
    <Chapter
      id="ch-02"
      number={2}
      title={<>Test the timing with <em>Ichimoku</em></>}
      intro="A stock can be a good pick and a bad moment to buy. Ichimoku is a Japanese chart that reads the trend in layers."
    >
      <Scrolly pane={(active) => <IchimokuPane step={active} />} paneLabel="Ichimoku chart">
        <Step>
          Here is one of your picks: its closing price for the last 12 months. Use the tabs to switch stocks. Hover the chart to read a day.
        </Step>
        <Step label="Two averages">
          Two lines join the price. The <strong>fast line</strong> averages the last 9 days. The <strong>slow line</strong>{" "}
          averages 26. Think of a sprinter and a hiker. Fast above slow: the trend is up.
        </Step>
        <Step label="The cloud">
          The cloud is drawn 26 days <em>ahead</em>, into the shaded part. It is a guess at support and resistance: a floor
          when the price is above it, a ceiling when below. Sage where it points up, clay where it points down.
        </Step>
        <Step label="The score">
          The lagging line is today&apos;s price, drawn 26 days back. It asks: is the price higher than a month ago? Add up
          three yes-or-no signals (price above the cloud, fast above slow, lagging above price) and you get a score from 0
          to 3.
        </Step>
        <Step label="Your turn">
          Step through your basket, and take out any stock you do not like. One honest note: in this project&apos;s tests,
          an Ichimoku gate <em>lowered</em> the result (D24). It is information for timing. It is not a filter.
        </Step>
      </Scrolly>
    </Chapter>
  );
}
