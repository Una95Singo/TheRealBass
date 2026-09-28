import type { Confidence, FormEntry } from './schema';

/** ● three sources agree, ◐ two agree or one gives timing, ○ estimate. */
export const CONFIDENCE_MARK: Record<Confidence, string> = { h: '●', m: '◐', l: '○' };

/** "Intro 10", "Ch ×2", "Vamp out" — the text shown in the roadmap. */
export function formLabel(entry: FormEntry): string {
  let s = entry.label;
  if (entry.bars !== undefined) s += ` ${entry.bars}`;
  if (entry.times !== undefined) s += ` ×${entry.times}`;
  return s;
}

/** Bars a section occupies when played once through its written repeat. */
export function playedBars(bars: number, repeat: boolean): number {
  return repeat ? bars * 2 : bars;
}
