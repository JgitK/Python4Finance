"use client";

/**
 * TickerChip: a ticker with its sector colour dot, and an optional remove button.
 *
 *   <TickerChip ticker="NVDA" />
 *   <TickerChip ticker="NVDA" onRemove={() => removeTicker("NVDA")} removeDisabled={!canRemove} />
 */

import { useStore } from "@/lib/store";
import { sectorColor } from "@/lib/theme";

export interface TickerChipProps {
  ticker: string;
  onRemove?: () => void;
  removeDisabled?: boolean;
  className?: string;
}

export function TickerChip({ ticker, onRemove, removeDisabled, className }: TickerChipProps) {
  const { sectorOf, data } = useStore();
  const sector = sectorOf(ticker) ?? "";
  return (
    <span className={`ticker-chip${className ? ` ${className}` : ""}`} title={sector}>
      <span className="dot" style={{ background: sectorColor(sector, data?.meta.sectors) }} aria-hidden="true" />
      <span className="sym">{ticker}</span>
      {onRemove ? (
        <button
          type="button"
          className="chip-x"
          onClick={onRemove}
          disabled={removeDisabled}
          aria-label={`Remove ${ticker} from the basket`}
          title={removeDisabled ? "A basket needs at least 2 stocks" : `Remove ${ticker}`}
        >
          ×
        </button>
      ) : null}
    </span>
  );
}
