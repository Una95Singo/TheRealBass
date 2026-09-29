import { z } from 'zod';

/**
 * Chart JSON: the single source of truth for a chart. Everything on the page
 * (header, form roadmap, staff, notes, numbers, footer) renders from this.
 *
 * Content rules (see PLAN.md §1): chords, form and counts only. No lyrics, no
 * melody, no note-for-note bass line.
 */

export const LETTER = /^[A-Z]$/;

/** One chord symbol printed above a given beat of a bar. */
export const ChordEventSchema = z.object({
  chord: z.string().min(1),
  /** 1-based beat within the bar (1..beats per bar). */
  beat: z.number().int().min(1),
});
export type ChordEvent = z.infer<typeof ChordEventSchema>;

/**
 * One bar of slashes. `chords` lists the symbols to PRINT in this bar; an empty
 * list means the previous chord continues and nothing is printed (Real Book
 * convention). `silent` renders an invisible rest instead of slashes, used for
 * "N.C." bars such as a drum intro.
 */
export const BarSchema = z.object({
  chords: z.array(ChordEventSchema).default([]),
  silent: z.boolean().optional(),
});
export type Bar = z.infer<typeof BarSchema>;

/** A lettered section: written once, referenced from the form roadmap. */
export const SectionSchema = z.object({
  letter: z.string().regex(LETTER),
  name: z.string(),
  /** Wrap the section in |: :| repeat bars. */
  repeat: z.boolean().default(false),
  bars: z.array(BarSchema).min(1),
});
export type Section = z.infer<typeof SectionSchema>;

/** Confidence in a bar count: h = three sources agree, m = two agree or one gives timing, l = estimate. */
export const ConfidenceSchema = z.enum(['h', 'm', 'l']);
export type Confidence = z.infer<typeof ConfidenceSchema>;

/** One entry of the roadmap across the top: "V1 16 (B) ◐". */
export const FormEntrySchema = z.object({
  label: z.string().min(1),
  bars: z.number().int().positive().optional(),
  /** "×2" style repeat count when the entry stands for several passes. */
  times: z.number().int().min(2).optional(),
  section: z.string().regex(LETTER),
  confidence: ConfidenceSchema,
});
export type FormEntry = z.infer<typeof FormEntrySchema>;

export const GivesSchema = z.enum([
  'chords',
  'beat-grid',
  'key',
  'bpm',
  'structure',
  'time',
  'year',
]);

export const SourceSchema = z.object({
  name: z.string().min(1),
  url: z.string().optional(),
  gives: z.array(GivesSchema).default([]),
  kind: z.enum(['api', 'dataset', 'pasted', 'audio', 'manual']).optional(),
  fetchedAt: z.string().optional(),
});
export type Source = z.infer<typeof SourceSchema>;

export const VerifySchema = z.object({
  /** Sources that agreed. */
  agree: z.array(z.string()).default([]),
  /** What still needs an ear. */
  check: z.array(z.string()).default([]),
  /** Optional hand-written footer text; **bold** markers allowed. When present it is printed verbatim. */
  text: z.string().optional(),
});
export type Verify = z.infer<typeof VerifySchema>;

export const KeySchema = z.object({
  /** e.g. "D major", "F# minor", "D♭ major" */
  display: z.string().min(1),
  /** ABC key signature: "D", "F#m", "Db", "Bbm" */
  abc: z.string().min(1),
  /** e.g. "Bm relative", "F# Dorian in the vamp" */
  relative: z.string().optional(),
});

export const LayoutSchema = z.object({
  barsPerLine: z.union([z.literal(4), z.literal(8)]).optional(),
});

export const ChartSchema = z.object({
  schemaVersion: z.literal(1),
  id: z.string().regex(/^[a-z0-9-]+$/),
  title: z.string().min(1),
  artist: z.string().min(1),
  year: z.number().int().optional(),
  key: KeySchema,
  bpm: z.number().positive(),
  /** Only simple x/4 metres are supported by the slash renderer for now. */
  time: z
    .string()
    .regex(/^\d+\/\d+$/)
    .default('4/4'),
  feel: z.string().optional(),
  form: z.array(FormEntrySchema),
  sections: z.array(SectionSchema).min(1),
  /** Bass notes; **bold** markers allowed. Keep to three or four. */
  notes: z.array(z.string()).default([]),
  /** Nashville / roman-numeral key, free text; newlines break lines. */
  numbers: z.string().optional(),
  verify: VerifySchema.optional(),
  sources: z.array(SourceSchema).default([]),
  layout: LayoutSchema.optional(),
});
export type Chart = z.infer<typeof ChartSchema>;
export type ChartInput = z.input<typeof ChartSchema>;

export function parseChart(input: unknown): Chart {
  return ChartSchema.parse(input);
}

export function safeParseChart(input: unknown) {
  return ChartSchema.safeParse(input);
}
