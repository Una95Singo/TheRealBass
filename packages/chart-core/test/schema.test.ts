import { describe, expect, it } from 'vitest';
import { CONFIDENCE_MARK, formLabel, safeParseChart } from '../src';
import { loadAllSeeds } from './fixtures';

describe('ChartSchema', () => {
  it('parses all seed charts', () => {
    const seeds = loadAllSeeds();
    expect(seeds.map((s) => s.id).sort()).toEqual([
      '12to12',
      'billiejean',
      'hecanonlyholdher',
      'holdon',
      'maniineed',
      'sinceubeengone',
      'whereismyhusband',
    ]);
    for (const s of seeds) {
      expect(s.sections.length).toBeGreaterThan(0);
      expect(s.form.length).toBeGreaterThan(0);
      expect(s.time).toBe('4/4');
    }
  });

  it('rejects a chart without sections or with a bad id', () => {
    const r1 = safeParseChart({
      schemaVersion: 1,
      id: 'x',
      title: 'T',
      artist: 'A',
      key: { display: 'C', abc: 'C' },
      bpm: 90,
      form: [],
      sections: [],
    });
    expect(r1.success).toBe(false);
    const r2 = safeParseChart({
      schemaVersion: 1,
      id: 'Bad Id',
      title: 'T',
      artist: 'A',
      key: { display: 'C', abc: 'C' },
      bpm: 90,
      form: [],
      sections: [{ letter: 'A', name: 'A', bars: [{ chords: [] }] }],
    });
    expect(r2.success).toBe(false);
  });

  it('applies defaults', () => {
    const r = safeParseChart({
      schemaVersion: 1,
      id: 'ok',
      title: 'T',
      artist: 'A',
      key: { display: 'C', abc: 'C' },
      bpm: 90,
      form: [],
      sections: [{ letter: 'A', name: 'A', bars: [{}] }],
    });
    expect(r.success).toBe(true);
    if (r.success) {
      expect(r.data.time).toBe('4/4');
      expect(r.data.sections[0]!.repeat).toBe(false);
      expect(r.data.sections[0]!.bars[0]!.chords).toEqual([]);
      expect(r.data.notes).toEqual([]);
    }
  });
});

describe('form helpers', () => {
  it('renders roadmap labels like the reference', () => {
    expect(formLabel({ label: 'Intro', bars: 10, section: 'A', confidence: 'm' })).toBe('Intro 10');
    expect(formLabel({ label: 'Ch', times: 2, section: 'D', confidence: 'l' })).toBe('Ch ×2');
    expect(formLabel({ label: 'Vamp out', section: 'A', confidence: 'l' })).toBe('Vamp out');
  });
  it('has the three marks', () => {
    expect(CONFIDENCE_MARK).toEqual({ h: '●', m: '◐', l: '○' });
  });
});
