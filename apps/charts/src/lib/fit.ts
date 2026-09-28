import { sectionLineCount, type Chart } from '@lowbook/chart-core';

/**
 * Fit-to-page policy (PLAN.md §4, DECISIONS.md).
 *
 * 1. Reference layout: 4 bars per staff line.
 * 2. 8 bars per staff line (same staff size, same chord size, half the height).
 * 3. Still too tall: back to 4 bars per line and split the sections across two
 *    pages at a section boundary, balanced by staff-line count; the split moves
 *    one section at a time toward whichever page overflows.
 * 4. Two pages at 4 bars per line still overflow: the same split at 8 bars per
 *    line, which always has room.
 * The chart says "2 pp." in its header whenever it is split.
 *
 * The staff is never shrunk: 8 bars per line keeps every symbol at the reference
 * size, and a smaller staff is not readable on a music stand. (`scale` is not a
 * lever under abcjs's responsive resize anyway; `staffwidth` is, but it shrinks
 * the chord symbols.)
 */
export type BarsPerLine = 4 | 8;

export type Layout =
  | { kind: 'single'; barsPerLine: BarsPerLine }
  | { kind: 'split'; barsPerLine: BarsPerLine; at: number };

/**
 * On screen the sheet box is 8.5in wide and its padding equals the print page
 * margins (0.45in / 0.5in / 0.4in on Letter), so the on-screen box height that
 * still fits one printed page is 11in.
 */
export const PAGE_HEIGHT_PX = 11 * 96;

export function fitsOnePage(sheetHeightPx: number): boolean {
  return sheetHeightPx <= PAGE_HEIGHT_PX + 0.5;
}

/** Staff lines per section, counting the P: label row as one. */
function weights(chart: Chart, barsPerLine: BarsPerLine): number[] {
  return chart.sections.map((s) => sectionLineCount(s, barsPerLine) + 1);
}

/**
 * The section index at which to start page 2 so the two staff blocks are as
 * even as possible (page 1 also carries the header and form, page 2 the notes).
 */
export function balancedSplit(chart: Chart, barsPerLine: BarsPerLine = 4): number {
  const w = weights(chart, barsPerLine);
  const total = w.reduce((a, b) => a + b, 0);
  let best = 1;
  let bestDiff = Infinity;
  let acc = 0;
  for (let k = 1; k < w.length; k++) {
    acc += w[k - 1]!;
    const diff = Math.abs(acc - (total - acc));
    if (diff < bestDiff) {
      bestDiff = diff;
      best = k;
    }
  }
  return best;
}

export function firstLayout(): Layout {
  return { kind: 'single', barsPerLine: 4 };
}

export function layoutLabel(layout: Layout): string {
  return layout.kind === 'single'
    ? `single-${layout.barsPerLine}`
    : `split-${layout.barsPerLine}-${layout.at}`;
}

/**
 * Next layout to try after `current` overflowed, skipping layouts already
 * tried (so a split cannot ping-pong). Null when nothing is left: the caller
 * keeps the current layout and accepts the overflow.
 */
export function nextLayout(
  current: Layout,
  chart: Chart,
  overflow: { page1: boolean; page2: boolean },
  tried: ReadonlySet<string>,
): Layout | null {
  const n = chart.sections.length;
  const candidates: Layout[] = [];
  if (current.kind === 'single') {
    if (current.barsPerLine === 4) candidates.push({ kind: 'single', barsPerLine: 8 });
    if (n >= 2) candidates.push({ kind: 'split', barsPerLine: 4, at: balancedSplit(chart, 4) });
  } else {
    if (overflow.page1 && current.at > 1) candidates.push({ ...current, at: current.at - 1 });
    if (overflow.page2 && current.at < n - 1) candidates.push({ ...current, at: current.at + 1 });
    if (current.barsPerLine === 4)
      candidates.push({ kind: 'split', barsPerLine: 8, at: balancedSplit(chart, 8) });
  }
  return candidates.find((c) => !tried.has(layoutLabel(c))) ?? null;
}
