"use client";

/**
 * MoneyInput: the amount of money to invest, in US dollars.
 *
 *   <MoneyInput />                   // the store amount, compact
 *   <MoneyInput variant="hero" />    // the large input of chapter 0, with presets
 *
 * The reader types freely. The value goes to the store on blur, on Enter,
 * or on a preset click. The store clamps it to $100 … $10,000,000.
 */

import { useId, useState } from "react";
import { AMOUNT_MAX, AMOUNT_MIN, useStore } from "@/lib/store";

const PRESETS = [1_000, 10_000, 50_000, 250_000];

const fmt = (x: number) => x.toLocaleString("en-US", { maximumFractionDigits: 2 });
const parse = (s: string) => Number(s.replace(/[^0-9.]/g, ""));

export interface MoneyInputProps {
  variant?: "hero" | "compact";
  label?: string;
  className?: string;
}

export function MoneyInput({ variant = "compact", label = "Amount to invest", className }: MoneyInputProps) {
  const { amount, setAmount } = useStore();
  const id = useId();
  const [draft, setDraft] = useState<string | null>(null);
  const shown = draft ?? fmt(amount);

  const commit = () => {
    if (draft === null) return;
    const v = parse(draft);
    if (Number.isFinite(v) && v > 0) setAmount(v);
    setDraft(null);
  };

  const parsed = draft === null ? amount : parse(draft);
  const outOfRange = draft !== null && Number.isFinite(parsed) && (parsed < AMOUNT_MIN || parsed > AMOUNT_MAX);

  return (
    <div className={`money-input ${variant}${className ? ` ${className}` : ""}`}>
      <label htmlFor={id} className={variant === "hero" ? "eyebrow" : "sr-only"}>
        {label}
      </label>
      <div className="money-field">
        <span className="money-sign" aria-hidden="true">
          $
        </span>
        <input
          id={id}
          inputMode="decimal"
          autoComplete="off"
          spellCheck={false}
          value={shown}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              commit();
              (e.target as HTMLInputElement).blur();
            }
            if (e.key === "Escape") setDraft(null);
          }}
          aria-describedby={variant === "hero" ? `${id}-hint` : undefined}
        />
      </div>
      {variant === "hero" ? (
        <>
          <div className="money-presets" role="group" aria-label="Quick amounts">
            {PRESETS.map((p) => (
              <button
                key={p}
                type="button"
                className={`chip-btn${amount === p && draft === null ? " on" : ""}`}
                onClick={() => {
                  setDraft(null);
                  setAmount(p);
                }}
              >
                ${p >= 1000 ? `${p / 1000}k` : p}
              </button>
            ))}
          </div>
          <p id={`${id}-hint`} className={`money-hint${outOfRange ? " warn" : ""}`}>
            {outOfRange
              ? `Pick an amount from $${fmt(AMOUNT_MIN)} to $${fmt(AMOUNT_MAX)}.`
              : "Pretend money. You can change it at any time in the tray at the bottom."}
          </p>
        </>
      ) : null}
    </div>
  );
}
