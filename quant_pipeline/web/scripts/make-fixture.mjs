// Make the fixture dataset in public/data-fixture/.
//
// The fixture is small and invented, but it has the shape of the real data
// (see lib/types.ts and docs/web_plan.md). The app uses it when
// public/data/meta.json is missing. Run: npm run fixture
//
// The prices come from a seeded factor model: one market factor, one
// factor for each sector, and noise for each stock. Thus stocks of the same
// sector move together, as real stocks do. Seed 42 gives the same files on
// each run.

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "data-fixture");
const DAYS = 252; // trading days of returns
const WARMUP = 52 + 26; // extra history for the Ichimoku lines
const AHEAD = 26; // days of the cloud ahead of the last date
const AS_OF = "2026-10-30";

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(42);
const normal = () => {
  const u = rand() || 1e-12;
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
};
const r6 = (x) => (x === null ? null : Math.round(x * 1e6) / 1e6);

// Trading dates: weekdays that end on AS_OF.
function tradingDates(count, endIso) {
  const out = [];
  const d = new Date(endIso + "T00:00:00Z");
  while (out.length < count) {
    const wd = d.getUTCDay();
    if (wd !== 0 && wd !== 6) out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return out.reverse();
}
function futureDates(count, startIso) {
  const out = [];
  const d = new Date(startIso + "T00:00:00Z");
  while (out.length < count) {
    d.setUTCDate(d.getUTCDate() + 1);
    const wd = d.getUTCDay();
    if (wd !== 0 && wd !== 6) out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

// [ticker, start price, annual drift, beta to the market, sector loading, own vol]
const UNIVERSE = {
  Energy: [
    ["XOM", 112, 0.08, 0.7, 0.9, 0.18],
    ["CVX", 151, 0.05, 0.7, 0.9, 0.19],
    ["COP", 104, 0.12, 0.8, 1.0, 0.22],
    ["EOG", 124, 0.02, 0.8, 1.0, 0.21],
    ["SLB", 41, -0.04, 0.9, 1.1, 0.27],
  ],
  Financials: [
    ["JPM", 214, 0.22, 1.0, 0.8, 0.16],
    ["GS", 512, 0.28, 1.1, 0.9, 0.2],
    ["BAC", 41, 0.15, 1.1, 0.9, 0.19],
    ["V", 298, 0.12, 0.9, 0.5, 0.15],
    ["PGR", 241, 0.18, 0.6, 0.4, 0.2],
  ],
  "Health Care": [
    ["LLY", 802, 0.32, 0.6, 0.7, 0.3],
    ["UNH", 515, -0.1, 0.6, 0.6, 0.24],
    ["JNJ", 158, 0.06, 0.5, 0.6, 0.14],
    ["ABBV", 182, 0.14, 0.6, 0.7, 0.2],
    ["ISRG", 476, 0.24, 1.1, 0.6, 0.27],
  ],
  "Information Technology": [
    ["NVDA", 128, 0.45, 1.6, 1.0, 0.38],
    ["AAPL", 226, 0.16, 1.1, 0.8, 0.2],
    ["MSFT", 418, 0.14, 1.0, 0.8, 0.18],
    ["AVGO", 168, 0.38, 1.4, 1.0, 0.33],
    ["ORCL", 165, 0.26, 1.1, 0.7, 0.29],
  ],
};
const SECTORS = Object.keys(UNIVERSE).sort();

const N = DAYS + 1 + WARMUP; // prices, one more than returns
const allDates = tradingDates(N, AS_OF);
const dt = 1 / 252;

// Factors.
const market = Array.from({ length: N }, () => 0.15 * Math.sqrt(dt) * normal() + 0.08 * dt);
const sectorF = Object.fromEntries(
  SECTORS.map((s) => [s, Array.from({ length: N }, () => 0.12 * Math.sqrt(dt) * normal())]),
);

const prices = {}; // ticker -> full price path
const meta = [];
for (const sector of SECTORS) {
  for (const [ticker, p0, mu, beta, load, vol] of UNIVERSE[sector]) {
    const path = [p0];
    for (let t = 1; t < N; t++) {
      const r = mu * dt + beta * market[t] + load * sectorF[sector][t] + vol * Math.sqrt(dt) * normal();
      path.push(path[t - 1] * (1 + r));
    }
    prices[ticker] = path;
    meta.push({ ticker, sector, lastPrice: Math.round(path[N - 1] * 100) / 100 });
  }
}
prices.SPY = [560];
for (let t = 1; t < N; t++) prices.SPY.push(prices.SPY[t - 1] * (1 + market[t] + 0.0001 * normal()));

// returns.json: the last DAYS returns. A few gaps, as in real data.
const retDates = allDates.slice(N - DAYS);
const series = {};
for (const [ticker, path] of Object.entries(prices)) {
  const r = [];
  for (let t = N - DAYS; t < N; t++) r.push(r6(path[t] / path[t - 1] - 1));
  series[ticker] = r;
}
series.ISRG[40] = null;
series.SLB[41] = null;
series.PGR[100] = null;

// leaders.json. Windows longer than the fixture use a scaled guess.
const WINDOWS = [
  { key: "1M", days: 21, effect: "Past winners tend to fall back", label: "Short-term reversal" },
  { key: "3M", days: 63, effect: "Past winners tend to continue", label: "Momentum" },
  { key: "6M", days: 126, effect: "Past winners tend to continue", label: "Momentum" },
  { key: "1Y", days: 252, effect: "Past winners tend to continue", label: "Momentum" },
  { key: "2Y", days: 504, effect: "Past winners tend to fall back", label: "Long-term reversal" },
  { key: "5Y", days: 1260, effect: "Past winners tend to fall back", label: "Long-term reversal" },
];
function windowStats(ticker, days) {
  const path = prices[ticker];
  const use = Math.min(days, DAYS);
  const end = path[N - 1];
  const start = path[N - 1 - use];
  let cum = end / start - 1;
  if (days > DAYS) cum = (1 + cum) ** (days / DAYS) - 1 + 0.05 * normal();
  const rs = [];
  for (let t = N - use; t < N; t++) rs.push(path[t] / path[t - 1] - 1);
  const m = rs.reduce((a, b) => a + b, 0) / rs.length;
  const v = rs.reduce((a, b) => a + (b - m) ** 2, 0) / (rs.length - 1);
  return { cum, vol: Math.sqrt(v * 252) };
}
const leaders = {};
const top5 = {}; // window -> Set
for (const w of WINDOWS) {
  const rows = [];
  for (const sector of SECTORS) {
    const ranked = UNIVERSE[sector]
      .map(([ticker]) => ({ ticker, ...windowStats(ticker, w.days) }))
      .sort((a, b) => b.cum - a.cum);
    ranked.forEach((s, i) => {
      const half = 1.96 * s.vol * Math.sqrt(w.days / 252);
      rows.push({
        ticker: s.ticker,
        sector,
        rank: i + 1,
        cumReturn: r6(s.cum),
        annualVol: r6(s.vol),
        rangeLow: r6(s.cum - half),
        rangeHigh: r6(s.cum + half),
        stable: false,
      });
    });
  }
  leaders[w.key] = rows;
  top5[w.key] = new Set(rows.map((r) => r.ticker));
}
// Five stocks in each sector means that all are top 5. Mark the stocks of
// rank 1 or 2 on 3M, 6M and 1Y as stable, so the ring has some use.
const near = (key) => new Set(leaders[key].filter((r) => r.rank <= 2).map((r) => r.ticker));
const stable = [...near("3M")].filter((t) => near("6M").has(t) && near("1Y").has(t));
for (const w of WINDOWS) for (const r of leaders[w.key]) r.stable = stable.includes(r.ticker);

// ichimoku/<T>.json for three tickers.
function ichimoku(ticker) {
  const path = prices[ticker];
  const mid = (t, len) => {
    if (t - len + 1 < 0) return null;
    let hi = -Infinity;
    let lo = Infinity;
    for (let i = t - len + 1; i <= t; i++) {
      hi = Math.max(hi, path[i]);
      lo = Math.min(lo, path[i]);
    }
    return (hi + lo) / 2;
  };
  const first = N - DAYS; // the first shown day
  const total = DAYS + AHEAD;
  const dates = [...allDates.slice(first), ...futureDates(AHEAD, AS_OF)];
  const out = { close: [], conversion: [], base: [], spanA: [], spanB: [], lagging: [] };
  for (let k = 0; k < total; k++) {
    const t = first + k; // index in the full path; t >= N is the future
    const real = t < N;
    out.close.push(real ? r6(path[t]) : null);
    out.conversion.push(real ? r6(mid(t, 9)) : null);
    out.base.push(real ? r6(mid(t, 26)) : null);
    const src = t - 26; // the spans are moved 26 days ahead
    const a = src >= 0 && src < N ? (mid(src, 9) + mid(src, 26)) / 2 : null;
    out.spanA.push(r6(a));
    out.spanB.push(src >= 0 && src < N ? r6(mid(src, 52)) : null);
    out.lagging.push(t + 26 < N ? r6(path[t + 26]) : null);
  }
  const last = DAYS - 1;
  const close = out.close[last];
  const cloudTop = Math.max(out.spanA[last], out.spanB[last]);
  const signals = {
    priceAboveCloud: close > cloudTop,
    conversionAboveBase: out.conversion[last] > out.base[last],
    // The lagging line of 26 days ago is today's close. Compare it with the
    // close of 26 days ago.
    laggingAbovePrice: close > out.close[last - 26],
  };
  const score = Object.values(signals).filter(Boolean).length;
  return { ticker, dates, ...out, score, signals };
}

mkdirSync(join(OUT, "ichimoku"), { recursive: true });
const write = (name, obj) => writeFileSync(join(OUT, name), JSON.stringify(obj));
write("meta.json", {
  asOf: AS_OF,
  universe: "sp500",
  riskFree: 0.045,
  tradingDays: 252,
  windows: WINDOWS,
  sectors: SECTORS,
  tickers: meta.sort((a, b) => a.ticker.localeCompare(b.ticker)),
  benchmark: "SPY",
});
write("leaders.json", leaders);
write("returns.json", { dates: retDates, series });
const rank1 = leaders["1Y"].filter((r) => r.rank === 1).map((r) => r.ticker);
for (const t of rank1) write(join("ichimoku", `${t}.json`), ichimoku(t));
write("scorecard.json", {
  windows: 85,
  holdDays: 180,
  inSampleSharpe: 5.32,
  realizedSharpe: 0.88,
  rows: [
    { name: "Optimizer", meanSharpe: 0.78, medianExcess: 0.0705, winReturn: 0.635, winSharpe: 0.506, note: "Fixture value." },
    { name: "Equal weight", meanSharpe: 0.88, medianExcess: 0.0501, winReturn: null, winSharpe: null, note: "Fixture value." },
    { name: "SPY", meanSharpe: 0.8, medianExcess: null, winReturn: null, winSharpe: null, note: "Fixture value." },
    { name: "Random order", meanSharpe: 0.62, medianExcess: 0.0022, winReturn: 0.506, winSharpe: 0.471, note: "Fixture value." },
  ],
  perWindow: [
    { date: "2025-02-10", portfolioReturn: -0.008, benchmarkReturn: 0.136, portfolioSharpe: -0.27, benchmarkSharpe: 0.69 },
    { date: "2025-08-12", portfolioReturn: 0.107, benchmarkReturn: 0.118, portfolioSharpe: 0.66, benchmarkSharpe: 0.99 },
    { date: "2026-02-11", portfolioReturn: 0.045, benchmarkReturn: 0.112, portfolioSharpe: 0.12, benchmarkSharpe: 0.88 },
  ],
});
console.log(`Wrote ${OUT}: ${meta.length} tickers, ${DAYS} days, ichimoku for ${rank1.join(", ")}.`);
