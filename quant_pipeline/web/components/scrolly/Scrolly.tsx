"use client";

/**
 * Scrolly: the museum corridor. Text steps scroll on the left (40%). One
 * sticky pane stays on the right (60%, top 84px). Under 940px wide the pane
 * pins to the top of the viewport and the steps scroll under it.
 *
 * A line in the middle of the viewport names the active step: the last
 * step whose card is above the line (on a phone the line sits below the
 * pinned pane). The pane
 * gets `activeStep` (0-based) through a render prop, and every component
 * inside the Scrolly can read it with `useScrolly()`.
 *
 * Usage:
 *
 *   import { Scrolly, Step, Pane } from "@/components/scrolly";
 *
 *   <Scrolly
 *     id="frontier"
 *     pane={(active) => (
 *       <Pane title="frontier.canvas" controls={<button className="pane-btn">Replay</button>}>
 *         <FrontierChart step={active} />
 *       </Pane>
 *     )}
 *   >
 *     <Step>Only the stocks of the basket, as in chapter 3.</Step>
 *     <Step>One random portfolio drops in.</Step>
 *     <Step>Ten thousand portfolios rain in.</Step>
 *   </Scrolly>
 *
 * Props of Scrolly:
 * - `pane`: a node, or `(activeStep: number) => ReactNode`.
 * - `children`: the <Step> elements, in order. Each direct child is one step.
 * - `id?`: an id for the section element (anchor links).
 * - `onStepChange?`: called with the new active step.
 * - `paneLabel?`: the aria-label of the pane column.
 *
 * The pane column has a fixed height (the viewport less the menu bar and
 * the tray), so a chart can fill it: use `useChartSize()` on the chart box.
 * Controls in the pane work at every step.
 */

import {
  Children,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

// ─── Contexts ────────────────────────────────────────────────────────────────

interface ScrollyState {
  /** The 0-based index of the step in the band. */
  activeStep: number;
  /** The count of steps. */
  stepCount: number;
}

interface Registry {
  register: (index: number, el: HTMLElement | null) => void;
}

const ScrollyContext = createContext<ScrollyState>({ activeStep: 0, stepCount: 0 });
const RegistryContext = createContext<Registry | null>(null);
const StepIndexContext = createContext<number>(-1);

/** The active step and the step count of the nearest Scrolly. */
export function useScrolly(): ScrollyState {
  return useContext(ScrollyContext);
}

/** The index of the Step that holds this component (-1 outside a step). */
export function useStepIndex(): number {
  return useContext(StepIndexContext);
}

// ─── Media query ─────────────────────────────────────────────────────────────

/** The breakpoint where the pane pins to the top. Keep in step with globals.css. */
export const SCROLLY_BREAKPOINT = 940;

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${SCROLLY_BREAKPOINT}px)`);
    const on = () => setNarrow(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return narrow;
}

// ─── Scrolly ─────────────────────────────────────────────────────────────────

export interface ScrollyProps {
  pane: ReactNode | ((activeStep: number) => ReactNode);
  children: ReactNode;
  id?: string;
  onStepChange?: (step: number) => void;
  paneLabel?: string;
  className?: string;
}

export function Scrolly({ pane, children, id, onStepChange, paneLabel, className }: ScrollyProps) {
  const steps = Children.toArray(children);
  const stepCount = steps.length;
  const [activeStep, setActiveStep] = useState(0);
  const elements = useRef<(HTMLElement | null)[]>([]);
  const narrow = useNarrow();
  const onChange = useRef(onStepChange);
  useEffect(() => {
    onChange.current = onStepChange;
  }, [onStepChange]);

  const registry = useMemo<Registry>(
    () => ({
      register: (index, el) => {
        elements.current[index] = el;
      },
    }),
    [],
  );

  // The playhead: a line across the viewport. The active step is the last
  // step whose card top is above the line. A scroll listener reads the
  // positions, so a jump (an anchor link) also gives the correct step, and
  // the last step stays active after it leaves the line.
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      frame = 0;
      const line = window.innerHeight * (narrow ? 0.71 : 0.5);
      let active = 0;
      for (let i = 0; i < stepCount; i++) {
        const el = elements.current[i];
        if (!el) continue;
        if (el.getBoundingClientRect().top <= line) active = i;
      }
      setActiveStep((prev) => {
        if (prev !== active) onChange.current?.(active);
        return active;
      });
    };
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [narrow, stepCount]);

  const state = useMemo(() => ({ activeStep, stepCount }), [activeStep, stepCount]);
  const paneNode = typeof pane === "function" ? pane(activeStep) : pane;

  return (
    <ScrollyContext.Provider value={state}>
      <RegistryContext.Provider value={registry}>
        <div id={id} className={`scrolly${className ? ` ${className}` : ""}`}>
          <div className="scrolly-steps">
            {steps.map((child, i) => (
              <StepIndexContext.Provider key={i} value={i}>
                {child}
              </StepIndexContext.Provider>
            ))}
          </div>
          <div className="scrolly-pane" aria-label={paneLabel} role={paneLabel ? "region" : undefined}>
            {paneNode}
          </div>
        </div>
      </RegistryContext.Provider>
    </ScrollyContext.Provider>
  );
}

// ─── Step ────────────────────────────────────────────────────────────────────

export interface StepProps {
  children: ReactNode;
  /** A small label above the text, such as "Step 2". Default: none. */
  label?: ReactNode;
  className?: string;
}

/** One text step. Put it as a direct child of <Scrolly>. */
export function Step({ children, label, className }: StepProps) {
  const index = useContext(StepIndexContext);
  const registry = useContext(RegistryContext);
  const { activeStep } = useContext(ScrollyContext);
  const ref = useCallback(
    (el: HTMLDivElement | null) => {
      registry?.register(index, el);
    },
    [registry, index],
  );
  const active = index === activeStep;
  return (
    <div className={`scrolly-step${active ? " is-active" : ""}${className ? ` ${className}` : ""}`} data-step={index}>
      {/* The observer watches the card, so a step becomes active when its text reaches the band. */}
      <div ref={ref} className="scrolly-step-card" aria-current={active ? "step" : undefined}>
        {label ? <div className="eyebrow scrolly-step-label">{label}</div> : null}
        <div className="scrolly-step-body">{children}</div>
      </div>
    </div>
  );
}
