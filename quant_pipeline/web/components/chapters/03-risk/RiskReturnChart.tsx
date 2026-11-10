"use client";

// risk-return.svg: one labelled dot for each basket stock, and SPY in stone.
//
// Steps:
//   0  The x axis is closed. The dots sit on one vertical line by return.
//   1  The x axis opens. The dots move right by their volatility.
//   2  Hover (or focus) a dot to see its daily returns. With no hover, the
//      most volatile stock shows its card.
//   3  "The wish": dashed lines from the top payer and the calmest stock
//      meet at a corner that no single stock reaches.
//
// React makes the <svg> and the tooltip. D3 draws only inside the <g>.

import * as d3 from "d3";
import { useEffect, useMemo, useRef, useState } from "react";
import { useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { useStore } from "@/lib/store";
import { COLORS, DURATION, NEUTRAL, d3Ease, pct, sectorColor } from "@/lib/theme";
import { MONO, margins, styleAxis, useDuration, usePaneGate } from "./kit";
import { monoWidth, placeLabels, type LabelPlace } from "./labels";
import { SparkCard } from "./SparkCard";
import styles from "./core.module.css";

export interface RiskPoint {
  ticker: string;
  sector: string;
  ret: number;
  vol: number;
  bench: boolean;
  color: string;
}

interface Layout {
  pos: { x: number; y: number }[];
  labels: LabelPlace[];
}

/** The basket stocks and SPY as points. */
export function useRiskPoints(): RiskPoint[] {
  const { stats, data } = useStore();
  return useMemo(() => {
    if (!stats) return [];
    const sectors = data?.meta.sectors;
    const pts: RiskPoint[] = stats.tickers.map((t, i) => ({
      ticker: t,
      sector: stats.sectors[i],
      ret: stats.annualReturn[i],
      vol: stats.annualVol[i],
      bench: false,
      color: sectorColor(stats.sectors[i], sectors),
    }));
    if (stats.benchmark) {
      pts.push({
        ticker: stats.benchmark.ticker,
        sector: "The S&P 500 index fund",
        ret: stats.benchmark.annualReturn,
        vol: stats.benchmark.annualVol,
        bench: true,
        color: NEUTRAL,
      });
    }
    return pts;
  }, [stats, data]);
}

/** The daily returns of each point, on the aligned dates of the basket. */
function useDaily(): Map<string, number[]> {
  const { stats, data } = useStore();
  return useMemo(() => {
    const m = new Map<string, number[]>();
    if (!stats) return m;
    stats.tickers.forEach((t, i) => m.set(t, stats.aligned.rows.map((r) => r[i])));
    const bench = stats.benchmark?.ticker;
    const series = bench ? data?.returns.series[bench] : undefined;
    if (bench && series && data) {
      const at = new Map(data.returns.dates.map((d, i) => [d, i]));
      m.set(
        bench,
        stats.aligned.dates.map((d) => {
          const k = at.get(d);
          const v = k === undefined ? null : series[k];
          return v ?? NaN;
        }),
      );
    }
    return m;
  }, [stats, data]);
}

export function RiskReturnChart({ step }: { step: number }) {
  const gate = usePaneGate();
  const points = useRiskPoints();
  const daily = useDaily();
  const [box, { width, height }] = useChartSize();
  const gRef = useRef<SVGGElement>(null);
  const [hover, setHover] = useState<string | null>(null);
  const lastTip = useRef<{ x: number; y: number; card: RiskPoint } | null>(null);
  const dur = useDuration(DURATION.long);

  const geo = useMemo(() => {
    if (!points.length || width === 0 || height === 0) return null;
    const m = margins(width);
    const iw = Math.max(10, width - m.left - m.right);
    const ih = Math.max(10, height - m.top - m.bottom);
    const fs = width < 480 ? 10 : 11;
    const maxVol = d3.max(points, (p) => p.vol) ?? 0.5;
    const x = d3.scaleLinear().domain([0, maxVol * 1.08]).nice().range([0, iw]);
    const lo = d3.min(points, (p) => p.ret) ?? 0;
    const hi = d3.max(points, (p) => p.ret) ?? 0.2;
    const pad = (hi - lo) * 0.08 || 0.05;
    const y = d3.scaleLinear().domain([Math.min(0, lo - pad), hi + pad]).nice().range([ih, 0]);
    // Label the stocks with the most return first: they are the story.
    const order = d3.range(points.length).sort((a, b) => points[b].ret - points[a].ret);
    const layout = (open: boolean): Layout => {
      const pos = points.map((p) => ({ x: open ? x(p.vol) : iw * 0.38, y: y(p.ret) }));
      const placed = placeLabels(
        order.map((i) => ({ x: pos[i].x, y: pos[i].y, w: monoWidth(points[i].ticker, fs) })),
        { width: iw, height: ih, h: fs + 3, r: 8 },
      );
      const labels: LabelPlace[] = new Array(points.length);
      order.forEach((i, k) => (labels[i] = placed[k]));
      return { pos, labels };
    };
    return { m, iw, ih, fs, x, y, closed: layout(false), open: layout(true) };
  }, [points, width, height]);

  // The card shows on hover. At step 2 the most volatile stock shows when nothing is hovered.
  const defaultKey = useMemo(() => {
    const stocks = points.filter((p) => !p.bench);
    return stocks.length ? stocks.reduce((a, b) => (b.vol > a.vol ? b : a)).ticker : null;
  }, [points]);
  const shown = hover ?? (step === 2 ? defaultKey : null);
  const shownIdx = points.findIndex((p) => p.ticker === shown);

  // ── Draw ──
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo) return;
    const { iw, ih, fs, x, y } = geo;
    const open = step >= 1;
    const L = open ? geo.open : geo.closed;
    const root = d3.select(g);
    const t = d3.transition().duration(dur).ease(d3Ease);

    const layer = (cls: string) =>
      root
        .selectAll<SVGGElement, number>(`g.${cls}`)
        .data([0])
        .join("g")
        .attr("class", cls);

    // The hit area for the pointer: under all marks.
    layer("hit")
      .selectAll("rect")
      .data([0])
      .join("rect")
      .attr("width", iw)
      .attr("height", ih)
      .attr("fill", "transparent");

    // The y grid and axis.
    const yAxis = layer("y-axis");
    yAxis
      .call(
        d3
          .axisLeft(y)
          .ticks(Math.max(3, Math.round(ih / 60)))
          .tickFormat((d) => pct(+d, 0))
          .tickSize(-iw)
          .tickPadding(6),
      )
      .call((s) => styleAxis(s, fs))
      .call((s) => s.select(".domain").remove());
    yAxis
      .selectAll<SVGTextElement, number>("text.title")
      .data([0])
      .join("text")
      .attr("class", "title")
      .attr("x", -geo.m.left + 2)
      .attr("y", -12)
      .attr("text-anchor", "start")
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text("↑ return a year");

    // The zero line, when a stock lost money.
    layer("zero")
      .selectAll("line")
      .data(y.domain()[0] < 0 ? [0] : [])
      .join("line")
      .attr("x1", 0)
      .attr("x2", iw)
      .attr("y1", y(0))
      .attr("y2", y(0))
      .attr("stroke", COLORS.stone)
      .attr("stroke-width", 1);

    // The x axis: closed at step 0.
    const xAxis = layer("x-axis").attr("transform", `translate(0,${ih})`);
    xAxis
      .call(
        d3
          .axisBottom(x)
          .ticks(Math.max(3, Math.round(iw / 90)))
          .tickFormat((d) => pct(+d, 0)),
      )
      .call((s) => styleAxis(s, fs));
    xAxis.interrupt().transition(t).attr("opacity", open ? 1 : 0);
    const xTitle = layer("x-title").attr("transform", `translate(${iw},${ih + geo.m.bottom - 6})`);
    xTitle
      .selectAll<SVGTextElement, number>("text")
      .data([0])
      .join("text")
      .attr("text-anchor", "end")
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text(open ? "volatility a year (the bumpiness) →" : "volatility: not shown yet");

    // The wish (step 3).
    const stocks = points.map((p, i) => ({ p, i })).filter((d) => !d.p.bench);
    const top = stocks.reduce((a, b) => (b.p.ret > a.p.ret ? b : a), stocks[0]);
    const calm = stocks.reduce((a, b) => (b.p.vol < a.p.vol ? b : a), stocks[0]);
    const wishOn = step >= 3 && top && calm && top.i !== calm.i;
    const wish = layer("wish");
    if (top && calm) {
      const cx = x(calm.p.vol);
      const cy = y(top.p.ret);
      wish
        .selectAll("rect")
        .data([0])
        .join("rect")
        .attr("x", 0)
        .attr("y", cy)
        .attr("width", Math.max(0, cx))
        .attr("height", Math.max(0, ih - cy))
        .attr("fill", COLORS.sage)
        .attr("fill-opacity", 0.08);
      wish
        .selectAll<SVGPathElement, number>("path")
        .data([0])
        .join("path")
        .attr("d", `M${x(top.p.vol)},${cy}H${cx}V${y(calm.p.ret)}`)
        .attr("fill", "none")
        .attr("stroke", COLORS.sageDeep)
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "4 4");
      wish
        .selectAll("circle")
        .data([0])
        .join("circle")
        .attr("cx", cx)
        .attr("cy", cy)
        .attr("r", 8)
        .attr("fill", COLORS.paper)
        .attr("stroke", COLORS.sageDeep)
        .attr("stroke-width", 2);
      const below = cy < 30;
      wish
        .selectAll<SVGTextElement, number>("text")
        .data([0])
        .join("text")
        .attr("x", Math.max(cx, 4))
        .attr("y", below ? cy + 24 : cy - 14)
        .attr("text-anchor", cx < 120 ? "start" : "middle")
        .attr("fill", COLORS.ink)
        .style("font-family", MONO)
        .style("font-size", `${fs}px`)
        .style("font-weight", 600)
        .text("the wish: top pay, low bumps");
    }
    wish.interrupt().transition(t).attr("opacity", wishOn ? 1 : 0);

    // The dots. A <g> for each, so a keyboard can focus it.
    const posOf = (d: RiskPoint) => L.pos[points.indexOf(d)];
    const dots = layer("dots")
      .selectAll<SVGGElement, RiskPoint>("g.dot")
      .data(points, (d) => d.ticker)
      .join((enter) => {
        const e = enter
          .append("g")
          .attr("class", "dot")
          .attr("tabindex", 0)
          .attr("role", "img")
          .attr("transform", (d) => `translate(${posOf(d).x},${posOf(d).y})`)
          .style("cursor", "pointer")
          .style("outline", "none");
        e.append("circle").attr("class", "focus-ring").attr("r", 11).attr("fill", "none").attr("stroke", COLORS.sageDeep).attr("stroke-width", 2).attr("opacity", 0);
        e.append("circle").attr("class", "mark").attr("r", 6).attr("stroke", COLORS.paper).attr("stroke-width", 2);
        return e;
      });
    dots
      .attr("aria-label", (d) => `${d.ticker}, ${d.sector}: return ${pct(d.ret)} a year, volatility ${pct(d.vol)}`)
      .on("focus", (_, d) => setHover(d.ticker))
      .on("blur", () => setHover(null));
    dots.select("circle.mark").attr("fill", (d) => d.color);
    dots.interrupt().transition(t).attr("transform", (d) => `translate(${posOf(d).x},${posOf(d).y})`);

    // The ticker labels.
    const labels = layer("labels")
      .attr("pointer-events", "none")
      .selectAll<SVGTextElement, RiskPoint>("text")
      .data(points, (d) => d.ticker)
      .join((enter) =>
        enter
          .append("text")
          .attr("x", (d) => L.labels[points.indexOf(d)].x)
          .attr("y", (d) => L.labels[points.indexOf(d)].y + fs),
      );
    labels
      .text((d) => d.ticker)
      .attr("fill", (d) => (d.bench ? COLORS.inkSoft : COLORS.ink))
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .style("font-weight", (d) => (d.bench ? 400 : 600))
      .style("paint-order", "stroke")
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 3)
      .attr("stroke-linejoin", "round");
    labels
      .interrupt()
      .transition(t)
      .attr("x", (d) => L.labels[points.indexOf(d)].x)
      .attr("y", (d) => L.labels[points.indexOf(d)].y + fs);

    // The pointer: the nearest dot within 28 px.
    const pick = (event: PointerEvent) => {
      const [px, py] = d3.pointer(event, g);
      let best = -1;
      let bestD = 28 * 28;
      L.pos.forEach((q, i) => {
        const dd = (q.x - px) ** 2 + (q.y - py) ** 2;
        if (dd < bestD) {
          bestD = dd;
          best = i;
        }
      });
      setHover(best >= 0 ? points[best].ticker : null);
    };
    root.on("pointermove", pick).on("pointerdown", pick).on("pointerleave", () => setHover(null));
  }, [geo, step, points, dur]);

  // The highlight of the shown dot. No transition: it follows the pointer.
  useEffect(() => {
    const g = gRef.current;
    if (!g) return;
    const dots = d3.select(g).selectAll<SVGGElement, RiskPoint>("g.dot");
    dots.select("circle.focus-ring").attr("opacity", (d) => (d.ticker === shown ? 1 : 0));
    dots.select("circle.mark").attr("r", (d) => (d.ticker === shown ? 7.5 : 6));
    d3.select(g)
      .selectAll<SVGTextElement, RiskPoint>("g.labels text")
      .attr("opacity", (d) => (shown && d.ticker !== shown ? 0.45 : 1));
  }, [shown, geo, step, points]);

  if (gate) return <div className={styles.fill} style={{ display: "flex" }}>{gate}</div>;

  const card = shownIdx >= 0 && geo ? points[shownIdx] : null;
  const L = geo ? (step >= 1 ? geo.open : geo.closed) : null;
  // Keep the last place while the card fades out, so it does not jump to the corner.
  if (card && L && geo) lastTip.current = { x: L.pos[shownIdx].x + geo.m.left, y: L.pos[shownIdx].y + geo.m.top, card };
  const tip = lastTip.current;

  return (
    <div ref={box} className={styles.fill}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`A scatter of risk against return for ${points.length} holdings. Up is more return a year. Right is more volatility.${step === 0 ? " The volatility axis is closed: the dots sit on one line by return." : ""}`}
      >
        {geo ? <g ref={gRef} transform={`translate(${geo.m.left},${geo.m.top})`} /> : null}
      </svg>
      <Tooltip x={tip?.x} y={tip?.y} visible={!!card} containerWidth={width} width={216}>
        {tip ? <SparkCard point={tip.card} values={daily.get(tip.card.ticker) ?? []} /> : null}
      </Tooltip>
    </div>
  );
}
