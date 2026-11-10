# markowitz.walk

A scrollytelling page that teaches Markowitz portfolio theory with real
S&P 500 data. The brief is `../docs/web_plan.md`. Read it first.

Next.js 16.2.4 (App Router), React 19, TypeScript, Tailwind 4, D3 v7,
framer-motion, Vitest. **Next 16 has breaking changes: read the guide in
`node_modules/next/dist/docs/` before you write code** (see `AGENTS.md`).

## Run

```sh
npm install
npm run dev            # http://localhost:3000
npm run build          # static build
npx vitest run         # the math tests
npx tsc --noEmit       # the type check
npm run fixture        # make public/data-fixture/ again
```

The page loads `public/data/` (written by `quant/export_web.py`). When
`public/data/meta.json` is missing, it loads `public/data-fixture/` and
shows a "fixture data" badge in the menu bar. Add `?data=fixture` to the
URL to force the fixture.

## Folder map

```
app/
  layout.tsx            fonts (Cascadia Code as --font-mono), metadata
  page.tsx              menu bar, chapter 0, chapters 1-7, footer, tray
  providers.tsx         StoreProvider + framer-motion reduced-motion rule
  globals.css           theme tokens, .win/.titlebar/.mac-btn/..., scrolly, tray
components/
  MenuBar.tsx, Footer.tsx
  scrolly/              Scrolly, Step, Pane, Chapter, useChartSize, usePrefersReducedMotion
  ui/                   BasketTray, WindowPicker, MoneyInput, Tooltip, SectorLegend, TickerChip, FixtureBadge
  chapters/
    00-opening/         chapter 0 (finished)
    01-pick/ ... 07-trust/   one folder for each chapter (index.tsx is the default export)
    StubReadout.tsx     the stub pane body; delete its use when a chapter is real
lib/
  types.ts              the data contract
  data.ts               fetch + cache the JSON (chapters do not call it)
  portfolio.ts          the math, pure functions
  portfolio.test.ts     Vitest
  store.tsx             the shared state (React context)
  theme.ts              colours for D3, scales, formatters
scripts/make-fixture.mjs
public/data/            real data (data agent)
public/data-fixture/    small invented data with the same shape
```

## The rule: React owns the DOM, D3 owns the inside

React makes every element of the page, the `<svg>` and `<canvas>`
elements too. D3 calculates (scales, shapes, layouts) and may draw
**only inside** one `<svg>` or `<canvas>` through a ref. Do not let React
and D3 change the same node.

```tsx
const ref = useRef<SVGGElement>(null);
const [box, { width, height }] = useChartSize();
useEffect(() => {
  if (!ref.current || width === 0) return;
  const x = d3.scaleLinear().domain([0, 0.6]).range([0, width]);
  d3.select(ref.current).call(d3.axisBottom(x));   // D3 owns the inside of <g>
}, [width]);
return <div ref={box} className="pane-fill"><svg width={width} height={height}><g ref={ref} /></svg></div>;
```

For motion, check `usePrefersReducedMotion()`: when true, use a duration
of 0 and show the end state.

## Scrolly API (`@/components/scrolly`)

```tsx
<Chapter id="ch-05" number={5} title={<>Ten thousand <em>portfolios</em></>} intro="Optional line.">
  <Scrolly
    pane={(active) => (
      <Pane title="frontier.canvas" controls={<button className="pane-btn">Replay</button>}>
        <FrontierChart step={active} />
      </Pane>
    )}
  >
    <Step>Text of step 0.</Step>
    <Step label="Try it">Text of step 1.</Step>
  </Scrolly>
</Chapter>
```

- `Scrolly` props: `pane` (node or `(activeStep) => node`), `children`
  (the `Step`s, each direct child is one step), `id?`, `onStepChange?`,
  `paneLabel?`, `className?`.
- `Step` props: `children`, `label?`, `className?`.
- `Pane` props: `title` (a file name), `controls?` (title bar, right),
  `footer?`, `children`, `className?`, `bodyClassName?`, `ariaLabel?`.
  The body is a flex column with the pane height. Put the chart in a
  `div.pane-fill` and measure it with `useChartSize()`.
- `useScrolly()` → `{ activeStep, stepCount }` inside a Scrolly.
- `useChartSize<T>()` → `[ref, { width, height }]` (ResizeObserver).
- `usePrefersReducedMotion()` → `boolean`.
- Layout: steps 40% left, pane 60% right, sticky at `top: 84px`. Under
  940px the pane pins to the top (50vh) and the steps scroll under it.
  The active step is the step card nearest the band in the middle of the
  viewport (at 71% height on a phone, under the pane).

Shared CSS classes: `.win`, `.titlebar`, `.mac-btn`, `.pane-btn`,
`.chip-btn` (`.on`), `.pane-select`, `.pane-check`, `.eyebrow`, `.da-h1`,
`.da-h2`, `.underline-mark`, `.mono`/`.num`, `.gain`, `.loss`.

## Store API (`@/lib/store`)

`useStore()` returns:

| Field | Type |
|---|---|
| `status`, `error` | `"loading" \| "ready" \| "error"`, `string \| null` |
| `data` | `DataBundle \| null` (`meta`, `leaders`, `returns`, `scorecard`, `source`, `base`) |
| `isFixture`, `riskFree`, `tradingDays` | `boolean`, `number`, `number` |
| `basket` | `string[]`, canonical order: by sector, then ticker |
| `windowKey`, `amount`, `fractional` | `WindowKey`, `number`, `boolean` |
| `selectedPortfolio` | `"maxSharpe" \| "minVol" \| "equal" \| number` (a cloud index) |
| `setBasket`, `addTicker`, `removeTicker`, `toggleTicker`, `resetBasket` | basket actions (limits 2 … 15) |
| `setWindowKey`, `setAmount`, `setSelectedPortfolio`, `setFractional` | setters |
| `canAdd`, `canRemove` | `boolean` |
| `sectorOf(t)`, `priceOf(t)` | lookups from `meta.tickers` |
| `leaders` | `Leader[]` of the current window |
| `defaultBasket` | `string[]` |
| `stats` | `BasketStats \| null`: `tickers`, `sectors`, `prices`, `aligned`, `meanDaily`, `covDaily`, `correlation`, `annualReturn`, `annualVol`, `years`, `benchmark` |
| `mc` | `MonteCarloResult \| null` (10,000 portfolios, seed 42) |
| `frontier` | `FrontierPoint[]` |
| `portfolios` | `{ maxSharpe, minVol, equal }: NamedPortfolio` or `null` |
| `selected` | `NamedPortfolio \| null` |

Index every derived array with `stats.tickers` (a basket ticker with no
returns is left out). Other hooks: `useBasket()`, `useIchimoku(ticker)` →
`{ data, loading }`. Constants: `BASKET_MIN`, `BASKET_MAX`,
`WINDOW_KEYS`, `MC_PORTFOLIOS`, `MC_SEED`, `AMOUNT_MIN`, `AMOUNT_MAX`.
