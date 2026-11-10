"use client";

// Chapter 7: how much to trust this. One pane that changes with the step:
// error bars, the bootstrap scatter, the weight ranges, the scorecard, the
// gap with the per-window chart, and the four rules.

import { useEffect, useRef, useState } from "react";
import { Chapter, Pane, Scrolly, Step } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { BootstrapScatter, BootstrapWeights } from "./Bootstrap";
import { Closing, Rules } from "./Closing";
import { ErrorBars } from "./ErrorBars";
import { GapView } from "./Gap";
import { ScorecardView } from "./Scorecard";
import { useBootstrap } from "./useBootstrap";

const TITLES = ["error-bars.svg", "bootstrap.svg", "bootstrap.svg", "scorecard.svg", "scorecard.svg", "verdict.md"];

export default function TrustChapter() {
  const { stats, status } = useStore();
  // Start the bootstrap only when the reader nears the chapter.
  const sentinel = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    const el = sentinel.current;
    if (!el || near) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setNear(true);
      },
      { rootMargin: "1800px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [near]);

  const key = stats ? `${stats.tickers.join(",")}|${stats.aligned.rows.length}` : "";
  const boot = useBootstrap(stats?.aligned.rows ?? null, key, near && status === "ready");

  return (
    <Chapter
      id="ch-07"
      number={7}
      title={
        <>
          How much to <em>trust</em> this
        </>
      }
      intro="The honest part. Everything so far looked at the past. Here is what the method does when the future arrives."
    >
      <div ref={sentinel} aria-hidden="true" />
      <Scrolly
        paneLabel="How much to trust the result"
        pane={(step) => (
          <Pane title={TITLES[step] ?? TITLES[0]} ariaLabel={TITLES[step] ?? TITLES[0]}>
            {step <= 0 ? <ErrorBars /> : null}
            {step === 1 ? <BootstrapScatter boot={boot} /> : null}
            {step === 2 ? <BootstrapWeights boot={boot} /> : null}
            {step === 3 ? <ScorecardView /> : null}
            {step === 4 ? <GapView /> : null}
            {step >= 5 ? <Rules /> : null}
          </Pane>
        )}
      >
        <Step label="Guesses, not facts">
          The optimizer needs an expected return for every stock, and it takes the past average as the answer. But
          a few years of prices say little about the next year. Each dot is the guess, and each bar is the range
          where the truth could plausibly sit. The optimizer used the dots as facts. <em>They are guesses.</em>
        </Step>
        <Step label="The best mix moves">
          Imagine you could replay the same years 200 times, with the days shuffled a little. Each replay gives a
          slightly different history, so a slightly different &ldquo;best&rdquo; mix. If the answer were solid, the
          dots would sit on one spot. Look at how they scatter. <em>The best mix moves when the data moves.</em>
        </Step>
        <Step label="Weights wobble too">
          The same replays, stock by stock. A short bar means the weight is stable. A long bar means it depends on
          which days you happened to see. Treat a weight like &ldquo;31%&rdquo; as &ldquo;somewhere between a
          little and a lot&rdquo;.
        </Step>
        <Step label="The scorecard">
          Now the real test, from the project&rsquo;s own walk-forward run. Choose the mix on old data, hold it on
          new days, and repeat. The optimizer sits next to equal weight, SPY and a random order. This is shown
          even when it is not flattering.
        </Step>
        <Step label="Paper versus real life">
          On the data it was fitted to, the optimizer looked far better than it was on new data. That gap is the
          price of trusting the guesses. Below it, each bar is one test window: green plus when the portfolio beat
          SPY, red minus when it did not.
        </Step>
        <Step label="What to keep">
          Markowitz is a risk tool. Trust the covariance more than the return. Spread across sectors. Equal weight
          is hard to beat.
        </Step>
      </Scrolly>
      <Closing />
    </Chapter>
  );
}
