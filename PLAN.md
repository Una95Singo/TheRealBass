# Plan: TheRealBass → "Low Book" (working title: Real Book for Bass)

Status: **awaiting your go.** Nothing in the repo has been refactored. This file and
nothing else is new on the branch.

Written after reading the handoff, the whole repo, your site repos (`singolab-com`,
`robot-to-red-light`), and the reference chart page, and after rendering the reference
in headless Chromium here to check the ABC dialect empirically.

---

## 0. What I found (facts, before opinions)

**The reference HTML.** It was not in the repo. It is your Claude artifact
"BCG Band — bass charts" (updated today), plus the single-song draft "12 to 12 — bass
chart (draft 3)". I pulled it, saved it locally, and rendered it with abcjs 6.4.4
from npm in headless Chromium (cdnjs is blocked from this container, npm is not):

- All 7 tunes parse with **zero abcjs warnings**. `K:<key> clef=bass style=rhythm`,
  `L:1/4`, `%%barsperstaff 4`, `P:` boxed parts, `"Chord"` annotations, `|:` `:|`
  repeats and `x4` invisible rests all render. The dialect is sound.
- **Bug in the reference:** once a part contains a `|:` … `:|` repeat, abcjs re-emits
  the boxed part letter at the start of *every later staff line* (labels come out
  A, B, B, B, C, B, C, …). That is the row of stray "B" boxes down the left of
  "12 to 12", "Billie Jean" and "Since U Been Gone". I reproduced it in isolation
  and it is **still present in abcjs 6.7.1** (current latest). Charts without repeats
  ("He Can Only Hold Her") are clean. Fix options are in §4.
- **"One song per Letter page" does not hold in the reference.** At Letter width the
  staff block alone is taller than a page for 6 of the 7 songs ("12 to 12" is ~2
  pages; only "He Can Only Hold Her" fits). Under `responsive:"resize"` the abcjs
  `scale` option has **no effect** on height; the levers that work are bars per
  source line (4 → 8) and `staffwidth`. Measured on "12 to 12" at print width:
  bars/line 4 → 8 and staffwidth 740 → 1100 together give roughly the 2.3×
  compaction needed. Design consequence in §4.

**The repo.** ~2,100 lines: FastAPI backend (Demucs → Basic Pitch → music21 →
VexFlow), React/Vite frontend, a synthetic eval harness, committed eval artifacts.
The default branch is `claude/general-session-SsMKd`; this branch is identical to it.
There is no ABC or music21-notation code to reuse; music21 was only used for
quantisation.

**Your hosting.** `singolab.com` is a Next.js static export on **Cloudflare Pages**,
deployed from `main` by the Cloudflare git integration. `drive.singolab.com`
(robot-to-red-light) is a **Vite + React + TS** app deployed as its **own Pages
project** (build `npm run build`, output `dist`, no env vars). The domain is at
Cloudflare Registrar with Cloudflare DNS. So `charts.singolab.com` as a third Pages
project is the zero-novelty path. Detail and the Pages-vs-Workers question in §3.4.

**Your setlist.** The Notion connector can see your workspace but no song/setlist
database (searched titles, "setlist", "sombr", "12 to 12", band pages; listed
private pages). Either the database is not shared with the Notion integration or it
lives elsewhere. Phase 2's bulk-paste input covers it either way; see §7.

**Toolchain here.** Node 22, npm 10, Python 3.11, Playwright Chromium. npm, Google
Fonts and GitHub reach fine through the proxy; cdnjs and singolab.com do not.

---

## 1. Answers to your four questions

### 1.1 What is reusable, what gets archived

| Keep (and where it goes) | Why |
|---|---|
| `backend/isolate.py` (Demucs wrapper) | Phase 4 audio module, unchanged |
| `backend/segment.py` → `_cluster_ids_to_labels` + its tests | Phase 4: turns per-bar cluster ids into A/B/C runs with short-run merging. Exactly the "audio as one more source for structure" job |
| `backend/quantize_snap.py` + tests | Phase 4: snap detected chord changes to the beat grid |
| `backend/chords.py` (pitch-class / key parsing, diatonic naming) | Port the idea to TS for the "In numbers" box (or use a library, see §3.5) |
| `backend/main.py` upload guards (MIME allow-list, 250 MB streaming cap, path-traversal check) | Pattern for the Phase 4 upload endpoint |
| `frontend/e2e` Playwright setup | Pattern for the new e2e/visual tests |

Everything else is archived: `transcribe.py` (Basic Pitch), `octave_check.py` (CREPE),
`confidence.py`, `analyze.py`, `rhythm_log.py`, the `eval/` harness and corpora,
`artifacts/` (eval runs, rhythm logs, PNGs), `NotationRenderer.jsx` (VexFlow),
`MidiPlayer.jsx`, upload/processing views, `scripts/*.sh`, `requirements.txt`.

Mechanism: tag the current head `v0-transcriber`, then delete those paths from the
tree in Phase 1. Git keeps them; the tag makes them one command away; nothing gets
refactored. The Phase 4 keepers are pulled back from the tag when (if) Phase 4 starts,
so until then the repo contains no Python at all.

### 1.2 Which model providers offer real OAuth to third-party apps

_Being verified right now by independent agents against the vendors' current docs
(each verdict is then attacked by two sceptics). This table is filled in from those
results before this plan is committed._

| Provider | OAuth for an unaffiliated web app? | Fallback | Browser-direct calls with the user's key? |
|---|---|---|---|
| Anthropic | pending | pending | pending |
| OpenAI | pending | pending | pending |
| OpenRouter | pending | pending | pending |
| Ollama (local / cloud) | pending | pending | pending |
| Google Gemini (for completeness) | pending | pending | pending |

Design rule regardless of the outcome: **no fake OAuth.** A provider gets an OAuth
button only if its own docs describe a flow for third-party apps; otherwise it gets
a paste-your-key field, stored client-side only (see §3.3).

### 1.3 Can source gathering be done politely

_Same process: one agent per site reads only robots.txt, the terms page and any
official API docs (never chord content), gives a verdict, and a second agent tries to
refute it. Filled in before commit._

| Source | Gives | Official API? | Terms on automated access | Verdict |
|---|---|---|---|---|
| Ultimate Guitar | chords | pending | pending | pending |
| Chordify | chords + beat grid, key, bpm | pending | pending | pending |
| GuitarTuna / Yousician | chords | pending | pending | pending |
| Songsterr | tabs, tempo | pending | pending | pending |
| E-Chords | chords | pending | pending | pending |
| Chordie | chords (aggregator) | pending | pending | pending |
| Hooktheory / TheoryTab | numerals + structure, key | pending | pending | pending |
| Yalp | chords + timing, key, bpm | pending | pending | pending |
| GetSongBPM | bpm, key, time sig | pending | pending | pending |
| SongBPM | bpm, key | pending | pending | pending |
| Tunebat | bpm, key | pending | pending | pending |
| MusicBrainz | canonical metadata, year | pending | pending | pending |
| Deezer API | bpm, duration, year | pending | pending | pending |
| Spotify audio-features | tempo, key, sections | pending | pending | pending |
| Open datasets (Chordonomicon, McGill Billboard, Isophonics) | chords, some structure | pending | pending | pending |

Rules that apply whatever the verdicts: official API first; identify ourselves with
a real User-Agent and contact URL; one request per second per host at most; cache
every lookup for 30 days so a song is fetched once, not once per render; never
store or display a source's chord text, only the normalised evidence and a link
back; a site whose terms forbid automated access is dropped and named in this
table, not worked around.

### 1.4 Hosting recommendation

**Static app:** a third Cloudflare Pages project (or the Workers static-assets
equivalent if Pages is now legacy for new projects; agents are checking the
September 2026 state), root directory `apps/charts`, build `npm run build`, output
`dist`, custom domain `charts.singolab.com`. Because the zone is on Cloudflare the
dashboard creates the CNAME itself. This is exactly how `drive.singolab.com` is set
up, so there is nothing new to learn or pay for. You create the project (Cloudflare
auth stays with you, as in your other repos); I supply the settings and the repo
layout it expects.

**Thin backend:** one Cloudflare Worker (`workers/api`) for source lookups: it fetches
the approved APIs/pages with a polite User-Agent, caches results in Workers KV, and
enforces a per-IP rate limit. Free tier is more than enough for one person and a
17-song setlist. If the provider research confirms browser-direct calls (§1.2), the
**model call skips the backend entirely**: the browser talks to the provider with
the user's own key, and the Worker never sees a model key.

**Audio module (Phase 4 only):** cannot run on Workers. Cheapest sensible home is a
container that scales to zero (Fly.io machine or Modal), or run locally with the
flag on. Decided only if Phase 4 happens.

Subdomain vs `/charts` path: subdomain. A path would mean building into the Next.js
site's export or proxying, both more moving parts than a second project.

---

## 2. The product in one paragraph

A song title + artist in, one printable Real Book page out. The page is chords over
slashes on a bass-clef staff, boxed rehearsal letters, a form roadmap with bar counts
and ●◐○ confidence marks, key/tempo/feel, a "bass notes" box, a Nashville key, and a
footer naming which sources agreed and what still needs an ear. No lyrics, no
melody, no note-for-note line. The rendering is the reference page, byte-for-byte on
the ABC and pixel-matched on the CSS; the AI's only job is turning cross-checked
public evidence into that page's JSON.

Name proposal: **Low Book** (a Real Book for the low end; your site already says
"Low end, on the weekends"). Alternatives: *Bottom Line*, *Slash Book*. Used below as
the package name `lowbook`; trivial to rename.

---

## 3. Architecture

### 3.1 Shape

```
lowbook/                          (this repo, renamed when you say so)
  apps/charts/        Vite + React + TypeScript SPA → charts.singolab.com
  packages/chart-core/ pure TS: Chart JSON schema (zod), chartToAbc(), ABC lint,
                       Nashville numbers, cross-check maths. Zero DOM. 100% unit-tested.
  workers/api/        Cloudflare Worker (Hono): source adapters, cache, rate limit
  charts/             seed Chart JSON, one file per song (7 from the reference)
  prompts/            versioned prompt files: system.v1.md, generate.v1.md, …
  reference/          bcg-band-bass-charts.html frozen + golden ABC per song + baseline PNGs
  audio/              empty until Phase 4 (README pointing at tag v0-transcriber)
  .github/workflows/  ci.yml (lint, typecheck, unit, visual), deploy-worker.yml
  DECISIONS.md  PLAN.md  README.md
```

npm workspaces, TypeScript everywhere, vitest for units, Playwright for the visual
check, ESLint + Prettier, conventional commits.

### 3.2 The two pure transforms (the part you want never to regress)

`chartToAbc(chart, {barsPerLine = 4})` in `chart-core`. Golden test: for each of the
seven seed songs, the output must equal the ABC string the reference page builds
for that song (I can dump those strings from the reference itself, so the goldens
are the reference, not my reading of it). Think of it as a click track for the
renderer: if the new code drifts even a bar, the test stops. A second test file
encodes the dialect rules as assertions on any chart: header lines present and in
order, `K:` carries `clef=bass style=rhythm`, no blank line inside the tune, every
section's bar count matches its `form` entry, part letters unique, repeats
balanced.

ABC → SVG is abcjs itself; we pin the version and lock the render options in one
place. A Playwright test renders each seed chart and compares against the baseline
PNG from the reference (pixel diff with a small tolerance), so a CSS or abcjs change
that alters the look fails CI.

### 3.3 Bring-your-own-model

```ts
interface ModelProvider {
  id: 'anthropic' | 'openai' | 'openrouter' | 'ollama';
  auth: { kind: 'oauth-pkce' } | { kind: 'api-key' };
  listModels(): Promise<string[]>;
  generateJson(req: { system: string; user: string; schema: JsonSchema }): Promise<unknown>;
}
```

Credentials live in the browser only (IndexedDB, wrapped with WebCrypto under a
passphrase you set once per device); nothing is stored server-side, there is no
user database. Providers that permit browser-direct calls are called from the
browser; a provider that blocks CORS goes through a stateless Worker pass-through
that forwards the user's key per request and stores nothing. Which providers land
in which column is settled by §1.2.

Prompts are files in `prompts/` with a version in the name; the system prompt carries
the §1 content rules (slashes only, no lyrics or melody, confidence marks are given
to the model, not invented by it, footer names real sources).

### 3.4 Source gathering and cross-check

Each approved source is a `SourceAdapter` returning normalised evidence:

```ts
type Evidence = { source: string; url: string; gives: ('chords'|'beat-grid'|'key'|'bpm'|'structure')[];
  key?: string; bpm?: number; timeSig?: string;
  sections?: { label: string; bars?: number; chords?: string[] }[] };
```

`crossCheck(evidence[])` in `chart-core` is pure and unit-tested: key by majority
after enharmonic normalisation; bpm by clustering within ±2 (half/double-time
detected and flagged); section bar counts get `h` when three sources agree, `m`
when two agree or one source has a beat grid, `l` otherwise. That is your ●◐○ rule
as code, so the marks on the page come from arithmetic on real agreement counts.
The model then sees the evidence plus the agreement table and writes the Chart
JSON; the JSON is validated against the schema and the confidence fields are
overwritten by the computed ones before rendering. The footer's "agree" and "check"
lists are built from the same table.

### 3.5 Chart JSON

Your schema from the handoff, plus `schemaVersion`, an optional per-chart
`layout: { barsPerLine?: 4 | 8 }` hint, and `sources[].fetchedAt`. The
"numbers" line stays a string (author-editable) but Phase 3 generates it from the
chords with a small roman-numeral helper (library choice being checked: `tonal`
vs hand-rolled, judged on slash-chord and borrowed-chord support).

---

## 4. Two renderer decisions I need to make in Phase 1 (flagging now)

**Part-label bug.** Options, in order of preference: (a) keep standard `P:` fields
and, after render, drop any `.abcjs-part` box that is not the first occurrence of
its letter, with a unit test asserting one box per section; (b) emit boxed `"^A"`
annotations instead of `P:` (renders, no duplication, but the box position drifts
relative to the chord symbol); (c) report upstream and carry a patch. I will do (a)
and file (c). If side-by-side shows (a) changes spacing, I switch to (b).

**One page per song.** The reference does not achieve it; the thesis requires it.
Proposed policy: render at the reference layout (4 bars/line); if the page overflows,
step down through 8 bars/line for sections of 8+ identical bars, then a larger
`staffwidth` (smaller staff on paper) down to a legibility floor (chord symbols no
smaller than ~11 pt printed). If it still does not fit, the chart prints on two
pages with a "2 pp." mark in the header rather than shrinking further. This is the
one place I am changing something visible relative to the reference, so it is a
question for you (§7), not a decision.

---

## 5. Phases (each shippable, each ends with a deploy)

**Phase 1: renderer.** Tag `v0-transcriber`; delete archived paths; scaffold the
monorepo; `chart-core` with schema, `chartToAbc`, ABC lint, tests; seven seed JSONs
in `charts/` converted from the reference (see the rights note in §7); golden ABC and
baseline PNGs in `reference/`; `apps/charts` renders a list of the seed charts with
the reference CSS, self-hosted Architects Daughter and Nunito Sans (as your site
self-hosts its fonts), print CSS at Letter, fit-to-page policy from §4; CI green;
you create the Pages project and it goes live at `charts.singolab.com`.
Acceptance: golden tests pass, visual diff vs reference within tolerance for all 7,
browser print of a chart is one page for the songs the policy can fit.

**Phase 2: library.** IndexedDB library (`idb`), add/edit/delete, a form editor
plus a raw JSON editor with live schema validation, bulk paste ("Title — Artist"
per line, one stub chart each), export/import of the whole library as JSON, one
route per chart, print one or print all. No backend.

**Phase 3: generation.** `workers/api` with adapters for the approved sources only,
KV cache, rate limit; `crossCheck`; `ModelProvider` with the four implementations
and the settings screen (OAuth buttons only where §1.2 says yes); `prompts/v1`;
the generate flow shows the evidence table before it calls the model, then the
rendered chart with real confidence marks and a real footer; "generate all" for a
pasted setlist. Acceptance: the seven seed songs regenerate to charts whose form,
key and bpm agree with the seeds, and every mark on the page is traceable to a
row in the evidence table.

**Phase 4: audio, flagged, default off.** Only if you ask after 1–3 are solid.
Keepers come back from the tag into `audio/` as a separate Python package with
extras (`pip install lowbook-audio[demucs]`), reachable behind `VITE_FEATURE_AUDIO`
and a separate deploy target; it emits one more `Evidence` object with its own
weight and never a note-for-note line.

Order of commits inside each phase: scaffold → pure code + tests → UI → deploy
config → docs. Short commits, conventional messages, a DECISIONS.md entry per
non-obvious call.

---

## 6. Decisions I am making myself (going into DECISIONS.md at Phase 1 start)

- Vite + React + TypeScript for the app, matching `drive.singolab.com`; no Astro
  (no content pages to justify it).
- npm workspaces, vitest, zod, Hono on Workers, `idb`, ESLint + Prettier.
- abcjs pinned to 6.4.4 for reference parity in Phase 1; upgrade attempted as a
  separate commit once the visual test exists.
- Print via the browser print dialog and `@page { size: letter }`; the old
  jsPDF + svg2pdf export is dropped (the reference already prints correctly).
- Keys client-side only; no accounts, no server storage of anything per user.
- Old code is deleted behind a tag, not moved to an `archive/` folder.
- Fonts self-hosted; no runtime request to Google Fonts (same policy as your site).
- `charts.singolab.com`, not `singolab.com/charts`.

---

## 7. Things I need from you (only these)

1. **Go / no-go** on the plan, and the name.
2. **One page per song:** confirm the §4 policy (shrink through two steps, then
   allow "2 pp."), or tell me one page is absolute and I will shrink further.
3. **Rights check on one seed note.** The Billie Jean "bass notes" entry in the
   reference spells the riff pitch by pitch ("F#–C#–E–F#–E–C#–B–C# in 8ths"). That
   is a note-for-note line, which §1 rules out. When I convert the seeds to JSON I
   will rewrite it as a description of the shape and role (two-bar ostinato under
   the F#m/G#m vamp, same shape from B under Bm7) unless you tell me to keep it.
   Everything else in the seven charts is chords, root motion and feel, which is
   inside the line you drew.
4. **The 17-song setlist.** Paste it as "Title — Artist" lines (Phase 2's bulk
   input takes exactly that), or share the Notion database with the Notion
   integration so I can pull it.
5. **Cloudflare:** when Phase 1 is ready to deploy, create the Pages project
   pointing at this repo (I will give you the five settings) and add
   `charts.singolab.com` as its custom domain.
