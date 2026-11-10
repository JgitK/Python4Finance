"use client";

/**
 * Tooltip: a small card at a point inside a chart box.
 *
 *   <div className="pane-fill" style={{ position: "relative" }}>
 *     <svg ... />
 *     <Tooltip x={hover?.x} y={hover?.y} visible={!!hover} containerWidth={width}>
 *       <strong>NVDA</strong> · Sharpe 1.42
 *     </Tooltip>
 *   </div>
 *
 * x and y are pixels in the container (the parent must be position:
 * relative). The card sits above the point and flips below it near the
 * top. It stays inside the container width. It does not take the pointer.
 */

import type { ReactNode } from "react";

export interface TooltipProps {
  x?: number;
  y?: number;
  visible: boolean;
  children: ReactNode;
  /** The container width, to keep the card inside. Default: no clamp. */
  containerWidth?: number;
  /** Approximate card width for the clamp. Default 180. */
  width?: number;
}

export function Tooltip({ x = 0, y = 0, visible, children, containerWidth, width = 180 }: TooltipProps) {
  const half = width / 2;
  const left = containerWidth ? Math.min(Math.max(x, half + 4), containerWidth - half - 4) : x;
  const below = y < 70;
  return (
    <div
      className="chart-tooltip"
      role="status"
      aria-hidden={!visible}
      style={{
        left,
        top: y,
        opacity: visible ? 1 : 0,
        transform: `translate(-50%, ${below ? "14px" : "calc(-100% - 14px)"})`,
        maxWidth: width + 60,
      }}
    >
      {children}
    </div>
  );
}
