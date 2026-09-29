import { describe, expect, it } from 'vitest';
import { chartToAbc, lintAbc, lintChart, parseChart, type ChartInput } from '../src';
import { loadAllSeeds, loadGolden, referenceOrder } from './fixtures';

const base: ChartInput = {
  schemaVersion: 1,
  id: 'lint',
  title: 'Lint',
  artist: 'Test',
  key: { display: 'G major', abc: 'G' },
  bpm: 120,
  form: [{ label: 'V1', bars: 4, section: 'A', confidence: 'm' }],
  sections: [
    {
      letter: 'A',
      name: 'V1',
      bars: Array.from({ length: 4 }, () => ({ chords: [{ chord: 'G', beat: 1 }] })),
    },
  ],
};

describe('seeds', () => {
  it('lint clean (no errors) as charts and as ABC', () => {
    for (const chart of loadAllSeeds()) {
      const { errors } = lintChart(chart);
      expect(errors, chart.id).toEqual([]);
      expect(lintAbc(chartToAbc(chart)), chart.id).toEqual([]);
    }
  });
  it('the reference goldens obey the dialect once their barsperstaff line is dropped', () => {
    for (const id of referenceOrder()) {
      const golden = loadGolden(id);
      expect(lintAbc(golden).join('\n'), id).toMatch(/barsperstaff is not allowed/);
      expect(lintAbc(golden.replace(/^%%barsperstaff \d+\n/m, '')), id).toEqual([]);
    }
  });
});

describe('lintChart', () => {
  it('flags a chord beyond the bar', () => {
    const chart = parseChart({
      ...base,
      sections: [{ letter: 'A', name: 'V1', bars: [{ chords: [{ chord: 'G', beat: 5 }] }] }],
    });
    expect(lintChart(chart).errors.join('\n')).toMatch(/beat 5 of a 4-beat bar/);
  });
  it('flags two chords on one beat and duplicate letters', () => {
    const chart = parseChart({
      ...base,
      sections: [
        {
          letter: 'A',
          name: 'V1',
          bars: [
            {
              chords: [
                { chord: 'G', beat: 1 },
                { chord: 'C', beat: 1 },
              ],
            },
          ],
        },
        { letter: 'A', name: 'V2', bars: [{ chords: [] }] },
      ],
    });
    const { errors } = lintChart(chart);
    expect(errors.join('\n')).toMatch(/two chords on beat 1/);
    expect(errors.join('\n')).toMatch(/letter A is used twice/);
  });
  it('flags a form entry pointing at a missing section', () => {
    const chart = parseChart({
      ...base,
      form: [{ label: 'Ch', bars: 8, section: 'Z', confidence: 'l' }],
    });
    expect(lintChart(chart).errors.join('\n')).toMatch(/section Z, which does not exist/);
  });
  it('warns, not errors, when form bar counts disagree with the section', () => {
    const chart = parseChart({
      ...base,
      form: [{ label: 'V1', bars: 6, section: 'A', confidence: 'm' }],
    });
    const res = lintChart(chart);
    expect(res.errors).toEqual([]);
    expect(res.warnings.join('\n')).toMatch(/does not match section A/);
  });
  it('accepts a form count that equals the section with its repeat', () => {
    const chart = parseChart({
      ...base,
      form: [{ label: 'V1', bars: 8, section: 'A', confidence: 'm' }],
      sections: [{ ...base.sections[0]!, repeat: true }],
    });
    expect(lintChart(chart).warnings).toEqual([]);
  });
  it('rejects unsupported metres', () => {
    const chart = parseChart({ ...base, time: '6/8' });
    expect(lintChart(chart).errors.join('\n')).toMatch(/only x\/4/);
  });
});

describe('lintAbc', () => {
  const good = chartToAbc(parseChart(base));
  it('accepts a well-formed tune', () => {
    expect(lintAbc(good)).toEqual([]);
  });
  it('rejects a blank line inside the tune', () => {
    const bad = good.replace('P:A\n', 'P:A\n\n');
    expect(lintAbc(bad).join('\n')).toMatch(/blank line/);
  });
  it('rejects a K: without the rhythm style', () => {
    const bad = good.replace(' style=rhythm', '');
    expect(lintAbc(bad).join('\n')).toMatch(/style=rhythm/);
  });
  it('rejects unbalanced repeats', () => {
    const bad = good.replace('P:A\n', 'P:A\n|: ');
    expect(lintAbc(bad).join('\n')).toMatch(/unbalanced repeats/);
  });
  it('rejects the barsperstaff directive and unknown directives', () => {
    const bad = good.replace('P:A\n', '%%barsperstaff 4\nP:A\n');
    expect(lintAbc(bad).join('\n')).toMatch(/barsperstaff is not allowed/);
    const bad2 = good.replace('P:A\n', '%%stretchlast\nP:A\n');
    expect(lintAbc(bad2).join('\n')).toMatch(/not part of the dialect/);
  });
  it('rejects a last line that does not close with |]', () => {
    const bad = good.replace('|]\n', '|\n');
    expect(lintAbc(bad).join('\n')).toMatch(/must end with \|\]/);
  });
  it('rejects a missing final newline and tabs', () => {
    expect(lintAbc(good.trimEnd()).join('\n')).toMatch(/end with a newline/);
    expect(lintAbc(good.replace(' |', '\t|')).join('\n')).toMatch(/tab character/);
  });
});
