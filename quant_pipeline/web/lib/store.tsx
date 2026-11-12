"use client";

// The shared state of the page: one React context.
//
// The store owns the reader's choices (basket, window, amount, selected
// portfolio, whole or fractional shares) and the loaded data. It also
// calculates the derived values one time, with useMemo, so each chapter
// reads the same numbers. A chapter reads the store. It never fetches.
//
//   const { basket, stats, mc, portfolios, selected } = useStore();
//   const { annualReturn, annualVol } = stats!;     // one entry per basket ticker
//
// The order of `basket` is canonical: by sector (the order of meta.sectors),
// then by ticker. Every array of the derived values uses this order. The
// tickers with no returns are left out of `stats.tickers`, so always index
// the derived arrays with `stats.tickers`, not with `basket`.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { loadData, loadIchimoku, type DataBundle } from "./data";
import {
  alignReturns,
  correlationMatrix,
  covarianceMatrix,
  equalWeights,
  frontierHull,
  meanVector,
  monteCarlo,
  portfolioPerformance,
  weightsAt,
  DEFAULT_SEED,
  RISK_FREE,
  TRADING_DAYS,
  type AlignedReturns,
  type FrontierPoint,
  type MonteCarloResult,
  type Performance,
} from "./portfolio";
import type { Ichimoku, Leader, WindowKey } from "./types";

// ─── Constants ───────────────────────────────────────────────────────────────

export const BASKET_MIN = 2;
export const BASKET_MAX = 15;
export const DEFAULT_WINDOW: WindowKey = "1Y";
export const DEFAULT_AMOUNT = 10_000;
export const AMOUNT_MIN = 100;
export const AMOUNT_MAX = 10_000_000;
export const MC_PORTFOLIOS = 10_000;
export const MC_SEED = DEFAULT_SEED;
/** The count of sectors in the default basket. */
export const DEFAULT_SECTORS = 8;
export const WINDOW_KEYS: WindowKey[] = ["1M", "3M", "6M", "1Y", "2Y", "5Y"];

// ─── Types ───────────────────────────────────────────────────────────────────

export type PortfolioKey = "maxSharpe" | "minVol" | "equal";
/** A named portfolio, or the index of a dot of the Monte Carlo cloud. */
export type SelectedPortfolio = PortfolioKey | number;

export interface NamedPortfolio {
  key: PortfolioKey | "custom";
  label: string;
  /** In the order of stats.tickers. Sums to 1. */
  weights: number[];
  /** ticker -> weight. */
  weightsByTicker: Record<string, number>;
  performance: Performance;
  /** The index in the Monte Carlo cloud, or null for equal weight. */
  mcIndex: number | null;
}

/** The statistics of the basket, from the aligned daily returns. */
export interface BasketStats {
  /** The tickers with returns, in canonical order. */
  tickers: string[];
  /** The sector of each ticker. */
  sectors: string[];
  /** The last price of each ticker. */
  prices: number[];
  aligned: AlignedReturns;
  meanDaily: number[];
  covDaily: number[][];
  correlation: number[][];
  /** Daily mean × 252. */
  annualReturn: number[];
  /** sqrt(daily variance × 252). */
  annualVol: number[];
  /** The years of data: aligned days / 252. */
  years: number;
  /** SPY on the same days, or null when SPY has no series. */
  benchmark: { ticker: string; annualReturn: number; annualVol: number } | null;
}

export type LoadStatus = "loading" | "ready" | "error";

export interface StoreValue {
  // Data
  status: LoadStatus;
  error: string | null;
  data: DataBundle | null;
  /** True when the page runs on public/data-fixture. */
  isFixture: boolean;
  riskFree: number;
  tradingDays: number;

  // Reader choices
  basket: string[];
  windowKey: WindowKey;
  amount: number;
  selectedPortfolio: SelectedPortfolio;
  fractional: boolean;

  // Actions
  setBasket: (tickers: string[]) => void;
  addTicker: (ticker: string) => void;
  removeTicker: (ticker: string) => void;
  toggleTicker: (ticker: string) => void;
  resetBasket: () => void;
  setWindowKey: (key: WindowKey) => void;
  setAmount: (amount: number) => void;
  setSelectedPortfolio: (p: SelectedPortfolio) => void;
  setFractional: (on: boolean) => void;
  canAdd: boolean;
  canRemove: boolean;

  // Lookups
  sectorOf: (ticker: string) => string | undefined;
  priceOf: (ticker: string) => number | undefined;
  /** The leaders of the current window. Empty while loading. */
  leaders: Leader[];
  /** The default basket for the loaded data. */
  defaultBasket: string[];

  // Derived (null while loading or when the basket has under 2 tickers with returns)
  stats: BasketStats | null;
  mc: MonteCarloResult | null;
  frontier: FrontierPoint[];
  portfolios: Record<PortfolioKey, NamedPortfolio> | null;
  /** The portfolio of selectedPortfolio. */
  selected: NamedPortfolio | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** The rank-1 stock of up to `count` sectors on a window: the sectors whose leader went up most. */
export function makeDefaultBasket(data: DataBundle, windowKey: WindowKey = DEFAULT_WINDOW, count = DEFAULT_SECTORS): string[] {
  const rows = data.leaders[windowKey] ?? [];
  return rows
    .filter((r) => r.rank === 1 && Array.isArray(data.returns.series[r.ticker]))
    .sort((a, b) => b.cumReturn - a.cumReturn)
    .slice(0, count)
    .map((r) => r.ticker);
}

function canonical(tickers: string[], data: DataBundle | null): string[] {
  const unique = [...new Set(tickers)];
  if (!data) return unique;
  const sectorIdx = new Map(data.meta.sectors.map((s, i) => [s, i]));
  const sectorOf = new Map(data.meta.tickers.map((t) => [t.ticker, t.sector]));
  const known = unique.filter((t) => sectorOf.has(t));
  return known.sort((a, b) => {
    const sa = sectorIdx.get(sectorOf.get(a)!) ?? 99;
    const sb = sectorIdx.get(sectorOf.get(b)!) ?? 99;
    return sa - sb || a.localeCompare(b);
  });
}

function named(
  key: NamedPortfolio["key"],
  label: string,
  weights: number[],
  tickers: string[],
  stats: BasketStats,
  riskFree: number,
  tradingDays: number,
  mcIndex: number | null,
): NamedPortfolio {
  return {
    key,
    label,
    weights,
    weightsByTicker: Object.fromEntries(tickers.map((t, i) => [t, weights[i]])),
    performance: portfolioPerformance(weights, stats.meanDaily, stats.covDaily, tradingDays, riskFree),
    mcIndex,
  };
}

// ─── Context ─────────────────────────────────────────────────────────────────

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DataBundle | null>(null);
  const [rawBasket, setRawBasket] = useState<string[]>([]);
  const [windowKey, setWindowKey] = useState<WindowKey>(DEFAULT_WINDOW);
  const [amount, setAmountRaw] = useState<number>(DEFAULT_AMOUNT);
  const [selectedPortfolio, setSelectedPortfolio] = useState<SelectedPortfolio>("maxSharpe");
  const [fractional, setFractional] = useState(false);

  useEffect(() => {
    let live = true;
    loadData()
      .then((d) => {
        if (!live) return;
        setData(d);
        setRawBasket(makeDefaultBasket(d));
        setStatus("ready");
      })
      .catch((e: unknown) => {
        if (!live) return;
        setError(e instanceof Error ? e.message : String(e));
        setStatus("error");
      });
    return () => {
      live = false;
    };
  }, []);

  const basket = useMemo(() => canonical(rawBasket, data), [rawBasket, data]);
  const riskFree = data?.meta.riskFree ?? RISK_FREE;
  const tradingDays = data?.meta.tradingDays ?? TRADING_DAYS;

  const tickerInfo = useMemo(() => new Map((data?.meta.tickers ?? []).map((t) => [t.ticker, t])), [data]);
  const sectorOf = useCallback((t: string) => tickerInfo.get(t)?.sector, [tickerInfo]);
  const priceOf = useCallback((t: string) => tickerInfo.get(t)?.lastPrice, [tickerInfo]);
  const defaultBasket = useMemo(() => (data ? canonical(makeDefaultBasket(data), data) : []), [data]);
  const leaders = useMemo(() => data?.leaders[windowKey] ?? [], [data, windowKey]);

  // A basket change resets a selected cloud dot, because the cloud changes.
  const changeBasket = useCallback((next: (prev: string[]) => string[]) => {
    setRawBasket((prev) => {
      const out = next(prev);
      return out;
    });
    setSelectedPortfolio((p) => (typeof p === "number" ? "maxSharpe" : p));
  }, []);

  const setBasket = useCallback(
    (tickers: string[]) => changeBasket(() => [...new Set(tickers)].slice(0, BASKET_MAX)),
    [changeBasket],
  );
  const addTicker = useCallback(
    (t: string) => changeBasket((prev) => (prev.includes(t) || prev.length >= BASKET_MAX ? prev : [...prev, t])),
    [changeBasket],
  );
  const removeTicker = useCallback(
    (t: string) => changeBasket((prev) => (prev.length <= BASKET_MIN ? prev : prev.filter((x) => x !== t))),
    [changeBasket],
  );
  const toggleTicker = useCallback(
    (t: string) =>
      changeBasket((prev) => {
        if (prev.includes(t)) return prev.length <= BASKET_MIN ? prev : prev.filter((x) => x !== t);
        return prev.length >= BASKET_MAX ? prev : [...prev, t];
      }),
    [changeBasket],
  );
  const resetBasket = useCallback(() => changeBasket(() => (data ? makeDefaultBasket(data) : [])), [changeBasket, data]);
  const setAmount = useCallback((a: number) => {
    if (!Number.isFinite(a)) return;
    setAmountRaw(Math.min(AMOUNT_MAX, Math.max(AMOUNT_MIN, Math.round(a * 100) / 100)));
  }, []);

  // ── Derived values ──
  const stats = useMemo<BasketStats | null>(() => {
    if (!data || basket.length < BASKET_MIN) return null;
    const aligned = alignReturns(data.returns, basket);
    if (aligned.tickers.length < BASKET_MIN || aligned.rows.length < 3) return null;
    const meanDaily = meanVector(aligned.rows);
    const covDaily = covarianceMatrix(aligned.rows, meanDaily);
    const bench = data.meta.benchmark;
    let benchmark: BasketStats["benchmark"] = null;
    if (Array.isArray(data.returns.series[bench])) {
      const withSpy = alignReturns(data.returns, [...aligned.tickers, bench]);
      const col = withSpy.rows.map((r) => r[r.length - 1]);
      if (col.length > 2) {
        const m = col.reduce((a, b) => a + b, 0) / col.length;
        const v = col.reduce((a, b) => a + (b - m) ** 2, 0) / (col.length - 1);
        benchmark = { ticker: bench, annualReturn: m * tradingDays, annualVol: Math.sqrt(v * tradingDays) };
      }
    }
    return {
      tickers: aligned.tickers,
      sectors: aligned.tickers.map((t) => tickerInfo.get(t)?.sector ?? ""),
      prices: aligned.tickers.map((t) => tickerInfo.get(t)?.lastPrice ?? NaN),
      aligned,
      meanDaily,
      covDaily,
      correlation: correlationMatrix(covDaily),
      annualReturn: meanDaily.map((m) => m * tradingDays),
      annualVol: covDaily.map((row, i) => Math.sqrt(row[i] * tradingDays)),
      years: aligned.rows.length / tradingDays,
      benchmark,
    };
  }, [data, basket, tickerInfo, tradingDays]);

  const mc = useMemo(
    () => (stats ? monteCarlo(stats.meanDaily, stats.covDaily, MC_PORTFOLIOS, MC_SEED, { riskFree, tradingDays }) : null),
    [stats, riskFree, tradingDays],
  );
  const frontier = useMemo(() => (mc ? frontierHull(mc.risk, mc.ret) : []), [mc]);

  const portfolios = useMemo<Record<PortfolioKey, NamedPortfolio> | null>(() => {
    if (!stats || !mc || mc.maxSharpeIndex < 0) return null;
    const t = stats.tickers;
    return {
      maxSharpe: named("maxSharpe", "Maximum Sharpe", weightsAt(mc, mc.maxSharpeIndex), t, stats, riskFree, tradingDays, mc.maxSharpeIndex),
      minVol: named("minVol", "Minimum volatility", weightsAt(mc, mc.minVolIndex), t, stats, riskFree, tradingDays, mc.minVolIndex),
      equal: named("equal", "Equal weight", equalWeights(t.length), t, stats, riskFree, tradingDays, null),
    };
  }, [stats, mc, riskFree, tradingDays]);

  const selected = useMemo<NamedPortfolio | null>(() => {
    if (!portfolios || !stats || !mc) return null;
    if (typeof selectedPortfolio === "number") {
      const k = selectedPortfolio;
      if (k < 0 || k >= mc.n) return portfolios.maxSharpe;
      return named("custom", `Portfolio #${k + 1}`, weightsAt(mc, k), stats.tickers, stats, riskFree, tradingDays, k);
    }
    return portfolios[selectedPortfolio];
  }, [portfolios, stats, mc, selectedPortfolio, riskFree, tradingDays]);

  const value = useMemo<StoreValue>(
    () => ({
      status,
      error,
      data,
      isFixture: data?.source === "fixture",
      riskFree,
      tradingDays,
      basket,
      windowKey,
      amount,
      selectedPortfolio,
      fractional,
      setBasket,
      addTicker,
      removeTicker,
      toggleTicker,
      resetBasket,
      setWindowKey,
      setAmount,
      setSelectedPortfolio,
      setFractional,
      canAdd: basket.length < BASKET_MAX,
      canRemove: basket.length > BASKET_MIN,
      sectorOf,
      priceOf,
      leaders,
      defaultBasket,
      stats,
      mc,
      frontier,
      portfolios,
      selected,
    }),
    [
      status, error, data, riskFree, tradingDays, basket, windowKey, amount, selectedPortfolio, fractional,
      setBasket, addTicker, removeTicker, toggleTicker, resetBasket, setAmount, sectorOf, priceOf, leaders,
      defaultBasket, stats, mc, frontier, portfolios, selected,
    ],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

// ─── Hooks ───────────────────────────────────────────────────────────────────

/** The whole store. Throws outside <StoreProvider>. */
export function useStore(): StoreValue {
  const v = useContext(StoreContext);
  if (!v) throw new Error("useStore must be used inside <StoreProvider>.");
  return v;
}

/** The basket and its actions. */
export function useBasket() {
  const s = useStore();
  return {
    basket: s.basket,
    setBasket: s.setBasket,
    addTicker: s.addTicker,
    removeTicker: s.removeTicker,
    toggleTicker: s.toggleTicker,
    resetBasket: s.resetBasket,
    canAdd: s.canAdd,
    canRemove: s.canRemove,
    sectorOf: s.sectorOf,
  };
}

/** The Ichimoku file of one ticker, loaded on first use. `data` is null while loading or when the file is missing. */
export function useIchimoku(ticker: string | null | undefined): { data: Ichimoku | null; loading: boolean } {
  const { data: bundle } = useStore();
  const base = bundle?.base;
  const [state, setState] = useState<{ key: string; data: Ichimoku | null } | null>(null);
  const key = ticker && base ? `${base}/${ticker}` : "";
  useEffect(() => {
    if (!ticker || !base) return;
    let live = true;
    loadIchimoku(ticker, base).then((d) => {
      if (live) setState({ key: `${base}/${ticker}`, data: d });
    });
    return () => {
      live = false;
    };
  }, [ticker, base]);
  if (!key) return { data: null, loading: false };
  if (!state || state.key !== key) return { data: null, loading: true };
  return { data: state.data, loading: false };
}
