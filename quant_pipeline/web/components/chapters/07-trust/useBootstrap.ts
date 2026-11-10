"use client";

// Run the bootstrap in small chunks so the page keeps scrolling. Each chunk
// is 20 draws with its own seed. The points come in a chunk at a time, so
// the scatter fills up while the reader looks at it.

import { useEffect, useState } from "react";
import { bootstrapMaxSharpe, type BootstrapPoint } from "@/lib/portfolio";

export const BOOT_CHUNKS = 10;
export const BOOT_CHUNK_DRAWS = 20; // 10 x 20 = 200 samples
const BASE_SEED = 42;

interface State {
  key: string;
  points: BootstrapPoint[];
  done: boolean;
}

/**
 * `key` names the basket. A new key starts a new run. `enabled` false waits
 * (the chapter is far down the page). Returns the points so far.
 */
export function useBootstrap(rows: number[][] | null, key: string, enabled: boolean): { points: BootstrapPoint[]; done: boolean; progress: number } {
  const [state, setState] = useState<State>({ key: "", points: [], done: false });

  useEffect(() => {
    if (!enabled || !rows || rows.length < 2) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let idle: number | null = null;
    let acc: BootstrapPoint[] = [];
    let i = 0;

    const run = () => {
      if (cancelled) return;
      acc = acc.concat(bootstrapMaxSharpe(rows, BOOT_CHUNK_DRAWS, BASE_SEED + i * 7919));
      i += 1;
      setState({ key, points: acc, done: i >= BOOT_CHUNKS });
      if (i < BOOT_CHUNKS) timer = setTimeout(run, 24);
    };

    const ric = (window as unknown as { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number }).requestIdleCallback;
    if (ric) idle = ric(run, { timeout: 800 });
    else timer = setTimeout(run, 60);

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      const cic = (window as unknown as { cancelIdleCallback?: (h: number) => void }).cancelIdleCallback;
      if (idle !== null && cic) cic(idle);
    };
  }, [rows, key, enabled]);

  const mine = state.key === key ? state : { key, points: [], done: false };
  return { points: mine.points, done: mine.done, progress: Math.min(1, mine.points.length / (BOOT_CHUNKS * BOOT_CHUNK_DRAWS)) };
}
