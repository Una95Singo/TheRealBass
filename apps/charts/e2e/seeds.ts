import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseChart, type Chart } from '@lowbook/chart-core';

export const REPO_ROOT = fileURLToPath(new URL('../../..', import.meta.url));

export function loadSeeds(): Chart[] {
  const dir = join(REPO_ROOT, 'charts');
  return readdirSync(dir)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => parseChart(JSON.parse(readFileSync(join(dir, f), 'utf8'))));
}

export function pdfPageCount(pdf: Buffer): number {
  return (pdf.toString('latin1').match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
}
