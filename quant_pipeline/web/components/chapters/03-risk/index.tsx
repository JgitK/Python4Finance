"use client";

// Chapter 3: one stock is a bumpy ride. The pane is risk-return.svg.

import { Chapter, Pane, Scrolly, Step } from "@/components/scrolly";
import { SectorLegend } from "@/components/ui";
import { useStore } from "@/lib/store";
import { RiskReturnChart } from "./RiskReturnChart";
import styles from "./core.module.css";

function Footer() {
  const { stats } = useStore();
  if (!stats) return null;
  return (
    <div className={styles.footRow}>
      <span className={styles.wideOnly}>
        <SectorLegend only={stats.sectors} short />
      </span>
      {stats.benchmark ? (
        <span className={styles.key}>
          <span className={styles.dot} style={{ background: "var(--stone)" }} aria-hidden="true" />
          SPY (the whole market)
        </span>
      ) : null}
    </div>
  );
}

export default function RiskChapter() {
  return (
    <Chapter
      id="ch-03"
      number={3}
      title={
        <>
          One stock is a <em>bumpy</em> ride
        </>
      }
      intro="Every stock has two numbers that matter here: how much it paid a year, and how much it shook on the way."
    >
      <Scrolly
        paneLabel="Risk and return chart"
        pane={(step) => (
          <Pane title="risk-return.svg" footer={<Footer />} ariaLabel="risk-return.svg: return and volatility of each basket stock">
            <RiskReturnChart step={step} />
          </Pane>
        )}
      >
        <Step label="The pay">
          <p>
            Here are your picks, stacked by one number: the <em>return</em>, what each stock paid a year on
            average. Higher is better. If this were the whole story, you would buy the top one and stop.
          </p>
        </Step>
        <Step label="The price">
          <p>
            Now open the second axis. <strong>Return is the pay. Volatility is the price.</strong> Volatility
            measures how hard a stock shakes from day to day. The dots slide right by how bumpy the ride was.
          </p>
          <p>The grey dot is SPY, the whole market in one fund: a handy yardstick.</p>
        </Step>
        <Step label="Feel the bumps">
          <p>
            Hover a dot (or press Tab to reach one) to see its daily returns. Each tick is one day: green up,
            red down. A stock far to the right has tall ticks both ways. That is what a high volatility feels
            like from the inside.
          </p>
        </Step>
        <Step label="The wish">
          <p>
            Can we get the pay of the top dot for the price of the leftmost dot? <strong>Not with one stock.</strong>{" "}
            No single pick lives in that corner.
          </p>
          <p>With a mix of stocks, sometimes we can get closer. The next chapter shows why.</p>
        </Step>
      </Scrolly>
    </Chapter>
  );
}
