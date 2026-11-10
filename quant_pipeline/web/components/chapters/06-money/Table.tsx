"use client";

// The table of step 5 and the "copy as CSV" button.

import { useRef, useState } from "react";
import s from "./money.module.css";
import { dollars, pct, sectorColor, sectorShort, sharesFmt } from "@/lib/theme";
import { toCsv, type MoneyPlan } from "./allocation";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for a page without clipboard permission.
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch {
      return false;
    }
  }
}

export function AllocationTable({ plan, sectors }: { plan: MoneyPlan; sectors: readonly string[] }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copy = async () => {
    const ok = await copyText(toCsv(plan));
    setState(ok ? "copied" : "failed");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setState("idle"), 2200);
  };

  const totalWeight = plan.rows.reduce((s, r) => s + r.weight, 0);
  const totalActual = plan.rows.reduce((s, r) => s + r.actualWeight, 0);

  return (
    <div className={s.tableWrap}>
      <div className={s.tableBar}>
        <button type="button" className="pane-btn" onClick={copy}>
          Copy as CSV
        </button>
        <span className={s.status} role="status" aria-live="polite">
          {state === "copied" ? "Copied. Paste it into a spreadsheet." : state === "failed" ? "Your browser blocked the copy." : ""}
        </span>
      </div>
      <div className={s.scroll} tabIndex={0} role="region" aria-label="Allocation table, scrolls sideways on a small screen">
        <table className={s.table}>
          <thead>
            <tr>
              <th scope="col">Ticker</th>
              <th scope="col">Sector</th>
              <th scope="col" className={s.r}>Weight</th>
              <th scope="col" className={s.r}>Price</th>
              <th scope="col" className={s.r}>Shares</th>
              <th scope="col" className={s.r}>Cost</th>
              <th scope="col" className={s.r}>Actual</th>
            </tr>
          </thead>
          <tbody>
            {plan.rows.map((r) => (
              <tr key={r.ticker}>
                <th scope="row">{r.ticker}</th>
                <td>
                  <span className={s.swatch} style={{ background: sectorColor(r.sector, sectors) }} aria-hidden="true" />
                  {sectorShort(r.sector)}
                </td>
                <td className={s.r}>{pct(r.weight)}</td>
                <td className={s.r}>{dollars(r.price, 2)}</td>
                <td className={s.r}>
                  {sharesFmt(r.shares)}
                  {r.dropped ? <span className="loss"> ✕</span> : null}
                </td>
                <td className={s.r}>{dollars(r.cost, 2)}</td>
                <td className={s.r}>{pct(r.actualWeight)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>Total</th>
              <td className={s.r}>{pct(totalWeight)}</td>
              <td />
              <td />
              <td className={s.r}>{dollars(plan.spent, 2)}</td>
              <td className={s.r}>{pct(totalActual)}</td>
            </tr>
            <tr>
              <th scope="row" colSpan={5}>Cash left</th>
              <td className={s.r}>{dollars(plan.cash, 2)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
