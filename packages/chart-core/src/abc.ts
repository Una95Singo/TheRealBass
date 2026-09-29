import type { Bar, Chart, Section } from './schema';

/**
 * Chart JSON → ABC (the dialect abcjs renders as slash notation).
 *
 * For the seven seed charts the output must equal the ABC the reference page
 * (reference/bcg-band-bass-charts.html) builds, minus its `%%barsperstaff`
 * line. That equality is pinned by test/golden.test.ts; change this file only
 * with that test green.
 *
 * Dialect summary (see reference/README.md):
 *   X:n / M:4/4 / L:1/4 / Q:1/4=bpm / K:<key> clef=bass style=rhythm
 *   P:A                         boxed rehearsal letter
 *   "D"D,, "Em"D,, D,, D,, |    a bar: four quarter slashes, chords before the slash they sit on
 *   D,, D,, D,, D,, |           continuation bar (previous chord carries on)
 *   "N.C."x4 |                  silent bar (invisible whole rest)
 *   |: ... :|                   section repeat; the last bar of the tune ends with |]
 * Line breaks are explicit: one source line is one staff line (abcjs's
 * default). `%%barsperstaff` is deliberately NOT used: it makes abcjs ignore
 * the source lines and it counts a leading `|:` as a bar, which pushes the last
 * bar of every repeated section onto the next line.
 * A blank line would end the tune, so none is ever emitted.
 */

export const SLASH = 'D,,';

export interface AbcOptions {
  /** Bars per staff line. Default 4 (the reference layout). */
  barsPerLine?: 4 | 8;
  /** Tune index for the X: field. Default 1. */
  x?: number;
  /**
   * Render only sections[from, to). Used to split a long chart across pages.
   * The final |] is written only when the range reaches the chart's last section.
   */
  range?: { from: number; to: number };
}

/** Beats per bar for a simple x/4 time signature. Throws for anything else. */
export function beatsPerBar(time: string): number {
  const m = /^(\d+)\/(\d+)$/.exec(time);
  if (!m) throw new Error(`invalid time signature "${time}"`);
  const [, num, den] = m;
  if (den !== '4') throw new Error(`unsupported time signature "${time}": only x/4 is supported`);
  const beats = Number(num);
  if (beats < 1 || beats > 12) throw new Error(`unsupported time signature "${time}"`);
  return beats;
}

/** One bar, without its trailing bar line. */
export function barToAbc(bar: Bar, beats: number): string {
  if (bar.silent) {
    const text = bar.chords[0]?.chord;
    return (text !== undefined ? `"${text}"` : '') + `x${beats}`;
  }
  const byBeat = new Map<number, string>();
  for (const c of bar.chords) {
    if (c.beat > beats)
      throw new Error(`chord "${c.chord}" on beat ${c.beat} of a ${beats}-beat bar`);
    byBeat.set(c.beat, c.chord);
  }
  const cells: string[] = [];
  for (let b = 1; b <= beats; b++) {
    const chord = byBeat.get(b);
    cells.push((chord !== undefined ? `"${chord}"` : '') + SLASH);
  }
  return cells.join(' ');
}

export interface SectionAbcOptions {
  barsPerLine: number;
  beats: number;
  /** Last section of the tune: its final bar line is |] instead of |. */
  isLast: boolean;
}

/** A section as ABC source lines: the P: line followed by the music lines. */
export function sectionToAbcLines(section: Section, opts: SectionAbcOptions): string[] {
  const { barsPerLine, beats, isLast } = opts;
  const lines: string[] = [`P:${section.letter}`];
  const total = section.bars.length;
  for (let start = 0; start < total; start += barsPerLine) {
    const chunk = section.bars.slice(start, start + barsPerLine);
    const firstLine = start === 0;
    const lastLine = start + barsPerLine >= total;
    const cells = chunk.map((bar, j) => {
      const finalBar = lastLine && j === chunk.length - 1;
      const barline = finalBar && section.repeat ? ':|' : finalBar && isLast ? '|]' : '|';
      return `${barToAbc(bar, beats)} ${barline}`;
    });
    lines.push((firstLine && section.repeat ? '|: ' : '') + cells.join(' '));
  }
  return lines;
}

export function abcHeader(chart: Chart, opts: AbcOptions = {}): string[] {
  return [
    `X:${opts.x ?? 1}`,
    `M:${chart.time}`,
    `L:1/4`,
    `Q:1/4=${chart.bpm}`,
    `K:${chart.key.abc} clef=bass style=rhythm`,
  ];
}

/** Staff lines a section takes at a given bars-per-line (without the P: row). */
export function sectionLineCount(section: Section, barsPerLine: number): number {
  return Math.ceil(section.bars.length / barsPerLine);
}

/** The whole tune (or a section range of it). Ends with one newline; never contains a blank line. */
export function chartToAbc(chart: Chart, opts: AbcOptions = {}): string {
  const barsPerLine = opts.barsPerLine ?? chart.layout?.barsPerLine ?? 4;
  const beats = beatsPerBar(chart.time);
  const from = opts.range?.from ?? 0;
  const to = opts.range?.to ?? chart.sections.length;
  if (from < 0 || to > chart.sections.length || from >= to)
    throw new Error(`invalid section range ${from}..${to} for ${chart.sections.length} sections`);
  const lines = abcHeader(chart, opts);
  chart.sections.slice(from, to).forEach((section, i) => {
    lines.push(
      ...sectionToAbcLines(section, {
        barsPerLine,
        beats,
        isLast: from + i === chart.sections.length - 1,
      }),
    );
  });
  return lines.join('\n') + '\n';
}
