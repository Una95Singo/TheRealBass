import { beatsPerBar } from './abc';
import { LETTER, type Chart } from './schema';

export interface LintResult {
  /** Problems that would render wrongly or not at all. */
  errors: string[];
  /** Things worth a look that still render. */
  warnings: string[];
}

/** Content and consistency rules on a parsed chart. */
export function lintChart(chart: Chart): LintResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  let beats = 4;
  try {
    beats = beatsPerBar(chart.time);
  } catch (e) {
    errors.push((e as Error).message);
  }

  const letters = new Map<string, Chart['sections'][number]>();
  for (const s of chart.sections) {
    if (letters.has(s.letter)) errors.push(`section letter ${s.letter} is used twice`);
    letters.set(s.letter, s);
    s.bars.forEach((bar, i) => {
      const seen = new Set<number>();
      for (const c of bar.chords) {
        if (c.beat > beats)
          errors.push(
            `${s.letter} bar ${i + 1}: "${c.chord}" is on beat ${c.beat} of a ${beats}-beat bar`,
          );
        if (seen.has(c.beat)) errors.push(`${s.letter} bar ${i + 1}: two chords on beat ${c.beat}`);
        seen.add(c.beat);
        if (c.chord.includes('"'))
          errors.push(`${s.letter} bar ${i + 1}: chord "${c.chord}" contains a quote`);
      }
      if (bar.silent && bar.chords.length > 1)
        errors.push(`${s.letter} bar ${i + 1}: a silent bar can carry at most one text`);
    });
  }

  const referenced = new Set<string>();
  for (const f of chart.form) {
    const s = letters.get(f.section);
    if (!s) {
      errors.push(`form entry "${f.label}" points at section ${f.section}, which does not exist`);
      continue;
    }
    referenced.add(f.section);
    if (f.bars !== undefined) {
      const written = s.bars.length;
      const played = s.repeat ? written * 2 : written;
      if (f.bars !== written && f.bars !== played)
        warnings.push(
          `form entry "${f.label} ${f.bars}" does not match section ${f.section} (${written} bars written${s.repeat ? `, ${played} with the repeat` : ''})`,
        );
    }
  }
  for (const letter of letters.keys()) {
    if (!referenced.has(letter))
      warnings.push(`section ${letter} is never referenced from the form`);
    if (!LETTER.test(letter)) errors.push(`section letter "${letter}" must be a single capital`);
  }
  if (chart.notes.length > 4)
    warnings.push(`${chart.notes.length} bass notes; less is more (aim for three)`);
  if (!chart.form.length) warnings.push('no form roadmap');

  return { errors, warnings };
}

const HEADER_ORDER = ['X:', 'M:', 'L:', 'Q:', 'K:'];

/**
 * The ABC dialect rules abcjs needs for a slash chart. Returns error strings;
 * empty means the tune obeys the dialect.
 */
export function lintAbc(abc: string): string[] {
  const errors: string[] = [];
  if (!abc.endsWith('\n')) errors.push('tune must end with a newline');
  const lines = abc.replace(/\n$/, '').split('\n');

  lines.forEach((line, i) => {
    if (line.trim() === '') errors.push(`blank line at ${i + 1} would end the tune`);
    if (/\t/.test(line)) errors.push(`tab character on line ${i + 1}`);
    if (/\s$/.test(line)) errors.push(`trailing whitespace on line ${i + 1}`);
  });

  HEADER_ORDER.forEach((prefix, i) => {
    if (!lines[i]?.startsWith(prefix)) errors.push(`line ${i + 1} must start with ${prefix}`);
  });
  const k = lines[4] ?? '';
  if (!/^K:\S+ clef=bass style=rhythm$/.test(k))
    errors.push('K: must be "K:<key> clef=bass style=rhythm"');
  if (!/^L:1\/4$/.test(lines[2] ?? '')) errors.push('L: must be 1/4');

  const body = lines.slice(HEADER_ORDER.length);
  if (!body.length) errors.push('tune has no body');
  const parts = new Set<string>();
  let opens = 0;
  let closes = 0;
  body.forEach((line, j) => {
    const n = HEADER_ORDER.length + j + 1;
    if (line.startsWith('%%barsperstaff')) {
      errors.push(
        `line ${n}: %%barsperstaff is not allowed (it ignores source line breaks and miscounts |:); break lines explicitly`,
      );
      return;
    }
    if (line.startsWith('%%')) {
      errors.push(`line ${n}: directive "${line}" is not part of the dialect`);
      return;
    }
    if (line.startsWith('P:')) {
      const letter = line.slice(2);
      if (!LETTER.test(letter))
        errors.push(`line ${n}: part label "${letter}" must be a single capital`);
      if (parts.has(letter)) errors.push(`line ${n}: part ${letter} appears twice`);
      parts.add(letter);
      return;
    }
    if (line.startsWith('|:')) opens++;
    if (line.endsWith(':|')) closes++;
    const isLast = j === body.length - 1;
    if (isLast) {
      if (!line.endsWith('|]')) errors.push(`line ${n}: the last line must end with |]`);
    } else if (!/(\||:\|)$/.test(line) || line.endsWith('|]')) {
      errors.push(`line ${n}: every music line must end with a bar line (| or :|)`);
    }
  });
  if (opens !== closes) errors.push(`unbalanced repeats: ${opens} "|:" vs ${closes} ":|"`);
  if (!parts.size) errors.push('no P: part labels');
  return errors;
}
