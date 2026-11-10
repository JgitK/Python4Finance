"use client";

import { useCallback, useEffect, useState } from "react";

export interface ChartSize {
  width: number;
  height: number;
}

/**
 * Measure an element with a ResizeObserver.
 *
 *   const [ref, { width, height }] = useChartSize<HTMLDivElement>();
 *   return <div ref={ref} className="pane-fill">{width > 0 && <svg width={width} height={height} />}</div>;
 *
 * The size is 0 × 0 before the first measure (and on the server).
 */
export function useChartSize<T extends HTMLElement = HTMLDivElement>(): [(el: T | null) => void, ChartSize] {
  const [el, setEl] = useState<T | null>(null);
  const [size, setSize] = useState<ChartSize>({ width: 0, height: 0 });
  const ref = useCallback((node: T | null) => setEl(node), []);
  useEffect(() => {
    if (!el) return;
    const measure = (w: number, h: number) =>
      setSize((s) => (s.width === Math.round(w) && s.height === Math.round(h) ? s : { width: Math.round(w), height: Math.round(h) }));
    const box = el.getBoundingClientRect();
    measure(box.width, box.height);
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r) measure(r.width, r.height);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [ref, size];
}

/** True when the reader asks for reduced motion. Then show the end state with no transition. */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}
