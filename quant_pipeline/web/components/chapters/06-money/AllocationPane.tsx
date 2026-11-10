"use client";

// The pane of chapter 6: allocation.csv. The step picks the view:
// 0 weights, 1 dollars, 2 shares, 3 whole or fractional, 4 the table.
// The reader can also change the unit by hand. A new step resets it.

import { useMemo, useState } from "react";
import { Pane } from "@/components/scrolly";
import { MoneyInput, SectorLegend } from "@/components/ui";
import { useStore, type PortfolioKey } from "@/lib/store";
import { dollars, pct } from "@/lib/theme";
import { buildMoneyPlan, type MoneyPlan, type Unit } from "./allocation";
import { Bars } from "./Bars";
import { AllocationTable } from "./Table";
import s from "./money.module.css";

const UNITS: { unit: Unit; label: string; short: string }[] = [
  { unit: "weights", label: "weights", short: "%" },
  { unit: "dollars", label: "dollars", short: "$" },
  { unit: "shares", label: "shares", short: "sh" },
];
const PORTFOLIOS: { key: PortfolioKey; label: string }[] = [
  { key: "maxSharpe", label: "max Sharpe" },
  { key: "minVol", label: "min volatility" },
  { key: "equal", label: "equal weight" },
];
const CAPTIONS: Record<Unit, string> = {
  weights: "Share of the money for each stock",
  dollars: "Dollars for each stock",
  shares: "Shares to buy, at the last price",
};

const unitOfStep = (step: number): Unit => (step <= 0 ? "weights" : step === 1 ? "dollars" : "shares");

function Summary({ plan, amount, fractional }: { plan: MoneyPlan; amount: number; fractional: boolean }) {
  return (
    <div className={s.summary}>
      <div>
        Spent <strong>{dollars(plan.spent, 2)}</strong> of {dollars(amount)}. Cash left over:{" "}
        <strong>{dollars(plan.cash, 2)}</strong>.
      </div>
      {fractional ? (
        <div>With fractional shares every stock gets its full target. Nothing drops out.</div>
      ) : (
        <>
          {plan.droppedRows.length > 0 ? (
            <ul aria-label="Stocks that drop out">
              {plan.droppedRows.map((r) => (
                <li key={r.ticker} className={s.drop}>
                  <b>{r.ticker} drops out.</b> One share costs {dollars(r.price, 2)}, but its target is only{" "}
                  {dollars(r.targetDollars, 2)} ({pct(r.weight)} of {dollars(amount)}).
                </li>
              ))}
            </ul>
          ) : (
            <div>Every stock gets at least one share.</div>
          )}
          <div>
            The smallest amount that holds every weight with whole shares: <strong>{dollars(plan.minimum)}</strong>.
          </div>
        </>
      )}
    </div>
  );
}

export function AllocationPane({ step }: { step: number }) {
  const {
    status,
    selected,
    selectedPortfolio,
    setSelectedPortfolio,
    amount,
    fractional,
    setFractional,
    stats,
    data,
  } = useStore();
  const [pick, setPick] = useState<{ step: number; unit: Unit } | null>(null);
  const unit = pick && pick.step === step ? pick.unit : unitOfStep(step);

  const plan = useMemo(() => {
    if (!selected || !stats) return null;
    const prices: Record<string, number> = {};
    const sectors: Record<string, string> = {};
    stats.tickers.forEach((t, i) => {
      prices[t] = stats.prices[i];
      sectors[t] = stats.sectors[i];
    });
    return buildMoneyPlan(selected.weightsByTicker, prices, sectors, amount, fractional);
  }, [selected, stats, amount, fractional]);

  const allSectors = data?.meta.sectors ?? [];
  const presentSectors = plan ? Array.from(new Set(plan.rows.map((r) => r.sector))) : [];
  const isCustom = typeof selectedPortfolio === "number";
  const table = step >= 4;

  const controls = table ? null : (
    <div className={s.group} role="group" aria-label="What the bars measure">
      {UNITS.map((u) => (
        <button
          key={u.unit}
          type="button"
          className={`chip-btn${unit === u.unit ? " on" : ""}`}
          aria-pressed={unit === u.unit}
          aria-label={u.label}
          title={u.label}
          onClick={() => setPick({ step, unit: u.unit })}
        >
          <span className={s.long}>{u.label}</span>
          <span className={s.short} aria-hidden="true">{u.short}</span>
        </button>
      ))}
    </div>
  );

  let body;
  if (status === "error") body = <p className={s.empty}>The data did not load, so there is nothing to allocate.</p>;
  else if (status === "loading") body = <p className={s.empty}>Loading the prices…</p>;
  else if (!plan || plan.rows.length === 0)
    body = <p className={s.empty}>Pick at least two stocks in chapter 1 and this table fills in.</p>;
  else if (table) body = <AllocationTable plan={plan} sectors={allSectors} />;
  else
    body = (
      <div className={s.chart} style={{ minHeight: plan.rows.length * 18 + 70 }}>
        <div className={s.caption}>{CAPTIONS[unit]}</div>
        <Bars plan={plan} unit={unit} fractional={fractional} sectors={allSectors} />
        <SectorLegend className={s.legend} only={presentSectors} short />
      </div>
    );

  return (
    <Pane
      title="allocation.csv"
      controls={controls}
      ariaLabel="allocation.csv: how to split the money"
    >
      <div className={s.scroller}>
      <div className={s.toolbar}>
        <div className={s.group} role="group" aria-label="Portfolio">
          {PORTFOLIOS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`chip-btn${selectedPortfolio === p.key ? " on" : ""}`}
              aria-pressed={selectedPortfolio === p.key}
              onClick={() => setSelectedPortfolio(p.key)}
            >
              {p.label}
            </button>
          ))}
          {isCustom ? (
            <button type="button" className="chip-btn on" aria-pressed="true" title="The dot that you picked in chapter 5">
              your dot
            </button>
          ) : null}
        </div>
        <MoneyInput className={s.money} label="Amount to invest" />
        <label className="pane-check">
          <input type="checkbox" checked={fractional} onChange={(e) => setFractional(e.target.checked)} />
          fractional shares
        </label>
      </div>
      {body}
      {plan && step >= 3 && !table ? <Summary plan={plan} amount={amount} fractional={fractional} /> : null}
      </div>
    </Pane>
  );
}
