import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { REPO_ROOT, loadSeeds, pdfPageCount } from './seeds';

const seeds = loadSeeds();

async function openChart(page: Page, id: string, query = '') {
  await page.goto(`/chart/${id}${query}`);
  await page.waitForFunction(() => document.fonts.status === 'loaded');
  // The first sheet settles once the fit-to-page pass has decided a layout.
  const first = page.locator('main.sheet').first();
  await expect(first).toHaveAttribute('data-fit', /^(single-\d|split-\d-\d+)$/);
  return first;
}

test.describe('Real Book page', () => {
  for (const chart of seeds) {
    test.describe(chart.title, () => {
      test('staff matches the reference render (reference layout)', async ({ page }) => {
        await openChart(page, chart.id, '?fit=0');
        const svg = page.locator('.staff svg');
        await expect(svg).toHaveCount(1);
        // Exact SVG markup first: same ABC, same abcjs, same fonts must give the same drawing.
        const expected = readFileSync(
          join(REPO_ROOT, 'reference', 'baseline', `${chart.id}-staff.svg`),
          'utf8',
        );
        expect(await svg.evaluate((el) => el.outerHTML)).toBe(expected);
        // Then the pixels, with the SVG snapped to a whole-pixel top as in the baseline.
        await svg.evaluate((el) => {
          const top = el.getBoundingClientRect().top;
          (el as HTMLElement).style.position = 'relative';
          (el as HTMLElement).style.top = `${Math.floor(top) - top}px`;
        });
        await expect(svg).toHaveScreenshot(`${chart.id}-staff.png`);
      });

      test('one rehearsal box per section', async ({ page }) => {
        await openChart(page, chart.id);
        const letters = await page.locator('.abcjs-part').allTextContents();
        expect(letters.map((t) => t.trim())).toEqual(chart.sections.map((s) => s.letter));
      });

      test('fits its pages and prints on exactly that many', async ({ page }) => {
        const first = await openChart(page, chart.id);
        const claimed = Number(await first.getAttribute('data-pages'));
        expect([1, 2]).toContain(claimed);
        const sheets = page.locator('main.sheet');
        await expect(sheets).toHaveCount(claimed);
        // Every sheet must fit one Letter page on screen (same geometry as print).
        const heights = await sheets.evaluateAll((els) =>
          els.map((el) => (el as HTMLElement).offsetHeight),
        );
        for (const h of heights) expect(h).toBeLessThanOrEqual(11 * 96 + 0.5);
        await page.emulateMedia({ media: 'print' });
        const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
        expect(pdfPageCount(pdf)).toBe(claimed);
      });
    });
  }

  test('the index lists every seed in book order', async ({ page }) => {
    await page.goto('/');
    const titles = await page.locator('.index ol li a').allTextContents();
    expect(titles).toEqual([
      '12 to 12',
      'Billie Jean',
      'Hold On',
      'Since U Been Gone',
      'Man I Need',
      'He Can Only Hold Her',
      'Where Is My Husband!',
    ]);
  });

  test('the print view has one page per sheet', async ({ page }) => {
    await page.goto('/print');
    await page.waitForFunction(() => document.fonts.status === 'loaded');
    const sheets = page.locator('main.sheet');
    await expect(page.locator('main.sheet[data-fit="pending"]')).toHaveCount(0, {
      timeout: 30_000,
    });
    const count = await sheets.count();
    await page.emulateMedia({ media: 'print' });
    const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
    expect(pdfPageCount(pdf)).toBe(count);
  });
});
