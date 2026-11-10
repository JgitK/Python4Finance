"use client";

import { useStore } from "@/lib/store";

/** A small badge when the page runs on the fixture data. */
export function FixtureBadge() {
  const { isFixture, status, data } = useStore();
  if (status === "loading") return <span className="data-badge">loading data…</span>;
  if (status === "error") return <span className="data-badge warn">data failed to load</span>;
  if (isFixture)
    return (
      <span className="data-badge warn" title="public/data/meta.json is missing, so the page uses public/data-fixture.">
        fixture data
      </span>
    );
  return <span className="data-badge">prices to {data?.meta.asOf}</span>;
}
