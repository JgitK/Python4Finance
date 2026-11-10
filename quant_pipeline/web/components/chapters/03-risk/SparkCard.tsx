"use client";

// The hover card of chapter 3: a ticker, its pay and price, and a small
// chart of its daily returns. React draws the <svg>; D3 is not needed here,
// because sparkPaths gives the path strings.

import { useMemo } from "react";
import { GAIN, LOSS, COLORS, pct, signedPct } from "@/lib/theme";
import type { RiskPoint } from "./RiskReturnChart";
import { dayStats, sparkPaths } from "./spark";
import styles from "./core.module.css";

const W = 192;
const H = 40;

export function SparkCard({ point, values }: { point: RiskPoint; values: number[] }) {
  const paths = useMemo(() => sparkPaths(values, W, H), [values]);
  const days = useMemo(() => dayStats(values), [values]);
  return (
    <div className={styles.spark}>
      <div className={styles.sparkHead}>
        <span className={styles.dot} style={{ background: point.color }} aria-hidden="true" />
        <strong>{point.ticker}</strong>
        <span className={styles.sparkSector}>{point.sector}</span>
      </div>
      <div className={styles.sparkNums}>
        pay {signedPct(point.ret)} · price {pct(point.vol)}
      </div>
      <svg width={W} height={H} role="img" aria-label={`Daily returns of ${point.ticker} for ${values.length} days`}>
        <line x1={0} x2={W} y1={paths.zeroY} y2={paths.zeroY} stroke={COLORS.grid} />
        <path d={paths.up} stroke={GAIN} strokeWidth={1} />
        <path d={paths.down} stroke={LOSS} strokeWidth={1} />
      </svg>
      <div className={styles.sparkNums}>
        worst day {signedPct(days.worst, 0)} · best {signedPct(days.best, 0)}
      </div>
    </div>
  );
}
