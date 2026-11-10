"use client";

import { MotionConfig } from "framer-motion";
import type { ReactNode } from "react";
import { StoreProvider } from "@/lib/store";

/** The client providers: the store, and the reduced-motion rule for framer-motion. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <StoreProvider>{children}</StoreProvider>
    </MotionConfig>
  );
}
