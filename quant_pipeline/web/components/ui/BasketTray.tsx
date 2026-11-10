"use client";

/**
 * BasketTray: the sticky tray at the bottom of the viewport. It holds the
 * basket (ticker chips by sector colour, each with a remove button), the
 * window picker and the amount. It shows from chapter 1 to the end: it
 * hides while the opening (#ch-00) is on screen.
 *
 * On a phone the tray is one summary row. A button opens the chips and
 * the controls.
 */

import { useEffect, useState } from "react";
import { BASKET_MAX, BASKET_MIN, useStore } from "@/lib/store";
import { dollars } from "@/lib/theme";
import { MoneyInput } from "./MoneyInput";
import { TickerChip } from "./TickerChip";
import { WindowPicker } from "./WindowPicker";

export function BasketTray() {
  const { basket, removeTicker, canRemove, resetBasket, windowKey, amount, status } = useStore();
  const [shown, setShown] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const opening = document.getElementById("ch-00");
    if (!opening) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(([e]) => setShown(!e.isIntersecting), { threshold: 0, rootMargin: "0px 0px -35% 0px" });
    io.observe(opening);
    return () => io.disconnect();
  }, []);

  if (status !== "ready") return null;

  return (
    <aside
      className={`basket-tray${shown ? " shown" : ""}${open ? " open" : ""}`}
      aria-label="Your basket"
      aria-hidden={!shown}
      inert={!shown}
    >
      <div className="tray-inner da-container">
        <div className="tray-summary">
          <span className="eyebrow tray-title">
            <span className="pixel-check" />
            Basket
          </span>
          <span className="tray-count" aria-live="polite">
            {basket.length}/{BASKET_MAX}
          </span>
          <span className="tray-mini">
            {windowKey} · {dollars(amount)}
          </span>
          <button
            type="button"
            className="tray-toggle"
            aria-expanded={open}
            aria-controls="tray-body"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? "Close" : "Edit"}
          </button>
        </div>
        <div id="tray-body" className="tray-body">
          <ul className="tray-chips" aria-label="Tickers in the basket">
            {basket.map((t) => (
              <li key={t}>
                <TickerChip ticker={t} onRemove={() => removeTicker(t)} removeDisabled={!canRemove} />
              </li>
            ))}
          </ul>
          <div className="tray-controls">
            <WindowPicker size="sm" />
            <MoneyInput variant="compact" />
            <button type="button" className="tray-reset" onClick={resetBasket} title="Go back to the default basket">
              Reset
            </button>
          </div>
        </div>
        {basket.length <= BASKET_MIN ? <span className="sr-only">The basket has the minimum of {BASKET_MIN} stocks.</span> : null}
      </div>
    </aside>
  );
}
