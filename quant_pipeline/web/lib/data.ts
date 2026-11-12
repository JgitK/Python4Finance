// Fetch and cache the JSON files of the data contract (lib/types.ts).
//
// The base path is /data. When /data/meta.json is missing, the loader uses
// /data-fixture, and the bundle says so (source "fixture"), so the page can
// show a badge. Each file loads one time. Chapters do not call this module:
// they read the store (lib/store.tsx).

import type { Ichimoku, Leaders, Meta, Returns, Scorecard } from "./types";

export const DATA_BASE = "/data";
export const FIXTURE_BASE = "/data-fixture";

export type DataSource = "data" | "fixture";

export interface DataBundle {
  meta: Meta;
  leaders: Leaders;
  returns: Returns;
  scorecard: Scorecard;
  /** "fixture" when the real files are missing. */
  source: DataSource;
  /** "/data" or "/data-fixture". */
  base: string;
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

async function loadFrom(base: string, source: DataSource, meta: Meta): Promise<DataBundle> {
  const [leaders, returns, scorecard] = await Promise.all([
    getJson<Leaders>(`${base}/leaders.json`),
    getJson<Returns>(`${base}/returns.json`),
    getJson<Scorecard>(`${base}/scorecard.json`),
  ]);
  return { meta, leaders, returns, scorecard, source, base };
}

let bundlePromise: Promise<DataBundle> | null = null;

/** Load the four main files one time. Later calls get the same promise. */
export function loadData(): Promise<DataBundle> {
  if (!bundlePromise) {
    bundlePromise = (async () => {
      let meta: Meta | null = null;
      // "?data=fixture" in the URL forces the fixture, for a test.
      const forceFixture =
        typeof window !== "undefined" && new URLSearchParams(window.location.search).get("data") === "fixture";
      if (!forceFixture) {
        try {
          meta = await getJson<Meta>(`${DATA_BASE}/meta.json`);
        } catch {
          meta = null;
        }
      }
      if (meta) return loadFrom(DATA_BASE, "data", meta);
      const fixtureMeta = await getJson<Meta>(`${FIXTURE_BASE}/meta.json`);
      return loadFrom(FIXTURE_BASE, "fixture", fixtureMeta);
    })();
    // Let a later call try again after a failure.
    bundlePromise.catch(() => {
      bundlePromise = null;
    });
  }
  return bundlePromise;
}

const ichimokuCache = new Map<string, Promise<Ichimoku | null>>();

/**
 * Load ichimoku/<TICKER>.json from the same base as the bundle. Each
 * ticker loads one time. The promise gives null when the file is missing.
 */
export function loadIchimoku(ticker: string, base: string): Promise<Ichimoku | null> {
  const key = `${base}/${ticker}`;
  let p = ichimokuCache.get(key);
  if (!p) {
    p = getJson<Ichimoku>(`${base}/ichimoku/${encodeURIComponent(ticker)}.json`).catch(() => null);
    ichimokuCache.set(key, p);
  }
  return p;
}
