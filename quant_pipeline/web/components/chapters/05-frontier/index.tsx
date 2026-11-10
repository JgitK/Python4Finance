"use client";

// Chapter 5: ten thousand portfolios. The pane is frontier.canvas.

import { Chapter, Scrolly, Step } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { FrontierPane } from "./FrontierPane";

export default function FrontierChapter() {
  const { stats } = useStore();
  const n = stats?.tickers.length ?? 0;
  return (
    <Chapter
      id="ch-05"
      number={5}
      title={
        <>
          Ten thousand <em>portfolios</em>
        </>
      }
      intro="Two stocks make one curve. A whole basket makes a cloud. We find its edge by throwing darts."
    >
      <Scrolly paneLabel="Monte Carlo portfolio cloud" pane={(step) => <FrontierPane step={step} />}>
        <Step label="The stocks">
          <p>
            Back to the map of chapter 3: your {n || ""} stocks, each one alone. Every dot is a portfolio with
            100% of the money in one stock.
          </p>
        </Step>
        <Step label="One dart">
          <p>
            Now give each stock a <em>random</em> share of the money, and plot the mix. One dart lands. Its
            weights are on the right.
          </p>
          <p>One dart tells us little. Is it a good mix? We can only say once we see the others.</p>
        </Step>
        <Step label="Ten thousand darts">
          <p>
            Throw 10, then 100, then <strong>10,000</strong>. Each dot is one random mix. Darker green means a
            better Sharpe ratio: more return for each unit of bumpiness, after the return of cash.
          </p>
          <p>Hover a dot to see its weights.</p>
        </Step>
        <Step label="The edge">
          <p>
            The cloud has a hard upper-left edge: the <em>efficient frontier</em>. No mix is above this line.
            Below it, you pay risk for nothing, because a mix on the line gives more return for the same risk.
          </p>
        </Step>
        <Step label="Three answers">
          <p>Three portfolios stand out:</p>
          <p>
            ▲ <strong>minimum volatility</strong>, the calmest mix. ★ <strong>maximum Sharpe</strong>, the best
            return for each unit of risk. ■ <strong>equal weight</strong>, the same share in each stock.
          </p>
          <p>
            The dashed line from cash through the star is the <em>capital market line</em>. Click a marker, a
            button, or any dot to see its weights. The next chapter puts your money into that pick.
          </p>
        </Step>
        <Step label="Your turn">
          <p>
            Edit the basket in the tray at the bottom. The cloud rains in again for the new stocks. The darts use
            a fixed seed (42), so the same basket always gives the same cloud.
          </p>
        </Step>
      </Scrolly>
    </Chapter>
  );
}
