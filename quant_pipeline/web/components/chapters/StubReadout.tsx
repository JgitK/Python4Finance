"use client";

/**
 * StubReadout: the body of a stub pane. It prints the active step and a
 * few live values from the store, to prove the plumbing. A chapter agent
 * replaces it with the real chart.
 */

import type { ReactNode } from "react";
import { useScrolly } from "@/components/scrolly";

export function StubReadout({ rows }: { rows: [string, ReactNode][] }) {
  const { activeStep, stepCount } = useScrolly();
  return (
    <div className="stub">
      <p className="stub-step">
        step {activeStep + 1} / {stepCount}
      </p>
      <dl className="stub-rows">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="stub-note">Stub pane. The chart of this chapter goes here.</p>
    </div>
  );
}
