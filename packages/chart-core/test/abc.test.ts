import { describe, expect, it } from 'vitest';
import {
  barToAbc,
  beatsPerBar,
  chartToAbc,
  parseChart,
  sectionToAbcLines,
  type ChartInput,
} from '../src';

const tiny: ChartInput = {
  schemaVersion: 1,
  id: 'tiny',
  title: 'Tiny',
  artist: 'Test',
  key: { display: 'C major', abc: 'C' },
  bpm: 100,
  form: [{ label: 'A', bars: 2, section: 'A', confidence: 'l' }],
  sections: [
    {
      letter: 'A',
      name: 'A',
      bars: [
        {
          chords: [
            { chord: 'C', beat: 1 },
            { chord: 'G', beat: 3 },
          ],
        },
        { chords: [] },
      ],
    },
  ],
};

describe('beatsPerBar', () => {
  it('accepts simple x/4 metres', () => {
    expect(beatsPerBar('4/4')).toBe(4);
    expect(beatsPerBar('3/4')).toBe(3);
  });
  it('rejects anything else for now', () => {
    expect(() => beatsPerBar('6/8')).toThrow(/only x\/4/);
    expect(() => beatsPerBar('four')).toThrow(/invalid/);
  });
});

describe('barToAbc', () => {
  it('places chords before the slash they sit on', () => {
    expect(
      barToAbc(
        {
          chords: [
            { chord: 'D', beat: 1 },
            { chord: 'Em', beat: 2 },
          ],
        },
        4,
      ),
    ).toBe('"D"D,, "Em"D,, D,, D,,');
    expect(barToAbc({ chords: [{ chord: 'Gb', beat: 4 }] }, 4)).toBe('D,, D,, D,, "Gb"D,,');
  });
  it('emits a continuation bar with no annotation', () => {
    expect(barToAbc({ chords: [] }, 4)).toBe('D,, D,, D,, D,,');
  });
  it('emits invisible rests for silent bars', () => {
    expect(barToAbc({ silent: true, chords: [{ chord: 'N.C. drums', beat: 1 }] }, 4)).toBe(
      '"N.C. drums"x4',
    );
    expect(barToAbc({ silent: true, chords: [] }, 4)).toBe('x4');
    expect(barToAbc({ silent: true, chords: [] }, 3)).toBe('x3');
  });
  it('refuses a chord beyond the bar', () => {
    expect(() => barToAbc({ chords: [{ chord: 'C', beat: 5 }] }, 4)).toThrow(/beat 5/);
  });
});

describe('sectionToAbcLines', () => {
  const bars = Array.from({ length: 6 }, (_, i) => ({
    chords: i % 2 ? [] : [{ chord: 'C', beat: 1 }],
  }));
  it('breaks lines every barsPerLine bars and closes with |] on the last section', () => {
    const lines = sectionToAbcLines(
      { letter: 'A', name: 'A', repeat: false, bars },
      { barsPerLine: 4, beats: 4, isLast: true },
    );
    expect(lines).toHaveLength(3);
    expect(lines[0]).toBe('P:A');
    expect(lines[1]!.split(' | ')).toHaveLength(4);
    expect(lines[2]).toMatch(/\|\]$/);
  });
  it('wraps a repeated section in |: and :|', () => {
    const lines = sectionToAbcLines(
      { letter: 'B', name: 'B', repeat: true, bars },
      { barsPerLine: 8, beats: 4, isLast: false },
    );
    expect(lines[1]!.startsWith('|: ')).toBe(true);
    expect(lines[1]!.endsWith(' :|')).toBe(true);
  });
  it('a repeated last section keeps :| rather than |]', () => {
    const lines = sectionToAbcLines(
      { letter: 'B', name: 'B', repeat: true, bars },
      { barsPerLine: 4, beats: 4, isLast: true },
    );
    expect(lines.at(-1)!.endsWith(' :|')).toBe(true);
  });
});

describe('chartToAbc', () => {
  it('writes the header in the dialect order', () => {
    const abc = chartToAbc(parseChart(tiny));
    expect(abc.split('\n').slice(0, 6)).toEqual([
      'X:1',
      'M:4/4',
      'L:1/4',
      'Q:1/4=100',
      'K:C clef=bass style=rhythm',
      'P:A',
    ]);
    expect(abc).not.toContain('%%');
    expect(abc.endsWith('|]\n')).toBe(true);
  });
  it('honours barsPerLine from options, then layout, then the default', () => {
    const long = parseChart({
      ...tiny,
      sections: [
        {
          letter: 'A',
          name: 'A',
          bars: Array.from({ length: 8 }, () => ({ chords: [{ chord: 'C', beat: 1 }] })),
        },
      ],
    });
    const musicLines = (abc: string) =>
      abc
        .trim()
        .split('\n')
        .filter((l) => l.startsWith('"'));
    expect(musicLines(chartToAbc(long))).toHaveLength(2);
    expect(musicLines(chartToAbc(long, { barsPerLine: 8 }))).toHaveLength(1);
    const viaLayout = parseChart({ ...long, layout: { barsPerLine: 8 } });
    expect(musicLines(chartToAbc(viaLayout))).toHaveLength(1);
    expect(musicLines(chartToAbc(viaLayout, { barsPerLine: 4 }))).toHaveLength(2);
  });
  it('renders a section range for page splits, closing with |] only at the true end', () => {
    const two = parseChart({
      ...tiny,
      sections: [
        { letter: 'A', name: 'A', bars: [{ chords: [{ chord: 'C', beat: 1 }] }] },
        { letter: 'B', name: 'B', bars: [{ chords: [{ chord: 'G', beat: 1 }] }] },
      ],
    });
    const first = chartToAbc(two, { range: { from: 0, to: 1 } });
    const second = chartToAbc(two, { range: { from: 1, to: 2 } });
    expect(first).toContain('P:A');
    expect(first).not.toContain('P:B');
    expect(first.endsWith(' |\n')).toBe(true);
    expect(second).toContain('P:B');
    expect(second.endsWith(' |]\n')).toBe(true);
    expect(() => chartToAbc(two, { range: { from: 1, to: 1 } })).toThrow(/invalid section range/);
  });
  it('never contains a blank line', () => {
    expect(chartToAbc(parseChart(tiny))).not.toMatch(/\n\n/);
  });
});
