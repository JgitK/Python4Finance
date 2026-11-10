"use client";

// two-stocks.svg: the curve of all mixes of two stocks in risk and return
// space, and a dot for the mix of the weight slider.
//
// Steps (of the first Scrolly of chapter 4):
//   0  Only the two stocks and the mix dot (100% in A).
//   1  The curve of all mixes, the straight "lockstep" line (rho +1), and
//      the wash between them: the bend.
//   2  Also the ghost curve of rho -1, the most bend there can be.
//
// The paths follow the sliders with no transition. Only the show and hide
// of a layer has a transition.

import * as d3 from "d3";
import { useEffect, useMemo, useRef } from "react";
import { useChartSize } from "@/components/scrolly";
import { twoAssetCurve } from "@/lib/portfolio";
import { COLORS, DURATION, d3Ease, pct, signed } from "@/lib/theme";
import { MONO, margins, styleAxis, useDuration } from "../03-risk/kit";
import styles from "../03-risk/core.module.css";
import { mixPoint, straightRisk } from "./math";

export interface Stock {
  ticker: string;
  ret: number;
  vol: number;
  color: string;
}

export interface TwoStocksChartProps {
  step: number;
  a: Stock;
  b: Stock;
  /** The weight in A, 0 to 1. */
  w: number;
  /** The correlation of the drawn curve (real or pretend). */
  rho: number;
}

export function TwoStocksChart({ step, a, b, w, rho }: TwoStocksChartProps) {
  const [box, { width, height }] = useChartSize();
  const gRef = useRef<SVGGElement>(null);
  const dur = useDuration(DURATION.medium);

  const geo = useMemo(() => {
    if (width === 0 || height === 0) return null;
    const m = margins(width);
    const iw = Math.max(10, width - m.left - m.right);
    const ih = Math.max(10, height - m.top - m.bottom);
    const fs = width < 480 ? 10 : 11;
    const x = d3
      .scaleLinear()
      .domain([0, Math.max(a.vol, b.vol) * 1.15])
      .nice()
      .range([0, iw]);
    const lo = Math.min(a.ret, b.ret);
    const hi = Math.max(a.ret, b.ret);
    const pad = (hi - lo) * 0.15 || 0.05;
    const y = d3
      .scaleLinear()
      .domain([lo - pad, hi + pad])
      .nice()
      .range([ih, 0]);
    return { m, iw, ih, fs, x, y };
  }, [width, height, a.vol, b.vol, a.ret, b.ret]);

  // ── The static parts and the step layers ──
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo) return;
    const { iw, ih, fs, x, y } = geo;
    const root = d3.select(g);
    const t = d3.transition().duration(dur).ease(d3Ease);
    const layer = (cls: string) => root.selectAll<SVGGElement, number>(`g.${cls}`).data([0]).join("g").attr("class", cls);

    layer("y-axis")
      .call(d3.axisLeft(y).ticks(Math.max(3, Math.round(ih / 55))).tickFormat((d) => pct(+d, 0)).tickSize(-iw).tickPadding(6))
      .call((s) => styleAxis(s, fs))
      .call((s) => s.select(".domain").remove());
    layer("x-axis")
      .attr("transform", `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.round(iw / 90))).tickFormat((d) => pct(+d, 0)))
      .call((s) => styleAxis(s, fs));
    layer("titles")
      .selectAll<SVGTextElement, { t: string; x: number; y: number; anchor: string }>("text")
      .data([
        { t: "↑ return a year", x: -geo.m.left + 2, y: -12, anchor: "start" },
        { t: "volatility →", x: iw, y: ih + geo.m.bottom - 6, anchor: "end" },
      ])
      .join("text")
      .attr("x", (d) => d.x)
      .attr("y", (d) => d.y)
      .attr("text-anchor", (d) => d.anchor)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text((d) => d.t);

    // The layers in paint order. Each one is shown or hidden by the step.
    for (const [cls, on] of [
      ["bend", step >= 1],
      ["chord", step >= 1],
      ["ghost", step >= 2],
      ["curve", step >= 1],
    ] as const) {
      layer(cls).interrupt().transition(t).attr("opacity", on ? 1 : 0);
    }
    layer("stocks");
    layer("mix");
  }, [geo, step, dur]);

  // ── The paths and dots that follow the sliders ──
  useEffect(() => {
    const g = gRef.current;
    if (!g || !geo) return;
    const { iw, fs, x, y } = geo;
    const root = d3.select(g);
    const curve = twoAssetCurve(a.ret, b.ret, a.vol, b.vol, rho, 80);
    const ghost = twoAssetCurve(a.ret, b.ret, a.vol, b.vol, -1, 80);
    const line = d3
      .line<{ risk: number; ret: number }>()
      .x((d) => x(d.risk))
      .y((d) => y(d.ret));

    // The wash between the straight line and the curve: the bend.
    const area = d3
      .area<{ weightA: number; risk: number; ret: number }>()
      .y((d) => y(d.ret))
      .x0((d) => x(straightRisk(d.weightA, a.vol, b.vol)))
      .x1((d) => x(d.risk));
    root
      .select("g.bend")
      .selectAll("path")
      .data([curve])
      .join("path")
      .attr("d", area)
      .attr("fill", COLORS.sage)
      .attr("fill-opacity", 0.14);

    const chord = root.select("g.chord");
    chord
      .selectAll("line")
      .data([0])
      .join("line")
      .attr("x1", x(a.vol))
      .attr("y1", y(a.ret))
      .attr("x2", x(b.vol))
      .attr("y2", y(b.ret))
      .attr("stroke", COLORS.stone)
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "5 4");
    const mx = (x(a.vol) + x(b.vol)) / 2;
    const my = (y(a.ret) + y(b.ret)) / 2;
    chord
      .selectAll("text")
      .data([0])
      .join("text")
      .attr("x", Math.min(mx + 8, iw - 4))
      .attr("y", my - 6)
      .attr("text-anchor", mx + 8 > iw - 130 ? "end" : "start")
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text("in lockstep (ρ +1)");

    const ghostG = root.select("g.ghost");
    ghostG
      .selectAll("path")
      .data([ghost])
      .join("path")
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", COLORS.moss)
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "2 4")
      .attr("stroke-linecap", "round");
    const tip = ghost.reduce((p, q) => (q.risk < p.risk ? q : p), ghost[0]);
    ghostG
      .selectAll("text")
      .data([0])
      .join("text")
      .attr("x", x(tip.risk) + 6)
      .attr("y", y(tip.ret) + 4)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .style("font-size", `${fs}px`)
      .text("ρ −1");

    root
      .select("g.curve")
      .selectAll("path")
      .data([curve])
      .join("path")
      .attr("d", line)
      .attr("fill", "none")
      .attr("stroke", COLORS.sageDeep)
      .attr("stroke-width", 2)
      .attr("stroke-linejoin", "round")
      .attr("stroke-linecap", "round");

    // The two stocks.
    const stocks = root
      .select("g.stocks")
      .selectAll<SVGGElement, Stock>("g")
      .data([a, b], (d) => d.ticker)
      .join((enter) => {
        const e = enter.append("g");
        e.append("circle").attr("r", 6).attr("stroke", COLORS.paper).attr("stroke-width", 2);
        e.append("text").style("font-family", MONO).style("font-weight", 600).attr("fill", COLORS.ink);
        return e;
      })
      .attr("transform", (d) => `translate(${x(d.vol)},${y(d.ret)})`);
    stocks.select("circle").attr("fill", (d) => d.color);
    stocks
      .select("text")
      .style("font-size", `${fs}px`)
      .attr("x", (d) => (x(d.vol) > iw - 60 ? -10 : 10))
      .attr("text-anchor", (d) => (x(d.vol) > iw - 60 ? "end" : "start"))
      .attr("y", 4)
      .text((d) => d.ticker);

    // The mix dot.
    const p = mixPoint(w, a.ret, b.ret, a.vol, b.vol, rho);
    const mix = root
      .select("g.mix")
      .selectAll<SVGGElement, number>("g")
      .data([0])
      .join((enter) => {
        const e = enter.append("g");
        e.append("circle").attr("r", 8).attr("fill", COLORS.paper).attr("stroke", COLORS.ink).attr("stroke-width", 2);
        e.append("circle").attr("r", 3).attr("fill", COLORS.ink);
        e.append("text").style("font-family", MONO).attr("fill", COLORS.ink).attr("y", -13).attr("text-anchor", "middle");
        return e;
      })
      .attr("transform", `translate(${x(p.risk)},${y(p.ret)})`);
    mix.select("text").style("font-size", `${fs}px`).text("your mix");
  }, [geo, a, b, w, rho]);

  const p = mixPoint(w, a.ret, b.ret, a.vol, b.vol, rho);
  return (
    <div ref={box} className={styles.fill}>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`Risk and return of mixes of ${a.ticker} and ${b.ticker}. The mix of ${Math.round(w * 100)}% ${a.ticker} has return ${pct(p.ret)} and volatility ${pct(p.risk)}, with correlation ${signed(rho)}.`}
      >
        {geo ? <g ref={gRef} transform={`translate(${geo.m.left},${geo.m.top})`} /> : null}
      </svg>
    </div>
  );
}
