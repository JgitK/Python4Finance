"use client";

// Small parts that chapters 3, 4 and 5 share: the axis style, the motion
// duration, and the message that a pane shows while the data loads.

import type * as d3 from "d3";
import { usePrefersReducedMotion } from "@/components/scrolly";
import { useStore } from "@/lib/store";
import { COLORS } from "@/lib/theme";
import styles from "./core.module.css";

/** The mono font stack for SVG text. */
export const MONO = "var(--font-mono), ui-monospace, Menlo, monospace";

/** Make a D3 axis quiet: hairline domain and ticks, soft mono labels. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function styleAxis(g: d3.Selection<SVGGElement, any, any, any>, fontSize = 10.5): void {
  g.select(".domain").attr("stroke", COLORS.grid);
  g.selectAll(".tick line").attr("stroke", COLORS.grid);
  g.selectAll(".tick text").attr("fill", COLORS.inkSoft).style("font-family", MONO).style("font-size", `${fontSize}px`);
}

/** The transition time in ms, or 0 when the reader asks for reduced motion. */
export function useDuration(ms: number): number {
  const reduced = usePrefersReducedMotion();
  return reduced ? 0 : ms;
}

/**
 * The state of the basket data for a chart. Returns a node to show in
 * place of the chart, or null when the stats are ready.
 */
export function usePaneGate(): React.ReactNode | null {
  const { status, error, stats } = useStore();
  if (status === "loading") return <p className={styles.message}>Loading the prices…</p>;
  if (status === "error") return <p className={styles.message}>The data did not load: {error}</p>;
  if (!stats) return <p className={styles.message}>Put at least two stocks with a price history in the basket.</p>;
  return null;
}

/** The plot margins for a chart width. Narrow charts get tighter margins. */
export function margins(width: number): { top: number; right: number; bottom: number; left: number } {
  return width < 480 ? { top: 24, right: 12, bottom: 34, left: 40 } : { top: 28, right: 20, bottom: 40, left: 50 };
}
