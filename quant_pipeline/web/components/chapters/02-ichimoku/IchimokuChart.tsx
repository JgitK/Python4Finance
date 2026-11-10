"use client";

// The pane of chapter 2: an Ichimoku chart that builds layer by layer.
// React makes the <svg>. D3 draws only inside the <g> that a ref points to.
//
//   step 0  close
//   step 1  + conversion (9) and base (26)
//   step 2  + the cloud
//   step 3  + the lagging line
//   step 4  everything (the reader's turn)

import * as d3 from "d3";
// d3 says it has no side effects, so import the transition patch by hand.
import "d3-transition";
import { useEffect, useRef, useState } from "react";
import { usePrefersReducedMotion, useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { COLORS, d3Ease, num } from "@/lib/theme";
import type { Ichimoku } from "@/lib/types";
import { cloudRuns, firstFutureIndex, monthTicks, priceDomain } from "./helpers";

export const SERIES = [
  { key: "close", label: "Close", minStep: 0, color: COLORS.ink, width: 1.7, dash: null as string | null },
  { key: "conversion", label: "Fast line (9 days)", minStep: 1, color: "#3164a3", width: 1.5, dash: null },
  { key: "base", label: "Slow line (26 days)", minStep: 1, color: COLORS.tanDeep, width: 1.5, dash: null },
  { key: "lagging", label: "Lagging line", minStep: 3, color: "#7c4d90", width: 1.4, dash: "4 3" },
] as const;

export const CLOUD_UP = COLORS.sageDeep;
export const CLOUD_DOWN = "#C77A4A";

interface Readout {
  i: number;
  x: number;
  y: number;
}

interface Props {
  step: number;
  data: Ichimoku | null;
  loading: boolean;
  ticker: string | undefined;
}

const MONO = "var(--font-mono), monospace";

export function IchimokuChart({ step, data, loading, ticker }: Props) {
  const reduced = usePrefersReducedMotion();
  const [box, { width, height }] = useChartSize<HTMLDivElement>();
  const gRef = useRef<SVGGElement>(null);
  const [readout, setReadout] = useState<Readout | null>(null);
  // The keyboard cursor, so the arrow keys can move the crosshair.
  const cursor = useRef<number | null>(null);

  useEffect(() => {
    const g = gRef.current;
    if (!g || !data || width < 120 || height < 100) return;
    const narrow = width < 520;
    const m = { top: 10, right: 10, bottom: 22, left: narrow ? 40 : 46 };
    const innerW = width - m.left - m.right;
    const innerH = height - m.top - m.bottom;
    const n = data.dates.length;
    const X = d3.scaleLinear().domain([0, n - 1]).range([0, innerW]);
    const Y = d3
      .scaleLinear()
      .domain(priceDomain([data.close, data.conversion, data.base, data.spanA, data.spanB, data.lagging]))
      .range([innerH, 0])
      .nice(5);
    const future = firstFutureIndex(data.close);
    const dur = reduced ? 0 : 600;

    const root = d3.select(g).attr("transform", `translate(${m.left},${m.top})`);
    const layer = root
      .selectAll<SVGGElement, string>("g.layer")
      .data(["future", "grid", "cloud", "lines", "axis", "xh"], (d) => d)
      .join("g")
      .attr("class", (d) => `layer ${d}`);
    const L = (name: string) => layer.filter((d) => d === name);

    // The future band: the 26 days ahead, where only the cloud has values.
    const fut = L("future")
      .selectAll<SVGGElement, number>("g.fut")
      .data(future >= 0 ? [future] : [], (d) => d)
      .join((e) => {
        const f = e.append("g").attr("class", "fut");
        f.append("rect");
        f.append("text");
        return f;
      });
    fut.select("rect").attr("x", (d) => X(d - 1)).attr("y", 0).attr("width", (d) => innerW - X(d - 1)).attr("height", innerH).attr("fill", COLORS.stone).attr("fill-opacity", 0.1);
    fut
      .select("text")
      .attr("x", (d) => X(d - 1) + 4)
      .attr("y", 11)
      .attr("font-size", 10)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .text((d) => { const w = innerW - X(d - 1); return w < 60 ? "ahead" : w < 100 ? "26d ahead" : "26 days ahead"; });

    // Grid and axes.
    const yt = Y.ticks(5);
    L("grid")
      .selectAll<SVGLineElement, number>("line")
      .data(yt, (d) => d)
      .join("line")
      .attr("x1", 0)
      .attr("x2", innerW)
      .attr("y1", (d) => Y(d))
      .attr("y2", (d) => Y(d))
      .attr("stroke", COLORS.grid);
    const mt = monthTicks(data.dates)
      .filter((t) => t.i > 2 && t.i < n - 3)
      .filter((t, k, all) => (!narrow || k % 2 === 0) && (k === 0 || X(t.i) - X(all[k - 1].i) > 36 || !narrow));
    // Drop a label that would touch the one before it.
    for (let k = mt.length - 1; k > 0; k--) if (X(mt[k].i) - X(mt[k - 1].i) < 34) mt.splice(k - 1, 1);
    const axis = L("axis");
    axis
      .selectAll<SVGTextElement, number>("text.y")
      .data(yt, (d) => d)
      .join("text")
      .attr("class", "y")
      .attr("x", -6)
      .attr("y", (d) => Y(d))
      .attr("dy", "0.34em")
      .attr("text-anchor", "end")
      .attr("font-size", 10.5)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .text((d) => `$${d3.format(",.0f")(d)}`);
    axis
      .selectAll<SVGTextElement, { i: number; label: string }>("text.x")
      .data(mt, (d) => d.i)
      .join("text")
      .attr("class", "x")
      .attr("x", (d) => X(d.i))
      .attr("y", innerH + 15)
      .attr("text-anchor", "middle")
      .attr("font-size", 10.5)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", MONO)
      .text((d) => d.label);

    // The cloud: one polygon for each run of one colour.
    const runs = cloudRuns(data.spanA, data.spanB);
    const area = d3
      .area<{ x: number; a: number; b: number }>()
      .x((p) => X(p.x))
      .y0((p) => Y(p.b))
      .y1((p) => Y(p.a));
    const cloudOn = step >= 2;
    const cloud = L("cloud")
      .selectAll<SVGPathElement, (typeof runs)[number]>("path")
      .data(runs)
      .join("path")
      .attr("d", (r) => area(r.points))
      .attr("fill", (r) => (r.sign > 0 ? CLOUD_UP : CLOUD_DOWN))
      .attr("fill-opacity", (r) => (r.sign > 0 ? 0.3 : 0.4))
      .attr("stroke", (r) => (r.sign > 0 ? CLOUD_UP : CLOUD_DOWN))
      .attr("stroke-opacity", 0.35)
      .attr("stroke-width", 0.8);
    cloud.interrupt();
    if (dur) cloud.transition().duration(dur).ease(d3Ease).attr("opacity", cloudOn ? 1 : 0);
    else cloud.attr("opacity", cloudOn ? 1 : 0);

    // The lines. A line that appears draws in from the left.
    const gen = (key: (typeof SERIES)[number]["key"]) =>
      d3
        .line<number | null>()
        .defined((v) => v != null)
        .x((_, i) => X(i))
        .y((v) => Y(v as number))(data[key]);
    const lines = L("lines")
      .selectAll<SVGPathElement, (typeof SERIES)[number]>("path")
      .data(SERIES as unknown as (typeof SERIES)[number][], (s) => s.key)
      .join("path")
      .attr("fill", "none")
      .attr("stroke-linejoin", "round")
      .attr("stroke", (s) => s.color)
      .attr("stroke-width", (s) => s.width)
      .attr("d", (s) => gen(s.key));
    lines.each(function (s) {
      const p = d3.select(this);
      const on = step >= s.minStep;
      const was = this.dataset.on === "1" && this.dataset.t === data.ticker;
      const wasOff = this.dataset.on === "0" && this.dataset.t === data.ticker;
      p.interrupt();
      this.dataset.on = on ? "1" : "0";
      this.dataset.t = data.ticker;
      const dash = s.dash;
      p.attr("stroke-dasharray", dash).attr("stroke-dashoffset", null);
      if (on && wasOff && !reduced && !dash) {
        const len = this.getTotalLength();
        p.attr("opacity", 1)
          .attr("stroke-dasharray", `${len} ${len}`)
          .attr("stroke-dashoffset", len)
          .transition()
          .duration(900)
          .ease(d3Ease)
          .attr("stroke-dashoffset", 0)
          .on("end", () => p.attr("stroke-dasharray", null));
      } else if (on && wasOff && !reduced) {
        p.attr("opacity", 0).transition().duration(600).attr("opacity", 1);
      } else if (!on && was && !reduced) {
        p.transition().duration(300).attr("opacity", 0);
      } else {
        p.attr("opacity", on ? 1 : 0);
      }
    });

    // The crosshair and the readout.
    const xh = L("xh");
    xh.selectAll("*").remove();
    const vline = xh.append("line").attr("y1", 0).attr("y2", innerH).attr("stroke", COLORS.ink).attr("stroke-opacity", 0.45).attr("stroke-dasharray", "3 3").attr("display", "none");
    const marks = xh.append("g");
    const visible = SERIES.filter((s) => step >= s.minStep);
    const move = (i: number | null) => {
      if (i == null) {
        vline.attr("display", "none");
        marks.selectAll("*").remove();
        cursor.current = null;
        setReadout(null);
        return;
      }
      const idx = Math.max(0, Math.min(n - 1, i));
      cursor.current = idx;
      vline.attr("display", null).attr("x1", X(idx)).attr("x2", X(idx));
      const pts = visible.filter((s) => data[s.key][idx] != null);
      marks
        .selectAll<SVGCircleElement, (typeof SERIES)[number]>("circle")
        .data(pts, (s) => s.key)
        .join("circle")
        .attr("r", 3.8)
        .attr("fill", (s) => s.color)
        .attr("stroke", COLORS.paper)
        .attr("stroke-width", 1.5)
        .attr("cx", X(idx))
        .attr("cy", (s) => Y(data[s.key][idx] as number));
      const anchor = pts.length ? (data[pts[0].key][idx] as number) : (data.spanA[idx] ?? data.spanB[idx] ?? Y.domain()[0]);
      setReadout({ i: idx, x: m.left + X(idx), y: m.top + Y(anchor) });
    };
    const overlay = L("xh")
      .selectAll<SVGRectElement, number>("rect.hit")
      .data([0])
      .join("rect")
      .attr("class", "hit")
      .attr("width", innerW)
      .attr("height", innerH)
      .attr("fill", "transparent")
      .style("cursor", "crosshair")
      .style("touch-action", "pan-y");
    overlay.raise();
    overlay
      .on("pointermove pointerdown", (e: PointerEvent) => move(Math.round(X.invert(d3.pointer(e, g)[0]))))
      .on("pointerleave", () => move(null));
    d3.select(g.ownerSVGElement!)
      .on("keydown", (e: KeyboardEvent) => {
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
          e.preventDefault();
          const from = cursor.current ?? (future > 0 ? future - 1 : n - 1);
          move(from + (e.key === "ArrowRight" ? 1 : -1));
        } else if (e.key === "Escape") move(null);
      })
      .on("blur", () => move(null));

    return () => {
      d3.select(g.ownerSVGElement!).on("keydown", null).on("blur", null);
    };
  }, [data, width, height, step, reduced]);

  // Hide the crosshair when the stock changes.
  useEffect(() => {
    setReadout(null);
    cursor.current = null;
  }, [ticker]);

  const rows =
    readout && data
      ? [
          ...SERIES.filter((s) => step >= s.minStep && data[s.key][readout.i] != null).map((s) => ({
            key: s.key,
            label: s.label,
            color: s.color,
            value: num(data[s.key][readout.i] as number, 2),
          })),
          ...(step >= 2 && data.spanA[readout.i] != null && data.spanB[readout.i] != null
            ? [
                {
                  key: "cloud",
                  label: (data.spanA[readout.i] as number) >= (data.spanB[readout.i] as number) ? "Cloud (rising)" : "Cloud (falling)",
                  color: (data.spanA[readout.i] as number) >= (data.spanB[readout.i] as number) ? CLOUD_UP : CLOUD_DOWN,
                  value: `${num(Math.min(data.spanA[readout.i] as number, data.spanB[readout.i] as number), 2)} to ${num(Math.max(data.spanA[readout.i] as number, data.spanB[readout.i] as number), 2)}`,
                },
              ]
            : []),
        ]
      : [];
  const future = data ? firstFutureIndex(data.close) : -1;

  return (
    <div ref={box} className="pane-fill" style={{ position: "relative" }}>
      {width > 0 && data ? (
        <svg
          width={width}
          height={height}
          tabIndex={0}
          role="img"
          aria-label={`Ichimoku chart of ${data.ticker} over the last 12 months. Use the left and right arrow keys to read values by date.`}
          style={{ display: "block" }}
        >
          <g ref={gRef} />
        </svg>
      ) : null}
      {!data ? (
        <p className="mono" style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", margin: 0, textAlign: "center", padding: 24, fontSize: 12.5, color: "var(--ink-soft)" }}>
          {loading ? "Loading the chart…" : ticker ? `No Ichimoku file for ${ticker}.` : "Pick a stock in chapter 1 first."}
        </p>
      ) : null}
      <Tooltip x={readout?.x} y={readout?.y} visible={!!readout} containerWidth={width} width={200}>
        {readout && data ? (
          <>
            <strong>{data.dates[readout.i]}</strong>
            {future >= 0 && readout.i >= future ? <span style={{ color: COLORS.tanDeep }}> (ahead)</span> : null}
            {rows.map((r) => (
              <div key={r.key} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span aria-hidden="true" style={{ width: 8, height: 8, borderRadius: 2, background: r.color, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{r.label}</span>
                <span className="mono">{r.value}</span>
              </div>
            ))}
          </>
        ) : null}
      </Tooltip>
    </div>
  );
}
