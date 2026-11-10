"use client";

// correlation.csv: the lower triangle of the correlation (or covariance)
// matrix of the basket, ordered by sector, with the value in each cell.
//
// Steps (of the second Scrolly of chapter 4):
//   0  The cells draw in.
//   1  The most correlated pair gets a solid outline.
//   2  The least correlated pair gets a dashed outline.
//   3  (The pane switches the mode to covariance; the chart only follows `mode`.)
//
// The column labels sit on the diagonal, in the empty upper triangle.

import * as d3 from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import { useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { COLORS, DURATION, correlationScale, d3Ease, num, pct, sectorColor, textOn } from "@/lib/theme";
import { MONO, useDuration } from "../03-risk/kit";
import { monoWidth } from "../03-risk/labels";
import styles from "../03-risk/core.module.css";
import { cellText, type Pair } from "./math";

export interface HeatmapChartProps {
  step: number;
  mode: "corr" | "cov";
  tickers: string[];
  sectors: string[];
  allSectors?: string[];
  corr: number[][];
  /** The annual covariance. */
  cov: number[][];
  /** The largest absolute covariance off the diagonal: the colour domain. */
  covMax: number;
  vols: number[];
  max: Pair;
  min: Pair;
}

interface Cell {
  i: number;
  j: number;
  key: string;
}

export function HeatmapChart(props: HeatmapChartProps) {
  const { step, mode, tickers, sectors, allSectors, corr, cov, covMax, vols, max, min } = props;
  const [box, { width, height }] = useChartSize();
  const gRef = useRef<SVGGElement>(null);
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null);
  const dur = useDuration(DURATION.medium);
  const drawn = useRef(false);

  const geo = useMemo(() => {
    const n = tickers.length;
    if (width === 0 || height === 0 || n < 2) return null;
    const fsLabel = width < 480 ? 10 : 11;
    const labelW = Math.max(...tickers.map((t) => monoWidth(t, fsLabel))) + 10;
    const slant = labelW * 0.72 + 6;
    const left = labelW + 4;
    const avail = Math.min(width - left - slant, height - slant - 6);
    const cell = Math.max(8, Math.floor(avail / n));
    const gridW = cell * n;
    // Centre the grid and its labels in the box.
    const offX = Math.max(0, Math.floor((width - (left + gridW + slant)) / 2)) + left;
    const offY = Math.max(slant, Math.floor((height - gridW) / 2));
    return { n, cell, offX, offY, fsLabel };
  }, [tickers, width, height]);

  const color = useMemo(() => {
    const div = correlationScale();
    return (v: number) => (mode === "corr" ? div(v) : div(covMax > 0 ? v / covMax : 0));
  }, [mode, covMax]);

  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo) return;
    const { n, cell, fsLabel } = geo;
    const root = d3.select(g);
    const t = d3.transition().duration(dur).ease(d3Ease);
    const layer = (cls: string) => root.selectAll<SVGGElement, number>(`g.${cls}`).data([0]).join("g").attr("class", cls);
    const values = mode === "corr" ? corr : cov;
    const cells: Cell[] = [];
    for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) cells.push({ i, j, key: `${tickers[i]}|${tickers[j]}` });
    const fs = Math.min(11, Math.max(8, cell * 0.28));
    const first = !drawn.current;
    drawn.current = true;

    const fillOf = (d: Cell) => (d.i === d.j && mode === "corr" ? COLORS.lineSoft : color(values[d.i][d.j]));

    // The cells.
    const sel = layer("cells")
      .selectAll<SVGGElement, Cell>("g.cell")
      .data(cells, (d) => d.key)
      .join((enter) => {
        const e = enter
          .append("g")
          .attr("class", "cell")
          .attr("opacity", 0)
          .attr("transform", (d) => `translate(${d.j * cell},${d.i * cell})`);
        e.append("rect").attr("rx", 2);
        e.append("text").attr("text-anchor", "middle").style("font-family", MONO).style("font-variant-numeric", "tabular-nums");
        return e;
      });
    sel
      .on("pointerenter", (_, d) => setHover({ i: d.i, j: d.j }))
      .on("pointerleave", () => setHover(null));
    sel
      .select("rect")
      .attr("x", 1)
      .attr("y", 1)
      .attr("width", cell - 2)
      .attr("height", cell - 2)
      .transition(t)
      .attr("fill", fillOf);
    sel
      .select("text")
      .attr("x", cell / 2)
      .attr("y", cell / 2 + fs * 0.36)
      .style("font-size", `${fs}px`)
      .attr("fill", (d) => (d.i === d.j && mode === "corr" ? COLORS.inkSoft : textOn(fillOf(d))))
      .text((d) => (d.i === d.j && mode === "corr" ? (cell >= 18 ? "1" : "") : cellText(values[d.i][d.j], mode, cell)));
    sel
      .interrupt()
      .transition(t)
      .delay((d) => (first && dur > 0 ? (d.i + d.j) * 22 : 0))
      .attr("opacity", 1)
      .attr("transform", (d) => `translate(${d.j * cell},${d.i * cell})`);

    // The row labels with a sector bar, and the column labels on the diagonal.
    const isPairTicker = (k: number) =>
      (step >= 1 && (k === max.i || k === max.j)) || (step >= 2 && (k === min.i || k === min.j));
    const rows = layer("rows")
      .selectAll<SVGGElement, string>("g")
      .data(tickers, (d) => d)
      .join((enter) => {
        const e = enter.append("g");
        e.append("rect").attr("width", 4).attr("rx", 1);
        e.append("text").attr("text-anchor", "end").style("font-family", MONO);
        return e;
      })
      .attr("transform", (_, i) => `translate(0,${i * cell})`);
    rows
      .select("rect")
      .attr("x", -8)
      .attr("y", 2)
      .attr("height", cell - 4)
      .attr("fill", (_, i) => sectorColor(sectors[i], allSectors));
    rows
      .select("text")
      .attr("x", -12)
      .attr("y", cell / 2 + fsLabel * 0.36)
      .style("font-size", `${fsLabel}px`)
      .style("font-weight", (_, i) => (isPairTicker(i) ? 700 : 400))
      .attr("fill", (_, i) => (isPairTicker(i) ? COLORS.ink : COLORS.inkSoft))
      .text((d) => d);
    layer("cols")
      .selectAll<SVGTextElement, string>("text")
      .data(tickers, (d) => d)
      .join("text")
      .style("font-family", MONO)
      .style("font-size", `${fsLabel}px`)
      .style("font-weight", (_, i) => (isPairTicker(i) ? 700 : 400))
      .attr("fill", (_, i) => (isPairTicker(i) ? COLORS.ink : COLORS.inkSoft))
      .attr("transform", (_, i) => `translate(${i * cell + cell / 2 + 2},${i * cell - 4}) rotate(-45)`)
      .text((d) => d);

    // The outlines of the two pairs.
    const outlines = [
      { key: "max", p: max, on: step >= 1, dash: null as string | null },
      { key: "min", p: min, on: step >= 2, dash: "4 3" },
    ];
    layer("outlines")
      .attr("pointer-events", "none")
      .selectAll<SVGRectElement, (typeof outlines)[number]>("rect")
      .data(outlines, (d) => d.key)
      .join("rect")
      .attr("x", (d) => d.p.j * cell - 1)
      .attr("y", (d) => d.p.i * cell - 1)
      .attr("width", cell + 2)
      .attr("height", cell + 2)
      .attr("rx", 3)
      .attr("fill", "none")
      .attr("stroke", COLORS.ink)
      .attr("stroke-width", 2.5)
      .attr("stroke-dasharray", (d) => d.dash)
      .interrupt()
      .transition(t)
      .attr("opacity", (d) => (d.on ? 1 : 0));
  }, [geo, step, mode, tickers, sectors, allSectors, corr, cov, color, max, min, dur]);

  // The hover ring: no transition.
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo) return;
    const { cell } = geo;
    d3.select(g)
      .selectAll<SVGRectElement, { i: number; j: number }>("rect.hover")
      .data(hover ? [hover] : [])
      .join("rect")
      .attr("class", "hover")
      .attr("pointer-events", "none")
      .attr("x", (d) => d.j * cell)
      .attr("y", (d) => d.i * cell)
      .attr("width", cell)
      .attr("height", cell)
      .attr("rx", 2)
      .attr("fill", "none")
      .attr("stroke", COLORS.sageDeep)
      .attr("stroke-width", 2);
  }, [hover, geo]);

  const h = hover && geo ? hover : null;
  return (
    <div ref={box} className={styles.fill} onPointerLeave={() => setHover(null)}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`A ${mode === "corr" ? "correlation" : "covariance"} heatmap of ${tickers.length} stocks, ordered by sector. The most correlated pair is ${tickers[max.i]} and ${tickers[max.j]} at ${num(max.value)}. The least correlated pair is ${tickers[min.i]} and ${tickers[min.j]} at ${num(min.value)}.`}
      >
        {geo ? <g ref={gRef} transform={`translate(${geo.offX},${geo.offY})`} /> : null}
      </svg>
      {geo ? (
        <Tooltip
          x={h ? geo.offX + h.j * geo.cell + geo.cell / 2 : 0}
          y={h ? geo.offY + h.i * geo.cell : 0}
          visible={!!h}
          containerWidth={width}
          width={210}
        >
          {h ? (
            <>
              <strong>
                {tickers[h.i]} × {tickers[h.j]}
              </strong>
              <br />
              ρ {num(corr[h.i][h.j])} · cov {num(cov[h.i][h.j], 4)}
              <br />
              <span style={{ color: "var(--ink-soft)" }}>
                = {num(corr[h.i][h.j])} × {pct(vols[h.i])} × {pct(vols[h.j])}
              </span>
            </>
          ) : null}
        </Tooltip>
      ) : null}
    </div>
  );
}
