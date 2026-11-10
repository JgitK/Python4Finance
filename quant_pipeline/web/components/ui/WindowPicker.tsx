"use client";

/**
 * WindowPicker: a segmented radio group for the ranking window.
 *
 *   <WindowPicker />                 // reads and sets the store window
 *   <WindowPicker size="sm" showLabel />
 *
 * Arrow keys move the choice, as in a native radio group.
 * A window with no ranked stock is disabled. The data can be too short
 * for a long window.
 */

import { useRef, type KeyboardEvent } from "react";
import { useStore, WINDOW_KEYS } from "@/lib/store";
import type { WindowKey } from "@/lib/types";

export interface WindowPickerProps {
  /** "sm" for the tray. Default "md". */
  size?: "sm" | "md";
  /** Show the effect label of the window (such as "Momentum") after the buttons. */
  showLabel?: boolean;
  /** Override the store: a controlled value. */
  value?: WindowKey;
  onChange?: (key: WindowKey) => void;
  className?: string;
}

export function WindowPicker({ size = "md", showLabel = false, value, onChange, className }: WindowPickerProps) {
  const store = useStore();
  const current = value ?? store.windowKey;
  const set = onChange ?? store.setWindowKey;
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const info = store.data?.meta.windows.find((w) => w.key === current);

  const leaders = store.data?.leaders;
  const isEmpty = (k: WindowKey) => (leaders ? (leaders[k]?.length ?? 0) === 0 : false);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = WINDOW_KEYS.indexOf(current);
    const n = WINDOW_KEYS.length;
    let dir = 0;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") dir = 1;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") dir = -1;
    else return;
    e.preventDefault();
    // Skip each disabled window.
    let j = i;
    for (let step = 0; step < n; step++) {
      j = (j + dir + n) % n;
      if (!isEmpty(WINDOW_KEYS[j])) break;
    }
    if (j === i || isEmpty(WINDOW_KEYS[j])) return;
    set(WINDOW_KEYS[j]);
    refs.current[j]?.focus();
  };

  return (
    <div className={`window-picker ${size}${className ? ` ${className}` : ""}`}>
      <div role="radiogroup" aria-label="Ranking window" className="seg" onKeyDown={onKey}>
        {WINDOW_KEYS.map((k, i) => (
          <button
            key={k}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={k === current}
            tabIndex={k === current ? 0 : -1}
            className={`seg-btn${k === current ? " on" : ""}`}
            disabled={isEmpty(k)}
            title={isEmpty(k) ? "The price data is too short for this window." : undefined}
            style={isEmpty(k) ? { opacity: 0.4, cursor: "not-allowed", textDecoration: "line-through" } : undefined}
            onClick={() => set(k)}
          >
            {k}
          </button>
        ))}
      </div>
      {showLabel && info ? (
        <span className="window-label" aria-live="polite">
          {info.label}
        </span>
      ) : null}
    </div>
  );
}
