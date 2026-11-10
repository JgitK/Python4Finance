// Label placement for a labelled scatter. Pure functions, no DOM.
//
// Each dot gets one short text label (a ticker). The function tries some
// places around the dot and keeps the first place that does not touch an
// other label, an other dot, or the edge of the plot. When no place is
// free, it keeps the place with the smallest overlap.

export interface LabelInput {
  /** The dot centre, in pixels. */
  x: number;
  y: number;
  /** The label width, in pixels. */
  w: number;
}

export interface LabelPlace {
  /** The top-left corner of the label box, in pixels. */
  x: number;
  y: number;
  w: number;
  h: number;
  /** The side of the dot where the label is. */
  side: "right" | "left" | "above" | "below" | "upper-right" | "lower-right" | "upper-left" | "lower-left";
}

export interface LabelOptions {
  /** The label height, in pixels. Default 12. */
  h?: number;
  /** The dot radius plus a gap, in pixels. Default 7. */
  r?: number;
  /** The plot size. A label stays inside [0, width] × [0, height]. */
  width: number;
  height: number;
}

/** An estimate of the width of a mono label: about 0.62 em for each character. */
export function monoWidth(text: string, fontSize = 11): number {
  return Math.ceil(text.length * fontSize * 0.62);
}

function overlap(a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }): number {
  const dx = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const dy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return dx > 0 && dy > 0 ? dx * dy : 0;
}

/**
 * Place one label for each input dot. The output has the same order as
 * the input. Dots are placed in the given order, so put the most
 * important dot first.
 */
export function placeLabels(points: LabelInput[], opts: LabelOptions): LabelPlace[] {
  const h = opts.h ?? 12;
  const r = opts.r ?? 7;
  const dotBoxes = points.map((p) => ({ x: p.x - r + 2, y: p.y - r + 2, w: 2 * r - 4, h: 2 * r - 4 }));
  const placed: LabelPlace[] = [];
  const out: LabelPlace[] = [];

  points.forEach((p, i) => {
    const cands: LabelPlace[] = [
      { side: "right", x: p.x + r, y: p.y - h / 2, w: p.w, h },
      { side: "left", x: p.x - r - p.w, y: p.y - h / 2, w: p.w, h },
      { side: "above", x: p.x - p.w / 2, y: p.y - r - h, w: p.w, h },
      { side: "below", x: p.x - p.w / 2, y: p.y + r, w: p.w, h },
      { side: "upper-right", x: p.x + r - 2, y: p.y - r - h + 3, w: p.w, h },
      { side: "lower-right", x: p.x + r - 2, y: p.y + r - 3, w: p.w, h },
      { side: "upper-left", x: p.x - r - p.w + 2, y: p.y - r - h + 3, w: p.w, h },
      { side: "lower-left", x: p.x - r - p.w + 2, y: p.y + r - 3, w: p.w, h },
    ];
    let best = cands[0];
    let bestCost = Infinity;
    for (const c of cands) {
      let cost = 0;
      // The edge of the plot: a label out of bounds costs much.
      if (c.x < 0 || c.y < 0 || c.x + c.w > opts.width || c.y + c.h > opts.height) cost += 1e6;
      for (const q of placed) cost += overlap(c, q) * 10;
      dotBoxes.forEach((d, j) => {
        if (j !== i) cost += overlap(c, d) * 4;
      });
      if (cost < bestCost) {
        bestCost = cost;
        best = c;
        if (cost === 0) break;
      }
    }
    // Clamp into the plot when no place is fully inside.
    const clamped = {
      ...best,
      x: Math.min(Math.max(best.x, 0), Math.max(0, opts.width - best.w)),
      y: Math.min(Math.max(best.y, 0), Math.max(0, opts.height - best.h)),
    };
    placed.push(clamped);
    out.push(clamped);
  });
  return out;
}
