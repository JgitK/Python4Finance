"use client";

// A small tween for a number that a step animates (a slider value). It
// runs through key frames with requestAnimationFrame. A new run or a
// cancel stops the old run at once, so a fast scroll or a hand on the
// slider always wins.

import { useCallback, useEffect, useRef } from "react";
import { d3Ease } from "@/lib/theme";

export interface KeyFrame {
  /** The value at the end of this segment. */
  to: number;
  /** The length of this segment in ms. */
  ms: number;
}

export function useTween() {
  const frame = useRef<number | null>(null);

  const cancel = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
  }, []);

  const run = useCallback(
    (from: number, frames: KeyFrame[], onValue: (v: number) => void, onDone?: () => void) => {
      cancel();
      const total = frames.reduce((s, f) => s + f.ms, 0);
      if (total <= 0) {
        if (frames.length) onValue(frames[frames.length - 1].to);
        onDone?.();
        return;
      }
      const start = performance.now();
      const tick = (now: number) => {
        let t = now - start;
        let a = from;
        for (const f of frames) {
          if (t <= f.ms) {
            const k = f.ms > 0 ? d3Ease(t / f.ms) : 1;
            onValue(a + (f.to - a) * k);
            frame.current = requestAnimationFrame(tick);
            return;
          }
          t -= f.ms;
          a = f.to;
        }
        onValue(a);
        frame.current = null;
        onDone?.();
      };
      frame.current = requestAnimationFrame(tick);
    },
    [cancel],
  );

  useEffect(() => cancel, [cancel]);
  return { run, cancel };
}
