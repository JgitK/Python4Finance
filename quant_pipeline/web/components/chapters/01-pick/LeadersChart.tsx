"use client";

// The pane of chapter 1: one row per sector, the top 5 stocks as dots on a
// shared x axis (the return of the window), each with a 95% whisker.
// React makes the <svg>. D3 draws only inside the <g> that a ref points to.

import * as d3 from "d3";
// d3 says it has no side effects, so import the transition patch by hand.
import "d3-transition";
import { useEffect, useRef, useState } from "react";
import { usePrefersReducedMotion, useChartSize } from "@/components/scrolly";
import { Tooltip } from "@/components/ui";
import { useStore } from "@/lib/store";
import { COLORS, DURATION, LOSS, GAIN, d3Ease, pct, sectorShort, signedPct } from "@/lib/theme";
import type { Leader } from "@/lib/types";
import { clipRange, pinX, sectorCounts, xDomain } from "./helpers";

interface Hover {
  leader: Leader;
  x: number;
  y: number;
}

interface Props {
  step: number;
  leaders: Leader[];
  sectors: string[];
  /** Called when a click cannot change the basket. */
  onBlocked: (message: string) => void;
}

// Keep the focus ring and the outline rules in one place.
const CSS = `
.pk-dot { outline: none; cursor: pointer; }
.pk-dot .pk-focus { stroke-opacity: 0; }
.pk-dot:focus-visible .pk-focus { stroke-opacity: 1; }
.pk-dot:hover .pk-hit { fill-opacity: 0.08; }
`;

export function LeadersChart({ step, leaders, sectors, onBlocked }: Props) {
  const { basket, toggleTicker, canAdd, canRemove, sectorOf } = useStore();
  const reduced = usePrefersReducedMotion();
  const [box, { width, height }] = useChartSize<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const [hover, setHover] = useState<Hover | null>(null);

  // The D3 listeners call the newest handlers through this ref.
  const act = useRef({ toggle: (_l: Leader) => {}, show: (_l: Leader, _n: Element) => {}, hide: () => {} });
  useEffect(() => {
    act.current = {
      toggle: (l) => {
        const picked = basket.includes(l.ticker);
        if (picked && !canRemove) return onBlocked("A basket needs at least 2 stocks, so this one stays.");
        if (!picked && !canAdd) return onBlocked("The basket is full (15 stocks). Remove one to add another.");
        toggleTicker(l.ticker);
      },
      show: (l, node) => {
        const s = svgRef.current?.getBoundingClientRect();
        const c = node.getBoundingClientRect();
        if (!s) return;
        setHover({ leader: l, x: c.left + c.width / 2 - s.left, y: c.top + c.height / 2 - s.top });
      },
      hide: () => setHover(null),
    };
  });

  const hoverTicker = hover?.leader.ticker ?? null;

  useEffect(() => {
    const g = gRef.current;
    if (!g || width < 100 || height < 100) return;
    const narrow = width < 520;
    const m = { top: 6, right: 44, bottom: 24, left: narrow ? 74 : 90 };
    const innerW = width - m.left - m.right;
    const innerH = height - m.top - m.bottom;
    const n = sectors.length || 1;
    const rh = innerH / n;
    const domain = xDomain(leaders);
    const X = d3.scaleLinear().domain(domain).range([0, innerW]);
    const rowY = (s: string) => Math.max(0, sectors.indexOf(s)) * rh + rh / 2;
    const spread = Math.min(4.5, rh * 0.16);
    const r = Math.max(2.8, Math.min(5.2, rh * 0.14));
    const counts = sectorCounts(basket, sectorOf);
    const dur = reduced ? 0 : DURATION.medium;
    // A transition for the selection, or the selection itself when motion is off.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tr = (sel: any) => (dur ? sel.transition().duration(dur).ease(d3Ease) : sel);

    const root = d3.select(g).attr("transform", `translate(${m.left},${m.top})`);
    const layer = root
      .selectAll<SVGGElement, string>("g.layer")
      .data(["grid", "rows", "axis", "dots"], (d) => d)
      .join("g")
      .attr("class", (d) => `layer ${d}`);
    const L = (name: string) => layer.filter((d) => d === name);

    // Grid: vertical lines at the ticks, and the zero line.
    const ticks = X.ticks(narrow ? 4 : 6);
    L("grid")
      .selectAll<SVGLineElement, number>("line")
      .data(ticks, (d) => d)
      .join("line")
      .attr("y1", 0)
      .attr("y2", innerH)
      .attr("stroke", (d) => (d === 0 ? COLORS.inkSoft : COLORS.grid))
      .attr("stroke-dasharray", (d) => (d === 0 ? "3 3" : null))
      .attr("stroke-opacity", (d) => (d === 0 ? 0.7 : 1))
      .attr("x1", (d) => X(d))
      .attr("x2", (d) => X(d));

    // Rows: a tint when the sector holds a pick, the sector name, the count bar.
    const rows = L("rows")
      .selectAll<SVGGElement, string>("g.row")
      .data(sectors, (d) => d)
      .join((enter) => {
        const e = enter.append("g").attr("class", "row");
        e.append("rect").attr("class", "tint");
        e.append("line").attr("class", "mid");
        e.append("text").attr("class", "name");
        e.append("rect").attr("class", "bar");
        e.append("text").attr("class", "count");
        return e;
      })
      .attr("transform", (_, i) => `translate(0,${i * rh})`);
    rows
      .select<SVGRectElement>("rect.tint")
      .attr("x", -m.left + 2)
      .attr("width", width - 4)
      .attr("height", rh)
      .attr("fill", COLORS.sage)
      .attr("fill-opacity", (s) => (counts[s] ? 0.1 : 0));
    rows
      .select<SVGLineElement>("line.mid")
      .attr("x1", 0)
      .attr("x2", innerW)
      .attr("y1", rh / 2)
      .attr("y2", rh / 2)
      .attr("stroke", COLORS.grid)
      .attr("stroke-opacity", 0.8);
    rows
      .select<SVGTextElement>("text.name")
      .attr("x", -8)
      .attr("y", rh / 2)
      .attr("dy", "0.34em")
      .attr("text-anchor", "end")
      .attr("font-size", narrow ? 9 : 11)
      .attr("fill", COLORS.ink)
      .style("font-family", "var(--font-mono), monospace")
      .text((s) => sectorShort(s));
    rows
      .select<SVGRectElement>("rect.bar")
      .attr("x", innerW + 8)
      .attr("y", rh / 2 - 3)
      .attr("height", 6)
      .attr("rx", 2)
      .attr("fill", GAIN)
      .attr("width", (s) => Math.min(counts[s] ?? 0, 5) * 4);
    rows
      .select<SVGTextElement>("text.count")
      .attr("x", innerW + 8 + 5 * 4 + 4)
      .attr("y", rh / 2)
      .attr("dy", "0.34em")
      .attr("font-size", 10.5)
      .attr("fill", COLORS.inkSoft)
      .style("font-family", "var(--font-mono), monospace")
      .text((s) => (counts[s] ? `${counts[s]}` : ""));

    // Axis.
    const axis = d3
      .axisBottom(X)
      .tickValues(ticks)
      .tickFormat((d) => signedPct(d as number, 0))
      .tickSize(3);
    const axisG = L("axis").attr("transform", `translate(0,${innerH})`).call(axis);
    axisG.select(".domain").attr("stroke", COLORS.grid);
    axisG.selectAll("line").attr("stroke", COLORS.paneBorder);
    axisG
      .selectAll("text")
      .attr("fill", COLORS.inkSoft)
      .attr("font-size", 10.5)
      .style("font-family", "var(--font-mono), monospace");

    // Dots. Each dot is one <g> with a whisker, rings, a circle and a label.
    const showWhiskers = step >= 2;
    const showStable = step >= 4;
    const pos = (l: Leader) => ({ x: X(pinX(l.cumReturn, domain)), y: rowY(l.sector) + (l.rank - 3) * spread });
    const dots = L("dots")
      .selectAll<SVGGElement, Leader>("g.pk-dot")
      .data(leaders, (d) => d.ticker)
      .join(
        (enter) => {
          const e = enter
            .append("g")
            .attr("class", "pk-dot")
            .attr("role", "button")
            .attr("tabindex", 0)
            .attr("opacity", 0)
            .attr("transform", (d) => `translate(${pos(d).x},${pos(d).y})`);
          e.append("line").attr("class", "whisker");
          e.append("path").attr("class", "capL");
          e.append("path").attr("class", "capR");
          e.append("circle").attr("class", "stable-ring");
          e.append("circle").attr("class", "pick-ring");
          e.append("circle").attr("class", "pk-hit").attr("fill", COLORS.ink).attr("fill-opacity", 0);
          e.append("circle").attr("class", "dot");
          e.append("circle").attr("class", "pk-focus");
          e.append("text").attr("class", "label");
          return e;
        },
        (update) => update,
        (exit) => {
          tr(exit.attr("pointer-events", "none")).attr("opacity", 0).remove();
          return exit;
        },
      );
    tr(dots).attr("opacity", 1).attr("transform", (d: Leader) => `translate(${pos(d).x},${pos(d).y})`);

    dots
      .attr("aria-pressed", (d) => basket.includes(d.ticker))
      .attr("aria-label", (d) => {
        const picked = basket.includes(d.ticker) ? "in your basket, press to remove" : "press to add to your basket";
        return `${d.ticker}, ${sectorShort(d.sector)}, rank ${d.rank}, return ${signedPct(d.cumReturn)}, ${picked}`;
      })
      .on("click", (_e, d) => act.current.toggle(d))
      .on("keydown", (e: KeyboardEvent, d) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          act.current.toggle(d);
        }
      })
      .on("mouseenter focus", function (_e, d) {
        act.current.show(d, this.querySelector("circle.dot") ?? this);
      })
      .on("mouseleave blur", () => act.current.hide());

    const picked = (d: Leader) => basket.includes(d.ticker);
    const clip = (d: Leader) => clipRange(d.rangeLow, d.rangeHigh, domain);

    tr(dots.select("line.whisker"))
      .attr("x1", (d: Leader) => X(clip(d).from) - pos(d).x)
      .attr("x2", (d: Leader) => X(clip(d).to) - pos(d).x)
      .attr("y1", 0)
      .attr("y2", 0)
      .attr("stroke", (d: Leader) => (picked(d) ? GAIN : COLORS.inkSoft))
      .attr("stroke-width", (d: Leader) => (picked(d) ? 1.8 : 1.2))
      .attr("stroke-opacity", (d: Leader) => (showWhiskers ? (picked(d) ? 0.85 : 0.4) : 0));
    // A small triangle at a cut end says the true range runs on past the edge.
    const cap = (side: -1 | 1) => (d: Leader) => {
      const c = clip(d);
      const cut = side === -1 ? c.clipLow : c.clipHigh;
      if (!cut) return "";
      const ex = X(side === -1 ? c.from : c.to) - pos(d).x;
      return `M${ex},0 L${ex - side * 4.5},-3 L${ex - side * 4.5},3 Z`;
    };
    dots
      .select("path.capL")
      .attr("d", cap(-1))
      .attr("fill", COLORS.inkSoft)
      .attr("fill-opacity", showWhiskers ? 0.6 : 0);
    dots
      .select("path.capR")
      .attr("d", cap(1))
      .attr("fill", COLORS.inkSoft)
      .attr("fill-opacity", showWhiskers ? 0.6 : 0);

    dots
      .select("circle.stable-ring")
      .attr("r", r + 7)
      .attr("fill", "none")
      .attr("stroke", COLORS.tanDeep)
      .attr("stroke-width", 1.4)
      .attr("stroke-dasharray", "2.5 2.5")
      .attr("stroke-opacity", (d: Leader) => (showStable && d.stable ? 1 : 0));
    dots
      .select("circle.pick-ring")
      .attr("r", r + 3.5)
      .attr("fill", "none")
      .attr("stroke", GAIN)
      .attr("stroke-width", 1.6)
      .attr("stroke-opacity", (d: Leader) => (picked(d) ? 1 : 0));
    dots.select("circle.pk-hit").attr("r", r + 4);
    dots
      .select("circle.dot")
      .attr("r", r)
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 1.2)
      .attr("fill", (d: Leader) => (picked(d) ? GAIN : COLORS.stone));
    dots.select("circle.pk-focus").attr("r", r + 7).attr("fill", "none").attr("stroke", COLORS.ink).attr("stroke-width", 2);

    const nearRight = (d: Leader) => pos(d).x > innerW - 52;
    dots
      .select<SVGTextElement>("text.label")
      .attr("x", (d) => (nearRight(d) ? -(r + 7) : r + 7))
      .attr("dy", "0.34em")
      .attr("text-anchor", (d) => (nearRight(d) ? "end" : "start"))
      .attr("font-size", 10.5)
      .attr("font-weight", 600)
      .attr("fill", COLORS.ink)
      .attr("stroke", COLORS.paper)
      .attr("stroke-width", 3)
      .attr("paint-order", "stroke")
      .attr("pointer-events", "none")
      .style("font-family", "var(--font-mono), monospace")
      .attr("opacity", (d) => (picked(d) || d.ticker === hoverTicker ? 1 : 0))
      .text((d) => d.ticker);

    // A hovered or picked dot goes to the front.
    dots.sort((a, b) => Number(picked(a) || a.ticker === hoverTicker) - Number(picked(b) || b.ticker === hoverTicker) || a.rank - b.rank);
    return () => {
      d3.select(g).selectAll("*").interrupt();
    };
  }, [width, height, leaders, sectors, basket, step, reduced, hoverTicker, sectorOf]);

  const h = hover?.leader;
  const label = `Top 5 stocks of each of ${sectors.length} sectors by return over the window. ${basket.length} stocks are in your basket.`;
  return (
    <div ref={box} className="pane-fill" style={{ position: "relative" }}>
      <style>{CSS}</style>
      {width > 0 ? (
        <svg ref={svgRef} width={width} height={height} role="group" aria-label={label} style={{ display: "block" }}>
          <g ref={gRef} />
        </svg>
      ) : null}
      <Tooltip x={hover?.x} y={hover?.y} visible={!!h} containerWidth={width} width={190}>
        {h ? (
          <>
            <strong>{h.ticker}</strong> · {sectorShort(h.sector)} · rank {h.rank}
            <br />
            Return{" "}
            <span style={{ color: h.cumReturn < 0 ? LOSS : GAIN, fontWeight: 600 }}>{signedPct(h.cumReturn)}</span>
            <br />
            95% range {signedPct(h.rangeLow, 0)} to {signedPct(h.rangeHigh, 0)}
            <br />
            Volatility {pct(h.annualVol, 0)} a year
            {h.stable ? (
              <>
                <br />
                Leads on 3M, 6M and 1Y
              </>
            ) : null}
            <br />
            <span style={{ color: COLORS.tanDeep }}>{basket.includes(h.ticker) ? "Click to remove" : "Click to add"}</span>
          </>
        ) : null}
      </Tooltip>
    </div>
  );
}
