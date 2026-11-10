"use client";

// Chapter 0: the opening. The title, the money input, and a map of the walk.

import { motion } from "framer-motion";
import { MoneyInput } from "@/components/ui";
import { useStore } from "@/lib/store";
import { EASE, dollars } from "@/lib/theme";

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE } },
};
const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};

const ITINERARY = [
  { n: "01", id: "ch-01", title: "Pick the winners", line: "Start with what went up, and see how much of it is luck." },
  { n: "02", id: "ch-02", title: "Test the timing", line: "Read an Ichimoku chart for each pick." },
  { n: "03", id: "ch-03", title: "One stock is a bumpy ride", line: "Return is the pay. Volatility is the price." },
  { n: "04", id: "ch-04", title: "How they move together", line: "The bend in the curve is the free lunch." },
  { n: "05", id: "ch-05", title: "Ten thousand portfolios", line: "Throw darts, and find the edge of the cloud." },
  { n: "06", id: "ch-06", title: "Put the money in", line: "Turn weights into dollars and whole shares." },
  { n: "07", id: "ch-07", title: "How much to trust this", line: "The honest part: what the method gets wrong." },
];

export default function Opening() {
  const { amount, data, basket } = useStore();
  const stocks = data?.meta.tickers.length;
  const sectors = data?.meta.sectors.length;

  return (
    <section id="ch-00" className="opening" aria-labelledby="ch-00-title">
      <div className="da-container">
        <div className="opening-grid">
          <motion.div initial="hidden" animate="show" variants={stagger} className="opening-text">
            <motion.div variants={fadeUp}>
              <span className="eyebrow">
                <span className="pixel-check" />
                A walk through Markowitz · real S&amp;P 500 data
              </span>
            </motion.div>

            <motion.h1 id="ch-00-title" className="da-h1" variants={fadeUp}>
              Don&apos;t put all your <em>eggs</em> in one basket. But{" "}
              <span className="underline-mark">which</span> eggs, and how many in each?
            </motion.h1>

            <motion.p className="opening-lede" variants={fadeUp}>
              In 1952 Harry Markowitz turned that old proverb into arithmetic. On this page you do his method by
              hand, with real prices: pick the stocks, check the timing, see how they move together, search ten
              thousand mixes, and put{" "}
              <strong className="opening-amount" aria-live="polite">
                {dollars(amount)}
              </strong>{" "}
              to work. Then we ask the hard question: how much of the answer can you trust?
            </motion.p>

            <motion.div variants={fadeUp} className="opening-money">
              <MoneyInput variant="hero" label="How much would you invest?" />
            </motion.div>

            <motion.div variants={fadeUp} className="opening-actions">
              <a className="mac-btn primary" href="#ch-01">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M6 2v7M3 6l3 3 3-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Start with the winners
              </a>
              <a className="mac-btn" href="#ch-07">
                Skip to the honest part
              </a>
            </motion.div>

            <motion.p variants={fadeUp} className="opening-meta">
              <span>
                <span className="meta-dot" aria-hidden="true" />
                {stocks ? `${stocks} stocks · ${sectors} sectors` : "loading the data…"}
              </span>
              <span>{basket.length ? `${basket.length} in your starter basket` : ""}</span>
              <span>no sign-up · nothing leaves your browser</span>
            </motion.p>
          </motion.div>

          <motion.nav
            className="win opening-map"
            aria-label="The seven chapters"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.35 }}
          >
            <div className="titlebar">
              <span className="close-box" aria-hidden="true" />
              <span className="title-text">itinerary.md</span>
              <div className="controls">
                <span className="zoom-box" aria-hidden="true" />
              </div>
            </div>
            <ol className="itinerary">
              {ITINERARY.map((c) => (
                <li key={c.id}>
                  <a href={`#${c.id}`}>
                    <span className="it-n">{c.n}</span>
                    <span className="it-text">
                      <span className="it-title">{c.title}</span>
                      <span className="it-line">{c.line}</span>
                    </span>
                  </a>
                </li>
              ))}
            </ol>
            <p className="itinerary-foot">
              A museum corridor: the exhibit stays on the wall, and each label you pass changes what it shows.
            </p>
          </motion.nav>
        </div>
      </div>
    </section>
  );
}
