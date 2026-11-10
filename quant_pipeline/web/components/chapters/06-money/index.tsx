"use client";

// Chapter 6: put the money in. Weights become dollars, then whole shares.

import { Chapter, Scrolly, Step } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { dollars } from "@/lib/theme";
import { AllocationPane } from "./AllocationPane";

export default function MoneyChapter() {
  const { amount } = useStore();
  return (
    <Chapter
      id="ch-06"
      number={6}
      title={
        <>
          Put the <em>money</em> in
        </>
      }
      intro="A weight is a promise on paper. A broker wants dollars and whole shares. Here is the last mile."
    >
      <Scrolly pane={(step) => <AllocationPane step={step} />} paneLabel="Allocation of the money">
        <Step label="Weights">
          Start with the weights of the portfolio you chose. Each bar is one stock, coloured by its sector. The
          bars add up to 100%, like slices of one pie. Use the switch in the pane to try max Sharpe, min volatility
          or equal weight.
        </Step>
        <Step label="Dollars">
          Now the pie gets a price tag. Multiply each weight by your <strong>{dollars(amount)}</strong>, and the
          bars turn into dollars. Change the amount in the pane or in the tray, and every bar follows.
        </Step>
        <Step label="Shares">
          A broker sells shares, not dollars. Divide the dollars by the last price and you get a share count. A
          cheap stock gives many shares. A dear one gives few. The money is the same, so the bars change shape.
        </Step>
        <Step label="Whole or fractional">
          With <em>whole</em> shares you cannot buy 0.4 of a share. The leftover pennies stay as cash, and a stock
          whose single share costs more than its target <em>drops out</em>. Think of buying eggs by the dozen
          when you need only five. Tick &ldquo;fractional shares&rdquo; to buy any slice, and watch the cash and
          the drop-outs go away.
        </Step>
        <Step label="The table">
          The same plan as a table: ticker, sector, target weight, price, shares, cost and the weight you really
          got. Copy it as CSV and paste it into a spreadsheet. It is a plan, not an order: prices move before you
          trade.
        </Step>
      </Scrolly>
    </Chapter>
  );
}
