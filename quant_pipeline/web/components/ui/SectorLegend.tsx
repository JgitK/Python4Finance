"use client";

/**
 * SectorLegend: a swatch and a name for each sector.
 *
 *   <SectorLegend />                         // every sector of the data
 *   <SectorLegend only={stats.sectors} short />
 *   <SectorLegend onHover={setHoverSector} active={hoverSector} />
 */

import { useStore } from "@/lib/store";
import { sectorColor, sectorShort } from "@/lib/theme";

export interface SectorLegendProps {
  /** Show only these sectors (duplicates are fine). */
  only?: string[];
  /** Use the short names. */
  short?: boolean;
  /** Called with a sector on hover or focus, and null on leave. */
  onHover?: (sector: string | null) => void;
  /** A sector to highlight. The others fade. */
  active?: string | null;
  className?: string;
}

export function SectorLegend({ only, short = false, onHover, active = null, className }: SectorLegendProps) {
  const { data } = useStore();
  const all = data?.meta.sectors ?? [];
  const list = only ? all.filter((s) => only.includes(s)) : all;
  return (
    <ul className={`sector-legend${className ? ` ${className}` : ""}`} aria-label="Sectors">
      {list.map((s) => (
        <li
          key={s}
          className={active && active !== s ? "dim" : undefined}
          onMouseEnter={onHover ? () => onHover(s) : undefined}
          onMouseLeave={onHover ? () => onHover(null) : undefined}
          onFocus={onHover ? () => onHover(s) : undefined}
          onBlur={onHover ? () => onHover(null) : undefined}
          tabIndex={onHover ? 0 : undefined}
          title={s}
        >
          <span className="swatch" style={{ background: sectorColor(s, all) }} aria-hidden="true" />
          {short ? sectorShort(s) : s}
        </li>
      ))}
    </ul>
  );
}
