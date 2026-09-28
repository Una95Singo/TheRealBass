import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseChart, type Chart } from '../src';

export const REPO_ROOT = resolve(__dirname, '..', '..', '..');
export const CHARTS_DIR = join(REPO_ROOT, 'charts');
export const REFERENCE_DIR = join(REPO_ROOT, 'reference');

/** Reference song order; X: numbering in the goldens follows it. */
export function referenceOrder(): string[] {
  const songs = JSON.parse(readFileSync(join(REFERENCE_DIR, 'songs.json'), 'utf8')) as {
    id: string;
  }[];
  return songs.map((s) => s.id);
}

export function loadSeed(id: string): Chart {
  return parseChart(JSON.parse(readFileSync(join(CHARTS_DIR, `${id}.json`), 'utf8')));
}

export function loadAllSeeds(): Chart[] {
  return readdirSync(CHARTS_DIR)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => parseChart(JSON.parse(readFileSync(join(CHARTS_DIR, f), 'utf8'))));
}

export function loadGolden(id: string): string {
  return readFileSync(join(REFERENCE_DIR, 'abc', `${id}.abc`), 'utf8');
}
