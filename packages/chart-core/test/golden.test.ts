import { describe, expect, it } from 'vitest';
import { chartToAbc } from '../src';
import { loadGolden, loadSeed, referenceOrder } from './fixtures';

/**
 * The click track: for every seed song, Chart JSON → ABC must equal, byte for
 * byte, the ABC string the reference page builds for that song, with one
 * documented difference: the reference's `%%barsperstaff 4` line is dropped
 * (it makes abcjs ignore source line breaks and miscount `|:`; see
 * reference/README.md). Everything else is identical.
 */
const withoutDirective = (abc: string) => abc.replace(/^%%barsperstaff \d+\n/m, '');
describe('chartToAbc reproduces the reference ABC', () => {
  const ids = referenceOrder();

  it('covers all seven reference songs', () => {
    expect(ids).toHaveLength(7);
  });

  it('the goldens really do carry the directive we strip', () => {
    for (const id of ids) expect(loadGolden(id)).toMatch(/^%%barsperstaff 4$/m);
  });

  ids.forEach((id, i) => {
    it(`${id} (X:${i + 1})`, () => {
      const chart = loadSeed(id);
      expect(chartToAbc(chart, { x: i + 1 })).toBe(withoutDirective(loadGolden(id)));
    });
  });
});
