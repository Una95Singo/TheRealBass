import { parseChart, type Chart } from '@lowbook/chart-core';

/**
 * Phase 1: the library is the seed charts bundled from charts/*.json.
 * Phase 2 replaces this with the browser-side library.
 */
const modules = import.meta.glob('../../../../charts/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, unknown>;

/** Book order of the seed songs (the reference page's order). Unknown ids go after, by title. */
const BOOK_ORDER = [
  '12to12',
  'billiejean',
  'holdon',
  'sinceubeengone',
  'maniineed',
  'hecanonlyholdher',
  'whereismyhusband',
];

function rank(chart: Chart): number {
  const i = BOOK_ORDER.indexOf(chart.id);
  return i === -1 ? BOOK_ORDER.length : i;
}

export const charts: Chart[] = Object.values(modules)
  .map((json) => parseChart(json))
  .sort((a, b) => rank(a) - rank(b) || a.title.localeCompare(b.title));

export function findChart(id: string): Chart | undefined {
  return charts.find((c) => c.id === id);
}

/** 1-based position in the book, used for the ABC X: field. */
export function bookIndex(chart: Chart): number {
  return charts.indexOf(chart) + 1;
}
