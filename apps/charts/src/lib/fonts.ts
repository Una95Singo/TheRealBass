/**
 * abcjs measures text with whatever font is available at render time, so the
 * chord and part fonts must be loaded before the first render or the staff
 * lays out against fallback metrics and looks different after the swap.
 */
export const CHART_FONTS = [
  '13px "Architects Daughter"',
  '400 12px "Nunito Sans"',
  '700 12px "Nunito Sans"',
];

let ready: Promise<void> | undefined;

export function fontsReady(): Promise<void> {
  if (!ready) {
    ready =
      typeof document === 'undefined' || !('fonts' in document)
        ? Promise.resolve()
        : Promise.all(CHART_FONTS.map((f) => document.fonts.load(f)))
            .then(() => document.fonts.ready)
            .then(() => undefined)
            .catch(() => undefined);
  }
  return ready;
}
