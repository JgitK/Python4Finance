"use client";

// Chapter 4: how they move together. Two Scrolly blocks in one chapter:
// first two-stocks.svg (steps 1-3 of the plan), then correlation.csv
// (steps 4-7 of the plan).

import { Chapter, Scrolly, Step } from "@/components/scrolly";
import { HeatmapPane } from "./HeatmapPane";
import { TwoStocksPane } from "./TwoStocksPane";

export default function TogetherChapter() {
  return (
    <Chapter
      id="ch-04"
      number={4}
      title={
        <>
          How they move <em>together</em>
        </>
      }
      intro="A mix is not just the average of its parts. What matters is whether the parts rise and fall at the same time."
    >
      <Scrolly paneLabel="Two-stock mix chart" pane={(step) => <TwoStocksPane step={step} />}>
        <Step label="Two stocks">
          <p>
            Take two stocks from your basket. Put all of the money in the first one, <strong>A</strong>. The
            ringed dot, your mix, sits right on top of it.
          </p>
          <p>Use the two menus to try any pair. We start with the pair that moves least alike.</p>
        </Step>
        <Step label="The bend">
          <p>
            Now move money from A to B with the weight slider. You might expect the dot to slide along the
            straight dashed line. It does not. It follows a <em>curve</em> that bends to the left: less
            bumpiness for the same return.
          </p>
          <p>
            <strong>The bend is free.</strong> It is often called the only free lunch in finance. When one stock
            has a bad day, the other often does not, and the bumps partly cancel.
          </p>
        </Step>
        <Step label="Pretend">
          <p>
            How much bend you get depends on one number: the <em>correlation</em>, ρ. It runs from +1 (the two
            move in lockstep) to −1 (one goes up exactly when the other goes down).
          </p>
          <p>
            Turn the pretend ρ dial. At +1 the curve is the straight line: no free lunch. Lower values bend it
            more, and at −1 it touches zero risk. Then press ↺ to snap back to the real ρ of the pair.
          </p>
        </Step>
      </Scrolly>

      <Scrolly paneLabel="Correlation heatmap" pane={(step) => <HeatmapPane step={step} />}>
        <Step label="Every pair at once">
          <p>
            Two stocks are one pair. Your basket has many pairs, so here they all are in one table, grouped by
            sector. Each cell is the ρ of a pair.
          </p>
          <p>
            <em>Clay</em> means the two move together. <em>Sage</em> means they move apart. Pale means they
            mostly ignore each other.
          </p>
        </Step>
        <Step label="Twins">
          <p>
            The outlined cell is your <strong>most correlated pair</strong>. These two are close to one stock in
            two coats. Holding both adds less safety than you think.
          </p>
        </Step>
        <Step label="Opposites">
          <p>
            The second outline is your <strong>least correlated pair</strong>. This pair is where most of the
            diversification comes from.
          </p>
          <p>The marker on the colour bar shows the mean ρ of the basket. Lower is better for a mix.</p>
        </Step>
        <Step label="Covariance">
          <p>
            The optimizer in the next chapter uses one more number, the <em>covariance</em>. In one sentence: the
            covariance is the correlation times the two volatilities.
          </p>
          <p>
            So a pair of calm stocks has a small covariance even when they move alike. Use the toggle to switch
            the table between ρ and covariance.
          </p>
        </Step>
      </Scrolly>
    </Chapter>
  );
}
