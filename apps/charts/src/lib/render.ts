/** The abcjs options the reference page uses, locked in one place. */
export const RENDER_OPTIONS = {
  responsive: 'resize',
  scale: 0.78,
  paddingtop: 0,
  paddingbottom: 0,
  paddingleft: 0,
  paddingright: 0,
  add_classes: true,
  format: {
    partsfont: 'Architects Daughter 13 box',
    gchordfont: 'Architects Daughter 13',
  },
} as const;

/**
 * abcjs (6.4.4 and 6.7.1) prints a part's boxed letter again at the start of
 * every later staff line once that part contains a repeat. Each letter is
 * written once per chart, so keeping the first box per letter is exact.
 */
export function dedupePartLabels(root: HTMLElement): void {
  const seen = new Set<string>();
  for (const el of Array.from(root.querySelectorAll('.abcjs-part'))) {
    const text = el.textContent?.trim() ?? '';
    if (seen.has(text)) el.remove();
    else seen.add(text);
  }
}

/** "key of D", "key of F# minor" — as the reference derives it from the ABC key. */
export function keyName(abcKey: string): string {
  return abcKey.replace(/m$/, ' minor');
}
