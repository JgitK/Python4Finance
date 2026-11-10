# Web plan: a scrollytelling walk through Markowitz

Status: plan, 2026-11-09. Decision D35 records the choice of Next.js.
This file is the brief for each agent that builds a part. Read all of it
before you write code.

## The aim

One web page. The reader scrolls, and the page teaches the decision
process of a diversified portfolio with the real project data. The reader
does each step by hand: pick the stocks, read the Ichimoku chart, see how
the stocks move together, run the Monte Carlo search, and put a set
amount of money into the result. The last chapter says how much to trust
the result (D34).

An analogy for the page: a museum corridor. The exhibit stays on the
wall (the sticky chart). The reader walks past the labels (the text
steps), and each label changes what the exhibit shows.

## The stack

- Next.js 16 (App Router), React 19, TypeScript, Tailwind 4. The same
  versions as the personal site of the user (`next` 16.2.4).
  **Next 16 has breaking changes. Read the guide in
  `node_modules/next/dist/docs/` before you write code.**
- D3 v7 for scales, shapes, axes and transitions. React owns the DOM
  tree. D3 calculates, and D3 owns only the inside of an `<svg>` or a
  `<canvas>` through a ref. Do not mix the two on one node.
- Canvas for the 10,000 Monte Carlo dots. SVG for all other charts.
- Vitest for the TypeScript math.
- The app is static. Python writes JSON files, and the browser does all
  interactive math. There is no server and no API.

## Where the files go

```
quant_pipeline/
  quant/export_web.py          Python: warehouse -> JSON   (data agent)
  tests/test_export_web.py     (data agent)
  web/                         the Next.js app
    app/layout.tsx, page.tsx, globals.css      (foundation agent)
    lib/types.ts               the data contract, see below (foundation)
    lib/data.ts                fetch + cache the JSON       (foundation)
    lib/portfolio.ts           the math                     (foundation)
    lib/portfolio.test.ts
    lib/store.tsx              the shared state             (foundation)
    lib/theme.ts               colors for D3                (foundation)
    components/scrolly/        Scrolly, Step, Pane          (foundation)
    components/ui/             Basket, WindowPicker, MoneyInput, Tooltip
    components/chapters/
      01-pick/                 (pick agent)
      02-ichimoku/             (pick agent)
      03-risk/                 (core agent)
      04-together/             (core agent)
      05-frontier/             (core agent)
      06-money/                (money agent)
      07-trust/                (money agent)
    public/data/               the JSON files (data agent writes them)
    public/data-fixture/       small hand-made JSON (foundation agent)
```

An agent edits only the files of its own rows. If an agent needs a
change in a file of a different owner, it writes the request in its
final report and does not edit the file.

## The theme

The source is the `claude/color-experiments` branch of the personal
site. Copy the tokens. Do not invent a second look.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#F9F9F9` | The page |
| `--paper` | `#FFFFFF` | The cards |
| `--ink` | `#2F2A26` | Text |
| `--ink-soft` | `#5E554E` | Second text, axis labels |
| `--pane-tab-top` | `#E1EFF7` | The top of a title bar |
| `--pane-border` | `#C0D5E0` | Card edges, grid lines |
| `--line-soft` | `#E7E4E0` | Soft dividers |
| `--tan` | `#C0A18C` | Accent, italic words in a heading |
| `--tan-deep` | `#8A6A54` | Eyebrow labels |
| `--peach` | `#FCD0B1` | The card shadow, the underline mark |
| `--clay` | `#E3A881` | Warm accent |
| `--sage` | `#7A978A` | Buttons, the main data color |
| `--sage-deep` | `#498359` | Hover, the selected item |
| `--moss` | `#5F7A6E` | |
| `--stone` | `#A8A29E` | Neutral data (SPY, the random cloud) |

- Font: Cascadia Code (`next/font/google`, variable `--font-mono`) for
  headings, labels, numbers and buttons. Body text is `system-ui`.
- Each chart sits in a `.win` card: white, 1px `--pane-border`, radius
  8px, shadow `6px 6px 8px var(--peach)`, and a `.titlebar` with a blue
  gradient, a small mono label, and a tan dot and a sage dot on the
  right. The title bar names the chart like a file:
  `frontier.svg`, `correlation.csv`.
- Headings: `.da-h1`, `.da-h2`, mono, weight 600, tight tracking. One
  word in italic tan (`<em>`). Eyebrow: mono, 11.5px, uppercase,
  `--tan-deep`.
- Buttons: `.mac-btn`, mono, 2px sage border, sage fill on hover.
- Light theme only. The site has no dark theme.
- Motion: ease `[0.22, 1, 0.36, 1]`, 400 to 600 ms. Obey
  `prefers-reduced-motion`: no transition, show the end state.
- Data colors: gain is `--sage-deep`, loss is `#B5553C` (a clay red).
  Never use color alone: add a sign, a label or a shape. The 11 sectors
  need 11 colors that fit the palette. The foundation agent makes them
  in `lib/theme.ts` and follows the `dataviz` skill (load it before the
  first chart).

## The shape of the page

Each chapter is a `Scrolly`: text steps in the left column (40%), one
sticky `.win` pane on the right (60%, `top: 84px`). Under 940px wide,
the pane pins to the top and the steps scroll under it, as the projects
globe does on the personal site. An `IntersectionObserver` band in the
middle of the viewport names the active step. The pane receives
`activeStep` and draws that state. Controls in a pane work at any step.

A sticky tray at the bottom of the viewport holds the **basket** (the
picked tickers as chips), the ranking window and the amount of money. It
is visible from chapter 1 to the end.

### Chapter 0: the opening

Title: "Don't put all your *eggs* in one basket. But which eggs, and how
many in each?" A money input with a default of $10,000. A short line
that says what the reader will do. No chart.

### Chapter 1: pick the winners (`01-pick`)

Pane: `leaders.svg`. One row for each sector. In each row, the top 5
stocks by cumulative return are dots on a shared x axis (the return of
the window), each with a 95% range whisker.

1. "Start where most people start: with what went up." All dots in grey.
2. The window picker comes alive (1M, 3M, 6M, 1Y, 2Y, 5Y). The dots move
   when the window changes. Text: each window measures a different
   effect. Show the label of the window (reversal, momentum, reversal).
3. The whiskers fade in. "A return of +18% over 3 months can be luck.
   The line shows the range that the true return is probably in."
4. "Now pick. Click 6 to 12 stocks." A click adds a ticker to the
   basket. A sector balance meter shows the count for each sector.
   A "pick for me" button adds the top 1 of each sector for a reader
   who wants to continue.
5. A rank-stability mark: a ring on a dot that leads on 3M, 6M and 1Y.

The page starts with a default basket (the top stock of each of 8
sectors on the 1Y window), so every later chapter works with no click.

### Chapter 2: test the timing with Ichimoku (`02-ichimoku`)

Pane: `ichimoku.svg` for one ticker of the basket. Tabs or chips switch
the ticker. The x axis is the last 12 months.

1. The close price only. "Here is one of your picks."
2. The conversion line (9 days) and the base line (26 days) draw in.
   "Fast average and slow average. Fast above slow: the trend is up."
3. The cloud (span A and span B) fills, green where A is above B and
   clay where it is below. "The cloud is support and resistance, drawn
   26 days ahead."
4. The lagging line. Then the score chip: 0 to 3 signals, with a label
   for each signal (price above cloud, conversion above base, lagging
   above price).
5. "Your turn." The reader steps through the basket and can remove a
   stock. An honest note: in the project tests, an Ichimoku gate lowered
   the result (D24). The chart is information for timing. It is not a
   filter.

### Chapter 3: one stock is a bumpy ride (`03-risk`)

Pane: `risk-return.svg`. A scatter: x is the annual volatility, y is the
annual return, one labelled dot for each stock of the basket, and SPY in
stone.

1. Only the y axis matters: the dots sit on a line by return.
2. The x axis opens. "Return is the pay. Volatility is the price." The
   dots move right by their volatility.
3. Hover a dot to see a small sparkline of its daily returns.
4. "Can we get the pay of the top dots for the price of the left dots?
   Not with one stock. With a mix, sometimes."

### Chapter 4: how they move together (`04-together`)

Two panes in order.

Pane A: `two-stocks.svg`. The reader picks two stocks of the basket. A
slider sets the weight between them. The chart draws the curve of all
mixes in risk and return space, and a dot for the slider position.

1. Two stocks, 100% in one. The dot is on that stock.
2. Move the slider. The dot follows a curve, not a straight line. "The
   bend is free. It is the only free lunch in finance."
3. A second control sets a pretend correlation from +1 to -1. At +1 the
   curve is a straight line. Lower values bend it more. Then snap back
   to the real correlation of the pair.

Pane B: `correlation.csv`. A heatmap of the basket, ordered by sector.

4. The heatmap draws. Diverging scale: clay for +1, paper for 0, sage
   for -1. The numbers show in each cell.
5. The most correlated pair gets an outline. "These two are close to
   one stock. Holding both adds less than you think."
6. The least correlated pair gets an outline. "This pair is where the
   diversification comes from." A line gives the mean correlation of
   the basket.
7. Covariance in one sentence: correlation times the two volatilities.
   A toggle changes the heatmap between correlation and covariance.

### Chapter 5: ten thousand portfolios (`05-frontier`)

Pane: `frontier.canvas`. Risk on x, return on y.

1. Only the stocks of the basket, as in chapter 3.
2. One random portfolio drops in, with its weights as a small bar.
   "Give each stock a random share of the money."
3. 10, then 100, then 10,000 dots rain in (canvas, in batches over about
   2 seconds). Color by Sharpe ratio, stone to sage-deep.
4. The upper-left edge gets a line: the efficient frontier. "No mix is
   above this line. Below it, you pay risk for nothing."
5. Three markers: minimum volatility, maximum Sharpe, equal weight.
   A click on a marker (or on any dot) shows its weights in a bar chart
   beside the cloud. The capital market line draws from the risk-free
   rate through the maximum Sharpe point.
6. The reader edits the basket in the tray and the cloud draws again
   (seed 42, so the same basket gives the same cloud).

### Chapter 6: put the money in (`06-money`)

Pane: `allocation.csv`. The selected portfolio (default: maximum Sharpe)
and the amount of money.

1. The weights as horizontal bars, by sector color.
2. The bars change to dollars, then to shares, with the last price.
3. A toggle: whole shares or fractional shares. With whole shares, show
   the cash that is left and each stock that drops out because one share
   costs more than its target. Show the smallest amount that holds every
   weight.
4. A table: ticker, sector, weight, price, shares, cost. A "copy as CSV"
   button.

### Chapter 7: how much to trust this (`07-trust`)

1. Pane `error-bars.svg`: the expected return of each stock as a range.
   "The optimizer used these as facts. They are guesses." Use the
   standard error: annual volatility divided by the square root of the
   years.
2. Pane `bootstrap.canvas`: draw the maximum Sharpe point again for 200
   bootstrap samples of the days. The points scatter. "The best mix
   moves when the data moves."
3. Pane `scorecard.svg`: the walk-forward result of the project method
   next to equal weight, SPY and the random-order null, from
   `scorecard.json`. Show it also when it is bad. In-sample Sharpe 5.32,
   realized 0.88.
4. The close: "Markowitz is a risk tool. Trust the covariance more than
   the return. Spread across sectors. Equal weight is hard to beat."
   A short "what the page did not show" list and the source links.

## The data contract

`quant/export_web.py` writes these files to `web/public/data/`. The
TypeScript types in `web/lib/types.ts` must match this section exactly.
All returns are fractions (0.18 is +18%). All dates are `YYYY-MM-DD`.
Round floats to 6 decimal places.

```ts
type WindowKey = "1M" | "3M" | "6M" | "1Y" | "2Y" | "5Y";
// trading days: 21, 63, 126, 252, 504, 1260

// meta.json
interface Meta {
  asOf: string;                 // the last price date
  universe: "sp500";
  riskFree: number;             // 0.045
  tradingDays: number;          // 252
  windows: { key: WindowKey; days: number; effect: string; label: string }[];
  sectors: string[];            // sorted
  tickers: { ticker: string; sector: string; lastPrice: number }[]; // the union
  benchmark: "SPY";
}

// leaders.json: the top 5 of each sector for each window
interface Leader {
  ticker: string;
  sector: string;
  rank: number;                 // 1 to 5 inside the sector
  cumReturn: number;            // over the window
  annualVol: number;            // from the daily returns of the window
  rangeLow: number;             // cumReturn - 1.96 * annualVol * sqrt(days/252)
  rangeHigh: number;
  stable: boolean;              // top 5 of its sector on 3M, 6M and 1Y
}
type Leaders = Record<WindowKey, Leader[]>;

// returns.json: daily simple returns, the last 504 trading days,
// for each ticker of meta.tickers and for SPY. null where a price is missing.
interface Returns {
  dates: string[];
  series: Record<string, (number | null)[]>;
}

// ichimoku/<TICKER>.json: the last 252 trading days, plus the 26 days of
// span A and span B that lie ahead of the last date.
interface Ichimoku {
  ticker: string;
  dates: string[];
  close: (number | null)[];
  conversion: (number | null)[];
  base: (number | null)[];
  spanA: (number | null)[];     // already moved 26 days ahead
  spanB: (number | null)[];
  lagging: (number | null)[];
  score: number;                // 0 to 3 on the last date
  signals: { priceAboveCloud: boolean; conversionAboveBase: boolean; laggingAbovePrice: boolean };
}

// scorecard.json: from the existing output files and docs/context.md
interface Scorecard {
  windows: number;              // 85
  holdDays: number;             // 180
  inSampleSharpe: number;
  realizedSharpe: number;
  rows: { name: "Optimizer" | "Equal weight" | "SPY" | "Random order";
          meanSharpe: number | null; medianExcess: number | null;
          winReturn: number | null; winSharpe: number | null; note: string }[];
  perWindow: { date: string; portfolioReturn: number; benchmarkReturn: number;
               portfolioSharpe: number; benchmarkSharpe: number }[];
}
```

The union of tickers in `meta.tickers` is every ticker that is in
`leaders.json` for any window.

## The math in the browser (`web/lib/portfolio.ts`)

Pure functions, no DOM, each with a Vitest test. They follow
`quant/optimize.py` and `quant/allocate.py`, so the page and the
pipeline agree.

- `alignReturns(returns, tickers)`: drop each day where a ticker is null.
- `meanVector`, `covarianceMatrix` (sample, n-1), `correlationMatrix`.
- `portfolioPerformance(weights, meanDaily, covDaily, tradingDays, riskFree)`:
  annual return, annual volatility, Sharpe ratio.
- `mulberry32(seed)`: a seeded random source. Seed 42.
- `monteCarlo(meanDaily, covDaily, n, seed)`: typed arrays of risk,
  return, Sharpe and weights. Uniform random weights divided by the sum,
  as in `random_weights`.
- `frontierHull(points)`: the upper-left edge of the cloud.
- `twoAssetCurve(meanA, meanB, volA, volB, rho, steps)`.
- `allocateWhole`, `allocateFractional`, `minimumInvestment`: as in
  `quant/allocate.py`.
- `bootstrapMaxSharpe(returns, draws, seed)`: for chapter 7.
- `standardErrorRange(annualReturn, annualVol, years)`.

## The shared state (`web/lib/store.tsx`)

One React context: `basket: string[]`, `windowKey`, `amount`,
`selectedPortfolio` (`"maxSharpe" | "minVol" | "equal" | number`),
`fractional`, and the loaded data. Derived values with `useMemo`: the
aligned returns of the basket, the mean vector, the covariance, the
Monte Carlo result. A chapter reads the store and never fetches data
itself.

## Who builds what

| Phase | Agent | Model | Work |
|---|---|---|---|
| 1 | data | Sonnet 5.5 | `export_web.py`, its tests, the JSON files |
| 1 | foundation | Opus 5.5 | The app, the theme, the scrolly parts, the store, the math, the fixture, a stub for each chapter, chapter 0 |
| 2 | core | Opus 5.5 | Chapters 3, 4 and 5 |
| 2 | pick | Sonnet 5.5 | Chapters 1 and 2 |
| 2 | money | Sonnet 5.5 | Chapters 6 and 7 |
| 3 | lead | Fable | Integration, the browser check, the commit |

Phase 1 runs the two agents at the same time. Phase 2 starts when the
foundation is done and runs its three agents at the same time.

## The rules for each agent

- TDD for the Python and for `lib/portfolio.ts`: the test first, see it
  fail, then the code. After a pass, break the code and see a test fail.
- Comments and docs in Simplified Technical English (ASD-STE100). The
  text on the page is plain English with analogies.
- Do not delete files of the repository. Do not run `git commit`,
  `git push` or `git stash`. The lead commits.
- Open the warehouse read-only. If DuckDB reports a lock, wait and try
  again. Do not run `dbt build`.
- `npm run build` and `npx vitest run` must pass before the report.
- The final report lists: the files made, the commands run with their
  result, and each thing that does not work yet.

## Done means

- `npm run build` passes and `npx vitest run` passes in `web/`.
- `pytest` passes in `quant_pipeline/` with the new tests.
- The page loads with the real data and a default basket. Each of the
  seven chapters reacts to scroll and to its controls.
- A change of the basket, the window or the amount updates each later
  chapter.
- The page is usable at 390px wide and at 1440px wide.
- No console error.
