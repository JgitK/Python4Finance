"use client";

// frontier.canvas: the Monte Carlo cloud on a <canvas>, with an <svg> on
// top for the axes, the stocks, the efficient frontier, the markers, the
// capital market line and the hover ring.
//
// Steps:
//   0  Only the basket stocks, as in chapter 3.
//   1  One random portfolio (#1 of the cloud) drops in.
//   2  The cloud rains in: 10, then 100, then all 10,000 dots (about 2 s).
//   3  The efficient frontier draws along the upper-left edge.
//   4+ The three markers and the capital market line. A click on a marker
//      or a dot selects that portfolio (the store keeps it for chapter 6).
//
// A new basket gives a new cloud: it rains in again. A resize redraws the
// dots that show, with no rain.

import * as d3 from "d3";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useChartSize, usePrefersReducedMotion } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import type { MonteCarloResult } from "@/lib/portfolio";
import { useStore, type PortfolioKey } from "@/lib/store";
import { COLORS, DURATION, d3Ease, pct, sectorColor, sharpeFmt, sharpeInterpolator } from "@/lib/theme";
import { MONO, margins, styleAxis } from "../03-risk/kit";
import { monoWidth, placeLabels } from "../03-risk/labels";
import styles from "../03-risk/core.module.css";
import { buildGrid, capitalMarketLine, nearestPoint, rainCount, robustDomain, type PointGrid } from "./cloud";

const BINS = 24;

interface MarkerDatum {
  key: PortfolioKey;
  label: string;
  symbol: d3.SymbolType;
  risk: number;
  ret: number;
  sharpe: number;
}

export interface FrontierChartProps {
  step: number;
  /** The cloud index under the pointer, or -1. */
  hover: number;
  onHover: (k: number) => void;
}

export function FrontierChart({ step, hover, onHover }: FrontierChartProps) {
  const { stats, data, mc, frontier, portfolios, selectedPortfolio, setSelectedPortfolio, riskFree } = useStore();
  const [box, { width, height }] = useChartSize();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const reduced = usePrefersReducedMotion();
  const dur = reduced ? 0 : DURATION.long;
  const [dpr, setDpr] = useState(1);
  const [count, setCount] = useState(0);
  const countRef = useRef(0);
  const mcSeen = useRef<MonteCarloResult | null>(null);
  const gridRef = useRef<{ grid: PointGrid; count: number; key: unknown } | null>(null);
  const frontierOn = useRef(false);
  const randomOn = useRef(false);
  const lastHover = useRef(-1);

  useEffect(() => {
    const on = () => setDpr(window.devicePixelRatio || 1);
    on();
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);

  const stocks = useMemo(() => {
    if (!stats) return [];
    return stats.tickers.map((t, i) => ({
      ticker: t,
      ret: stats.annualReturn[i],
      vol: stats.annualVol[i],
      color: sectorColor(stats.sectors[i], data?.meta.sectors),
    }));
  }, [stats, data]);

  const geo = useMemo(() => {
    if (!stocks.length || width === 0 || height === 0) return null;
    const m = margins(width);
    const iw = Math.max(10, width - m.left - m.right);
    const ih = Math.max(10, height - m.top - m.bottom);
    const fs = width < 480 ? 10 : 11;
    const maxVol = d3.max(stocks, (s) => s.vol) ?? 0.5;
    const x = d3.scaleLinear().domain([0, maxVol * 1.08]).nice().range([0, iw]);
    const lo = Math.min(0, riskFree, d3.min(stocks, (s) => s.ret) ?? 0);
    const hi = d3.max(stocks, (s) => s.ret) ?? 0.2;
    const pad = (hi - lo) * 0.06 || 0.05;
    const y = d3.scaleLinear().domain([lo - pad, hi + pad]).nice().range([ih, 0]);
    return { m, iw, ih, fs, x, y };
  }, [stocks, width, height, riskFree]);

  // The pixel place of each portfolio.
  const pix = useMemo(() => {
    if (!mc || !geo) return null;
    const xs = new Float32Array(mc.n);
    const ys = new Float32Array(mc.n);
    for (let k = 0; k < mc.n; k++) {
      xs[k] = geo.x(mc.risk[k]);
      ys[k] = geo.y(mc.ret[k]);
    }
    return { xs, ys };
  }, [mc, geo]);

  // The colour bins: one list of indices (in order) for each Sharpe colour.
  const bins = useMemo(() => {
    if (!mc) return null;
    const [lo, hi] = robustDomain(mc.sharpe);
    const colors = d3.range(BINS).map((b) => sharpeInterpolator((b + 0.5) / BINS));
    const lists: number[][] = colors.map(() => []);
    for (let k = 0; k < mc.n; k++) {
      const s = mc.sharpe[k];
      const b = Number.isFinite(s) ? Math.min(BINS - 1, Math.max(0, Math.floor(((s - lo) / (hi - lo)) * BINS))) : 0;
      lists[b].push(k);
    }
    return { colors, lists, domain: [lo, hi] as [number, number] };
  }, [mc]);

  // ── Canvas ──
  const draw = useCallback(
    (c: number) => {
      const cv = canvasRef.current;
      if (!cv || !geo || !pix || !bins) return;
      const ctx = cv.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      if (c <= 0) return;
      ctx.save();
      ctx.translate(geo.m.left, geo.m.top);
      ctx.globalAlpha = 0.8;
      const r = width < 480 ? 1.4 : 1.8;
      const { xs, ys } = pix;
      // Low Sharpe first, so the best dots paint on top.
      bins.lists.forEach((list, b) => {
        ctx.fillStyle = bins.colors[b];
        ctx.beginPath();
        for (const k of list) {
          if (k >= c) break;
          ctx.moveTo(xs[k] + r, ys[k]);
          ctx.arc(xs[k], ys[k], r, 0, Math.PI * 2);
        }
        ctx.fill();
      });
      ctx.restore();
    },
    [geo, pix, bins, dpr, width, height],
  );

  // The rain. It runs when the step needs the cloud and the cloud is not
  // all there. A new cloud (a basket edit) starts from zero.
  useEffect(() => {
    if (!mc || !geo || !pix) return;
    if (mcSeen.current !== mc) {
      mcSeen.current = mc;
      countRef.current = 0;
    }
    const n = mc.n;
    const target = step >= 2 ? n : 0;
    const set = (c: number) => {
      countRef.current = c;
      setCount(c);
      draw(c);
    };
    if (target === 0 || reduced || countRef.current >= target) {
      set(target === 0 ? 0 : target);
      return;
    }
    const from = countRef.current;
    const full = from === 0;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = now - start;
      const c = full ? rainCount(t, n) : Math.round(from + (n - from) * Math.min(1, t / 500));
      set(c);
      if (c < n) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [step, mc, geo, pix, reduced, draw]);

  const markers = useMemo<MarkerDatum[]>(() => {
    if (!portfolios) return [];
    const mk = (key: PortfolioKey, label: string, symbol: d3.SymbolType): MarkerDatum => ({
      key,
      label,
      symbol,
      risk: portfolios[key].performance.annualVol,
      ret: portfolios[key].performance.annualReturn,
      sharpe: portfolios[key].performance.sharpe,
    });
    return [
      mk("maxSharpe", "max Sharpe", d3.symbolStar),
      mk("minVol", "min volatility", d3.symbolTriangle),
      mk("equal", "equal weight", d3.symbolSquare),
    ];
  }, [portfolios]);

  // ── SVG overlay ──
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo || !mc) return;
    const { iw, ih, fs, x, y } = geo;
    const root = d3.select(g);
    const t = d3.transition().duration(dur).ease(d3Ease);
    const layer = (cls: string) => root.selectAll<SVGGElement, number>(`g.${cls}`).data([0]).join("g").attr("class", cls);

    layer("hit")
      .selectAll("rect")
      .data([0])
      .join("rect")
      .attr("width", iw)
      .attr("height", ih)
      .attr("fill", "transparent");

    layer("y-axis")
      .call(d3.axisLeft(y).ticks(Math.max(3, Math.round(ih / 60))).tickFormat((d) => pct(+d, 0)).tickSize(-iw).tickPadding(6))
      .call((s) => styleAxis(s, fs))
      .call((s) => s.select(".domain").remove())
      .selectAll(".tick line")
      .attr("stroke-opacity", 0.7);
    layer("x-axis")
      .attr("transform", `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.round(iw / 90))).tickFormat((d) => pct(+d, 0)))
      .call((s) => styleAxis(s, fs));
    layer("titles")
      .selectAll<SVGTextElement, { t: string; x: number; y: number; a: string }>("text")
      .data([
        { t: "↑ return a year", x: -geo.m.left + 2, y: -12, a: "start" },
        { t: "volatility →", x: iw, y: ih + geo.m.bottom - 6, a: "end" },
      ])
      .join("text")
      .attr("x", (d) => d.x)
      .attr("y", (d) => d.y)
      .attr("text-anchor", (d) => d.a)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text((d) => d.t);

    // The capital market line (step 4+).
    const ms = portfolios?.maxSharpe.performance;
    const cml = layer("cml").attr("pointer-events", "none");
    if (ms) {
      const yMax = y.domain()[1];
      const xMax = x.domain()[1];
      const slope = ms.annualVol > 0 ? (ms.annualReturn - riskFree) / ms.annualVol : 0;
      const xEnd = slope > 0 ? Math.min(xMax, (yMax - riskFree) / slope) : xMax;
      const [p0, p1] = capitalMarketLine(riskFree, ms.annualVol, ms.annualReturn, xEnd);
      cml
        .selectAll("line")
        .data([0])
        .join("line")
        .attr("x1", x(p0.risk))
        .attr("y1", y(p0.ret))
        .attr("x2", x(p1.risk))
        .attr("y2", y(p1.ret))
        .attr("stroke", COLORS.tanDeep)
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "6 4");
      cml
        .selectAll("circle")
        .data([0])
        .join("circle")
        .attr("cx", x(0))
        .attr("cy", y(riskFree))
        .attr("r", 4)
        .attr("fill", COLORS.tanDeep);
      cml
        .selectAll<SVGTextElement, { t: string; x: number; y: number; a: string }>("text")
        .data([
          { t: `cash ${pct(riskFree)}`, x: x(0) + 7, y: y(riskFree) + 14, a: "start" },
          { t: "capital market line", x: x(p1.risk) - 4, y: y(p1.ret) + 14, a: "end" },
        ])
        .join("text")
        .attr("x", (d) => d.x)
        .attr("y", (d) => d.y)
        .attr("text-anchor", (d) => d.a)
        .attr("fill", COLORS.tanDeep)
        .style("font-family", MONO)
        .style("font-size", `${fs}px`)
        .style("paint-order", "stroke")
        .attr("stroke", COLORS.paper)
        .attr("stroke-width", 3)
        .text((d) => d.t);
    }
    cml.interrupt().transition(t).attr("opacity", step >= 4 ? 1 : 0);

    // The efficient frontier (step 3+). It draws in from left to right.
    const fl = layer("frontier").attr("pointer-events", "none");
    const path = fl
      .selectAll<SVGPathElement, number>("path")
      .data([0])
      .join("path")
      .attr("fill", "none")
      .attr("stroke", COLORS.ink)
      .attr("stroke-width", 2)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round")
      .attr(
        "d",
        d3
          .line<{ risk: number; ret: number }>()
          .x((d) => x(d.risk))
          .y((d) => y(d.ret))(frontier) ?? "",
      );
    const fOn = step >= 3 && frontier.length > 1;
    const node = path.node();
    path.interrupt();
    if (fOn && !frontierOn.current && node && dur > 0) {
      const len = node.getTotalLength();
      path
        .attr("opacity", 1)
        .attr("stroke-dasharray", `${len} ${len}`)
        .attr("stroke-dashoffset", len)
        .transition(t)
        .duration(dur * 1.6)
        .attr("stroke-dashoffset", 0)
        .on("end", function () {
          d3.select(this).attr("stroke-dasharray", null);
        });
    } else if (fOn) {
      path.attr("stroke-dasharray", null).attr("stroke-dashoffset", null).attr("opacity", 1);
    } else {
      path.transition(t).attr("opacity", 0);
    }
    frontierOn.current = fOn;
    const last = frontier[frontier.length - 1];
    fl.selectAll<SVGTextElement, number>("text")
      .data(frontier.length > 1 ? [0] : [])
      .join("text")
      .attr("x", last ? Math.min(x(last.risk) + 8, iw) : 0)
      .attr("y", last ? y(last.ret) + 4 : 0)
      .attr("text-anchor", last && x(last.risk) > iw - 80 ? "end" : "start")
      .attr("dy", last && x(last.risk) > iw - 80 ? -10 : 0)
      .attr("fill", COLORS.ink)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .style("font-weight", 600)
      .style("paint-order", "stroke")
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 3)
      .text("efficient frontier")
      .interrupt()
      .transition(t)
      .attr("opacity", fOn ? 1 : 0);

    // The basket stocks with their labels.
    // One placement for the marker labels and the stock labels, so they do
    // not touch. The markers go first: they are the story of step 4.
    const pos = stocks.map((s) => ({ x: x(s.vol), y: y(s.ret) }));
    const mpos = markers.map((d) => ({ x: x(d.risk), y: y(d.ret) }));
    const placed = placeLabels(
      [
        ...mpos.map((p, i) => ({ ...p, w: monoWidth(markers[i].label, fs) })),
        ...pos.map((p, i) => ({ ...p, w: monoWidth(stocks[i].ticker, fs) })),
      ],
      { width: iw, height: ih, h: fs + 3, r: 10 },
    );
    const mlab = placed.slice(0, markers.length);
    const labels = placed.slice(markers.length);
    const sg = layer("stocks").attr("pointer-events", "none");
    sg.selectAll<SVGCircleElement, (typeof stocks)[number]>("circle")
      .data(stocks, (d) => d.ticker)
      .join("circle")
      .attr("r", 5)
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 2)
      .attr("fill", (d) => d.color)
      .attr("cx", (_, i) => pos[i].x)
      .attr("cy", (_, i) => pos[i].y);
    sg.selectAll<SVGTextElement, (typeof stocks)[number]>("text")
      .data(stocks, (d) => d.ticker)
      .join("text")
      .attr("x", (_, i) => labels[i].x)
      .attr("y", (_, i) => labels[i].y + fs)
      .attr("fill", COLORS.ink)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .style("font-weight", 600)
      .style("paint-order", "stroke")
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 3)
      .text((d) => d.ticker);

    // Portfolio #1 drops in at step 1.
    const k0 = { x: x(mc.risk[0]), y: y(mc.ret[0]) };
    const rg = layer("random").attr("pointer-events", "none");
    const rOn = step === 1;
    const rdot = rg
      .selectAll<SVGGElement, number>("g")
      .data([0])
      .join((enter) => {
        const e = enter.append("g").attr("opacity", 0);
        e.append("circle").attr("r", 7).attr("fill", COLORS.sageDeep).attr("stroke", COLORS.paper).attr("stroke-width", 2);
        e.append("text").attr("y", -12).attr("text-anchor", "middle").style("font-family", MONO).attr("fill", COLORS.ink);
        return e;
      });
    rdot.select("text").style("font-size", `${fs}px`).style("paint-order", "stroke").attr("stroke", COLORS.paper).attr("stroke-width", 3).text("one random mix");
    rdot.interrupt();
    if (rOn && !randomOn.current && dur > 0) {
      rdot
        .attr("transform", `translate(${k0.x},${-20})`)
        .attr("opacity", 1)
        .transition(t)
        .duration(dur * 1.4)
        .ease(d3.easeBounceOut)
        .attr("transform", `translate(${k0.x},${k0.y})`);
    } else {
      rdot.attr("transform", `translate(${k0.x},${k0.y})`).transition(t).attr("opacity", rOn ? 1 : 0);
    }
    randomOn.current = rOn;

    // The three markers (step 4+). Each one is a button.
    const mOn = step >= 4;
    const mg = layer("markers").attr("pointer-events", mOn ? null : "none");
    const mk = mg
      .selectAll<SVGGElement, MarkerDatum>("g.marker")
      .data(markers, (d) => d.key)
      .join((enter) => {
        const e = enter.append("g").attr("class", "marker").attr("role", "button").style("cursor", "pointer").style("outline", "none");
        e.append("circle").attr("class", "hit").attr("r", 14).attr("fill", "transparent");
        e.append("circle").attr("class", "focus-ring").attr("r", 13).attr("fill", "none").attr("stroke", COLORS.sageDeep).attr("stroke-width", 2).attr("opacity", 0);
        e.append("path").attr("class", "shape").attr("stroke", COLORS.ink).attr("stroke-width", 2);
        e.append("text").style("font-family", MONO).style("font-weight", 600).attr("fill", COLORS.ink).style("paint-order", "stroke").attr("stroke", COLORS.paper).attr("stroke-width", 3);
        return e;
      });
    mk.attr("tabindex", mOn ? 0 : -1)
      .attr("aria-label", (d) => `${d.label} portfolio: return ${pct(d.ret)}, volatility ${pct(d.risk)}, Sharpe ${sharpeFmt(d.sharpe)}. Press to see its weights.`)
      .attr("transform", (_, i) => `translate(${mpos[i].x},${mpos[i].y})`)
      .on("click", (event: MouseEvent, d) => {
        event.stopPropagation();
        setSelectedPortfolio(d.key);
      })
      .on("keydown", (event: KeyboardEvent, d) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          setSelectedPortfolio(d.key);
        }
      })
      .on("focus", function () {
        d3.select(this).select(".focus-ring").attr("opacity", 1);
      })
      .on("blur", function () {
        d3.select(this).select(".focus-ring").attr("opacity", 0);
      });
    mk.select("path.shape").attr("d", (d) => d3.symbol(d.symbol, d.key === "maxSharpe" ? 190 : 120)());
    mk.select("text")
      .style("font-size", `${fs}px`)
      .attr("x", (_, i) => mlab[i].x - mpos[i].x)
      .attr("y", (_, i) => mlab[i].y - mpos[i].y + fs)
      .text((d) => d.label);
    mg.interrupt().transition(t).attr("opacity", mOn ? 1 : 0);

    // The pointer: hover and click on the cloud.
    const pickAt = (event: PointerEvent | MouseEvent): number => {
      const c = countRef.current;
      if (!pix || c <= 0) return -1;
      const key = pix;
      if (!gridRef.current || gridRef.current.count !== c || gridRef.current.key !== key) {
        gridRef.current = { grid: buildGrid(pix.xs, pix.ys, c, 10), count: c, key };
      }
      const [px, py] = d3.pointer(event, g);
      return nearestPoint(gridRef.current.grid, pix.xs, pix.ys, px, py, 10);
    };
    root
      .on("pointermove", (event: PointerEvent) => onHover(pickAt(event)))
      .on("pointerleave", () => onHover(-1))
      .on("click", (event: MouseEvent) => {
        const k = pickAt(event);
        if (k >= 0) setSelectedPortfolio(k);
      });
  }, [geo, mc, pix, step, dur, frontier, portfolios, markers, stocks, riskFree, setSelectedPortfolio, onHover]);

  // The fill of the selected marker, and a ring on a selected cloud dot.
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo || !mc) return;
    const root = d3.select(g);
    root
      .selectAll<SVGPathElement, MarkerDatum>("g.marker path.shape")
      .attr("fill", (d) => (d.key === selectedPortfolio ? COLORS.ink : COLORS.paper));
    root.selectAll<SVGGElement, MarkerDatum>("g.marker").attr("aria-pressed", (d) => String(d.key === selectedPortfolio));
    const k = typeof selectedPortfolio === "number" && selectedPortfolio < mc.n && step >= 2 ? selectedPortfolio : -1;
    const rings: { k: number; cls: string; color: string }[] = [];
    if (k >= 0) rings.push({ k, cls: "sel", color: COLORS.ink });
    if (hover >= 0 && hover < mc.n && step >= 2) rings.push({ k: hover, cls: "hov", color: COLORS.sageDeep });
    root
      .selectAll<SVGGElement, number>("g.rings")
      .data([0])
      .join("g")
      .attr("class", "rings")
      .attr("pointer-events", "none")
      .selectAll<SVGCircleElement, (typeof rings)[number]>("circle")
      .data(rings, (d) => d.cls)
      .join("circle")
      .attr("cx", (d) => geo.x(mc.risk[d.k]))
      .attr("cy", (d) => geo.y(mc.ret[d.k]))
      .attr("r", 6)
      .attr("fill", "none")
      .attr("stroke", (d) => d.color)
      .attr("stroke-width", 2);
  }, [selectedPortfolio, hover, geo, mc, step, markers]);

  if (!mc || !geo) return <div ref={box} className={styles.fill} />;

  const h = hover >= 0 && hover < mc.n && step >= 2 ? hover : -1;
  // Keep the last place while the card fades out.
  if (h >= 0) lastHover.current = h;
  const th = lastHover.current >= 0 && lastHover.current < mc.n ? lastHover.current : -1;
  const label =
    step < 2 ? null : count >= mc.n ? `${mc.n.toLocaleString("en-US")} portfolios` : `${count.toLocaleString("en-US")} portfolios…`;

  return (
    <div ref={box} className={styles.fill}>
      <canvas ref={canvasRef} width={Math.round(width * dpr)} height={Math.round(height * dpr)} style={{ width, height }} aria-hidden="true" />
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`Risk against return. ${stocks.length} basket stocks${step >= 2 ? `, and ${mc.n.toLocaleString("en-US")} random portfolios coloured by Sharpe ratio` : ""}${step >= 3 ? ", with the efficient frontier along the upper-left edge" : ""}${step >= 4 ? ", markers for the maximum Sharpe, minimum volatility and equal-weight portfolios, and the capital market line" : ""}.`}
      >
        <g ref={gRef} transform={`translate(${geo.m.left},${geo.m.top})`} />
      </svg>
      {label ? (
        <div className={styles.counter} aria-live="off">
          {label}
        </div>
      ) : null}
      <Tooltip
        x={th >= 0 ? geo.x(mc.risk[th]) + geo.m.left : 0}
        y={th >= 0 ? geo.y(mc.ret[th]) + geo.m.top : 0}
        visible={h >= 0}
        containerWidth={width}
        width={170}
      >
        {th >= 0 ? (
          <>
            <strong>Portfolio #{th + 1}</strong>
            <br />
            return {pct(mc.ret[th])} · vol {pct(mc.risk[th])}
            <br />
            Sharpe {sharpeFmt(mc.sharpe[th])} · click to pick
          </>
        ) : null}
      </Tooltip>
    </div>
  );
}
