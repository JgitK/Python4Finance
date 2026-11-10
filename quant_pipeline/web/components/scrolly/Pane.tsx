"use client";

/**
 * Pane: the `.win` card that holds a chart.
 *
 *   <Pane title="correlation.csv" controls={<Toggle />} footer={<p>Mean ρ 0.31</p>}>
 *     <Heatmap />
 *   </Pane>
 *
 * Props:
 * - `title`: the file name in the title bar, such as "frontier.svg".
 * - `controls?`: a node in the title bar, right of the title (buttons, tabs).
 * - `footer?`: a node under the body (a readout, a legend, a note).
 * - `children`: the body. The body is a flex column that fills the pane
 *   height, so give the chart box `flex: 1` (class "pane-fill") and
 *   measure it with useChartSize().
 * - `bodyClassName?`, `className?`, `ariaLabel?`.
 */

import type { ReactNode } from "react";

export interface PaneProps {
  title: string;
  controls?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
  ariaLabel?: string;
}

export function Pane({ title, controls, footer, children, className, bodyClassName, ariaLabel }: PaneProps) {
  return (
    <div className={`win pane${className ? ` ${className}` : ""}`} role="figure" aria-label={ariaLabel ?? title}>
      <div className="titlebar">
        <span className="close-box" aria-hidden="true" />
        <span className="title-text">{title}</span>
        <div className="controls">
          {controls ? <div className="pane-controls">{controls}</div> : null}
          <span className="zoom-box" aria-hidden="true" />
        </div>
      </div>
      <div className={`pane-body${bodyClassName ? ` ${bodyClassName}` : ""}`}>{children}</div>
      {footer ? <div className="pane-footer">{footer}</div> : null}
    </div>
  );
}
