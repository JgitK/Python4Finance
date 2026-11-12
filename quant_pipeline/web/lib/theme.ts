// The palette as JS constants for D3, the data colour scales, and the
// shared number formatters.
//
// The CSS tokens in app/globals.css have the same values. Use the CSS
// variables in React styles and these constants inside D3 code.
//
// The colour rules (from the dataviz skill):
// - A colour follows the entity (the sector), never its rank.
// - Never use colour alone. Add a label, a sign or a shape.
// - Text uses the ink colours, never the series colour.

import * as d3 from "d3";

// ─── Palette ─────────────────────────────────────────────────────────────────

export const COLORS = {
  bg: "#F9F9F9",
  paper: "#FFFFFF",
  paper2: "#FBFAF8",
  ink: "#2F2A26",
  inkSoft: "#5E554E",
  /** Muted text: ink at 66%. */
  inkMuted: "rgba(47, 42, 38, 0.66)",
  paneTabTop: "#E1EFF7",
  paneBorder: "#C0D5E0",
  lineSoft: "#E7E4E0",
  tan: "#C0A18C",
  tanDeep: "#8A6A54",
  peach: "#FCD0B1",
  clay: "#E3A881",
  sage: "#7A978A",
  sageDeep: "#498359",
  moss: "#5F7A6E",
  stone: "#A8A29E",
  /** Grid lines and axis domain lines. */
  grid: "#E7E4E0",
} as const;

/** A gain. Pair it with a "+" sign or an up arrow. */
export const GAIN = COLORS.sageDeep;
/** A loss (a clay red). Pair it with a "−" sign or a down arrow. */
export const LOSS = "#B5553C";
/** Neutral data: SPY, the benchmark, the random cloud before colour. */
export const NEUTRAL = COLORS.stone;

/** Gain or loss colour by the sign of x. 0 counts as a gain. */
export const signColor = (x: number): string => (x < 0 ? LOSS : GAIN);

// ─── Motion ──────────────────────────────────────────────────────────────────

/** The ease of the site, for framer-motion. */
export const EASE = [0.22, 1, 0.36, 1] as const;
/** The same ease for d3-transition. */
export const d3Ease = (t: number): number => {
  // A cubic bezier (0.22, 1, 0.36, 1), solved for y at x = t.
  const cx = 3 * 0.22;
  const bx = 3 * (0.36 - 0.22) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * 1;
  const by = 3 * (1 - 1) - cy;
  const ay = 1 - cy - by;
  let x = t;
  for (let i = 0; i < 6; i++) {
    const fx = ((ax * x + bx) * x + cx) * x - t;
    const dx = (3 * ax * x + 2 * bx) * x + cx;
    if (Math.abs(dx) < 1e-6) break;
    x -= fx / dx;
  }
  return ((ay * x + by) * x + cy) * x;
};
/** Milliseconds. Use 0 when the reader prefers reduced motion. */
export const DURATION = { short: 400, medium: 500, long: 600 } as const;

// ─── Sectors ─────────────────────────────────────────────────────────────────

/**
 * 11 categorical colours, one for each GICS sector, in the sorted order of
 * meta.sectors. Muted earth and water tones that sit with sage, tan and
 * clay. The order was searched to keep neighbours apart. The dataviz
 * validator gives, on white: all in the lightness band, chroma >= 0.10,
 * worst adjacent CVD ΔE 13.5, worst adjacent normal ΔE 24.8, all >= 3:1
 * contrast. 11 hues cannot all be far apart (any two can sit side by side
 * in a scatter), so always label the dots or show the sector name.
 */
export const SECTOR_PALETTE = [
  "#979031", // olive
  "#3164a3", // slate blue
  "#b5812f", // ochre
  "#5e58a1", // indigo
  "#709a58", // leaf
  "#7c4d90", // plum
  "#42a07c", // jade
  "#904572", // mulberry
  "#19a0a0", // teal
  "#934d2c", // rust
  "#1d9ac0", // sky
] as const;

/** The 11 GICS sectors in sorted order. meta.sectors overrides this when it differs. */
export const GICS_SECTORS = [
  "Communication Services",
  "Consumer Discretionary",
  "Consumer Staples",
  "Energy",
  "Financials",
  "Health Care",
  "Industrials",
  "Information Technology",
  "Materials",
  "Real Estate",
  "Utilities",
] as const;

/** Short names for chips and tight axes. */
export const SECTOR_SHORT: Record<string, string> = {
  "Communication Services": "Comms",
  "Consumer Discretionary": "Cons. Disc.",
  "Consumer Staples": "Staples",
  Energy: "Energy",
  Financials: "Financials",
  "Health Care": "Health",
  Industrials: "Industrials",
  "Information Technology": "Tech",
  Materials: "Materials",
  "Real Estate": "Real Estate",
  Utilities: "Utilities",
};
export const sectorShort = (s: string): string => SECTOR_SHORT[s] ?? s;

/**
 * The colour of a sector. A GICS sector always gets the same colour,
 * whatever sectors the data holds. Another name gets a slot by its place
 * in `sectors`, or stone.
 */
export function sectorColor(sector: string, sectors: readonly string[] = GICS_SECTORS): string {
  const g = (GICS_SECTORS as readonly string[]).indexOf(sector);
  if (g >= 0) return SECTOR_PALETTE[g];
  const i = sectors.indexOf(sector);
  return i >= 0 ? SECTOR_PALETTE[i % SECTOR_PALETTE.length] : NEUTRAL;
}

/** A d3 ordinal scale: sector name -> colour. */
export function sectorScale(sectors: readonly string[] = GICS_SECTORS): d3.ScaleOrdinal<string, string, string> {
  return d3
    .scaleOrdinal<string, string, string>()
    .domain(sectors as string[])
    .range(sectors.map((s) => sectorColor(s, sectors)))
    .unknown(NEUTRAL as string);
}

// ─── Sequential: Sharpe ratio ────────────────────────────────────────────────

/** Light stone to deep sage. One hue family, light to dark. */
export const SHARPE_RANGE = ["#D3CEC8", "#A8A29E", "#7A978A", "#498359", "#2C5A3A"] as const;

/** Interpolate t in [0, 1] from light stone to deep sage. */
export const sharpeInterpolator = d3.interpolateRgbBasis(SHARPE_RANGE as unknown as string[]);

/** A sequential scale for the Sharpe ratio. Values out of the domain clamp to the ends. */
export function sharpeScale(domain: [number, number]): d3.ScaleSequential<string> {
  return d3.scaleSequential(sharpeInterpolator).domain(domain).clamp(true);
}

// ─── Diverging: correlation ──────────────────────────────────────────────────

/** -1 is sage (moves apart: diversifies), 0 is a warm paper grey, +1 is clay (moves together). */
export const CORR_NEG = "#3F7A57";
export const CORR_MID = "#F1EEEA";
export const CORR_POS = "#B8683A";

/** A diverging scale for a correlation in [-1, 1]. */
export function correlationScale(): d3.ScaleDiverging<string> {
  return d3
    .scaleDiverging<string>()
    .domain([-1, 0, 1])
    .interpolator(d3.piecewise(d3.interpolateLab, [CORR_NEG, CORR_MID, CORR_POS]))
    .clamp(true);
}

/** Ink or white text for a fill, by the fill lightness. */
export function textOn(fill: string): string {
  const c = d3.lab(fill);
  return c.l > 62 ? COLORS.ink : "#FFFFFF";
}

// ─── Formatters ──────────────────────────────────────────────────────────────

const MINUS = "−";
const fix = (s: string) => s.replace("-", MINUS);

/** 0.1834 -> "18.3%". */
export const pct = (x: number, digits = 1): string =>
  Number.isFinite(x) ? fix(`${(x * 100).toFixed(digits)}%`) : "–";

/** 0.1834 -> "+18.3%", -0.05 -> "−5.0%". */
export const signedPct = (x: number, digits = 1): string =>
  Number.isFinite(x) ? (x > 0 ? "+" : "") + pct(x, digits) : "–";

const usd0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** 10000 -> "$10,000". digits 2 -> "$10,000.00". */
export const dollars = (x: number, digits: 0 | 2 = 0): string =>
  Number.isFinite(x) ? fix((digits === 2 ? usd2 : usd0).format(x)) : "–";

/** 12500 -> "$12.5k", 2_300_000 -> "$2.3M". */
export const dollarsCompact = (x: number): string => {
  if (!Number.isFinite(x)) return "–";
  const a = Math.abs(x);
  const s = a >= 1e6 ? `$${(a / 1e6).toFixed(1)}M` : a >= 1e3 ? `$${(a / 1e3).toFixed(1)}k` : `$${a.toFixed(0)}`;
  return (x < 0 ? MINUS : "") + s;
};

/** A plain number with a sign: 0.42 -> "+0.42". */
export const signed = (x: number, digits = 2): string =>
  Number.isFinite(x) ? (x > 0 ? "+" : "") + fix(x.toFixed(digits)) : "–";

/** A number with fixed digits and a true minus sign. */
export const num = (x: number, digits = 2): string => (Number.isFinite(x) ? fix(x.toFixed(digits)) : "–");

/** A Sharpe ratio: 2 digits. */
export const sharpeFmt = (x: number): string => num(x, 2);

/** A share count: whole shares with no digits, a fraction with up to 4. */
export const sharesFmt = (x: number): string =>
  Number.isInteger(x) ? x.toLocaleString("en-US") : x.toLocaleString("en-US", { maximumFractionDigits: 4 });
