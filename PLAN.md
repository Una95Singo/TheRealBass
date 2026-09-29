# Plan: TheRealBass → "Low Book" (working title: Real Book for Bass)

Status: **awaiting your go.** Nothing in the repo has been refactored. This file and
nothing else is new on the branch.

Written after reading the handoff, the whole repo, your site repos (`singolab-com`,
`robot-to-red-light`), and the reference chart page; after rendering the reference in
headless Chromium here to check the ABC dialect empirically; and after checking the
provider, source-site and hosting questions against current docs and terms pages.

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
  the boxed part letter at the start of _every later staff line_ (labels come out
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
Cloudflare Registrar with Cloudflare DNS. Detail and the Pages-vs-Workers question
in §1.4.

**Your setlist.** The Notion connector can see your workspace but no song/setlist
database (searched titles, "setlist", "sombr", "12 to 12", band pages; listed
private pages). Either the database is not shared with the Notion integration or it
lives elsewhere. Phase 2's bulk-paste input covers it either way; see §7.

**Toolchain here.** Node 22, npm 10, Python 3.11, Playwright Chromium. npm, Google
Fonts and GitHub reach fine through the proxy; cdnjs, singolab.com and most chord
sites do not.

**How the research below was done.** I started this as a fan-out of independent
agents that would each read a site's terms and then have a second agent try to
refute the verdict. That run was cut short by the account's monthly spend limit
after three verdicts (Chordify, GetSongBPM, SongBPM), so I finished the remaining
lookups myself against official docs where reachable and against search-indexed
copies of terms pages where the proxy blocked the site. Each row below says which.
Nothing here was answered from memory alone.

---

## 1. Answers to your four questions

### 1.1 What is reusable, what gets archived

| Keep (and where it goes)                                                                      | Why                                                                                                                                 |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `backend/isolate.py` (Demucs wrapper)                                                         | Phase 4 audio module, unchanged                                                                                                     |
| `backend/segment.py` → `_cluster_ids_to_labels` + its tests                                   | Phase 4: turns per-bar cluster ids into A/B/C runs with short-run merging. Exactly the "audio as one more source for structure" job |
| `backend/quantize_snap.py` + tests                                                            | Phase 4: snap detected chord changes to the beat grid                                                                               |
| `backend/chords.py` (pitch-class / key parsing, diatonic naming)                              | Port the idea to TS for the "In numbers" box                                                                                        |
| `backend/main.py` upload guards (MIME allow-list, 250 MB streaming cap, path-traversal check) | Pattern for the Phase 4 upload endpoint                                                                                             |
| `frontend/e2e` Playwright setup                                                               | Pattern for the new e2e/visual tests                                                                                                |

Everything else is archived: `transcribe.py` (Basic Pitch), `octave_check.py` (CREPE),
`confidence.py`, `analyze.py`, `rhythm_log.py`, the `eval/` harness and corpora,
`artifacts/` (eval runs, rhythm logs, PNGs), `NotationRenderer.jsx` (VexFlow),
`MidiPlayer.jsx`, upload/processing views, `scripts/*.sh`, `requirements.txt`.

Mechanism: tag the current head `v0-transcriber`, then delete those paths from the
tree in Phase 1. Git keeps them; the tag makes them one command away; nothing gets
refactored. The Phase 4 keepers are pulled back from the tag when (if) Phase 4 starts,
so until then the repo contains no Python at all.

### 1.2 Which model providers offer real OAuth to third-party apps (as of 27 Sep 2026)

| Provider       | OAuth for an unaffiliated web app?                                                                                                                                                                                                                                                      | What the app does                                                                                                                                                | Browser-direct calls with the user's own key?                                                                                                                                                                                                                                      |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Anthropic**  | **No.** Subscription OAuth (Pro/Max) was explicitly restricted to Claude Code and claude.ai on 19 Feb 2026; third-party use is a consumer-terms violation and was cut off on 4 Apr 2026. Console has no "sign in with Claude" for third parties.                                        | Paste an API key from the Console.                                                                                                                               | **Yes, with an opt-in header.** The API accepts browser requests when `anthropic-dangerous-direct-browser-access: true` is sent; the TypeScript SDK sets it via `dangerouslyAllowBrowser: true` (documented, "disabled by default to avoid exposing your secret API credentials"). |
| **OpenAI**     | **No.** "Sign in with ChatGPT" (announced May 2025) still ships only inside OpenAI's own Codex tooling; it is not offered to third-party developers and is identity sign-in, not API access on the user's plan.                                                                         | Paste an API key.                                                                                                                                                | **Yes.** The API answers browser requests; the SDK requires `dangerouslyAllowBrowser: true` and warns about key exposure.                                                                                                                                                          |
| **OpenRouter** | **Yes, real OAuth (PKCE).** Send the user to `https://openrouter.ai/auth?callback_url=…&code_challenge=…&code_challenge_method=S256`; exchange the code at `POST https://openrouter.ai/api/v1/auth/keys`; you get back a user-scoped API key. No client ID, secret or app registration. | One-click "Connect OpenRouter" button.                                                                                                                           | Yes; the flow is designed for browser apps (the key comes back to the page).                                                                                                                                                                                                       |
| **Ollama**     | n/a. Local server has no auth. Ollama cloud uses API keys (`Authorization: Bearer`, keys made at ollama.com/settings/keys).                                                                                                                                                             | Local: enter the URL; the user must add `https://charts.singolab.com` to `OLLAMA_ORIGINS` (default allows only 127.0.0.1 / 0.0.0.0 origins). Cloud: paste a key. | Local: yes once `OLLAMA_ORIGINS` includes the site (that is the documented mechanism). Cloud: bearer key; CORS to confirm at build time.                                                                                                                                           |

Sources: Anthropic policy change (Anthropic docs update 19 Feb 2026, reported by
AlternativeTo, Winbuzzer, GIGAZINE; claude-code issues #28091, #82266); Anthropic
SDK README (browser option); CORS header (Anthropic API, Aug 2024 onward); OpenAI
status (openai/codex issue #10974, help-center notes); openai-node README;
OpenRouter OAuth PKCE docs (openrouter.ai/docs/use-cases/oauth-pkce, quoted via
search since the host is blocked from here); Ollama FAQ and cloud docs
(github.com/ollama/ollama/docs).

Consequences for the design: exactly one OAuth button (OpenRouter), three paste-a-key
fields (Anthropic, OpenAI, Ollama cloud) and one URL field (Ollama local). Every
provider can be called **straight from the browser**, so the model step needs **no
backend at all**; the Worker exists only for source lookups. Gemini was not in your
list and I have not researched it.

### 1.3 Can source gathering be done politely

Rules that apply throughout: official API first; identify ourselves with a real
User-Agent and contact URL; at most one request per second per host; cache every
lookup for 30 days; never store or display a source's chord text, only the
normalised evidence and a link back; a site whose terms forbid automated access is
dropped, named, and not worked around.

| Source                            | Gives                                                                   | Verdict                                    | Why (with how it was checked)                                                                                                                                                                                                                                                                                                                                |
| --------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ultimate Guitar                   | chords (user-submitted)                                                 | **drop**                                   | Terms forbid copying, reproducing or exploiting the Service; no developer API (forum requests unanswered for years); tab pages sit behind an anti-bot challenge. (ToS via indexed copy; site blocked.)                                                                                                                                                       |
| Chordify                          | chords + beat grid, key, bpm                                            | **drop**                                   | Terms: no access "using automated means (such as harvesting bots, robots, spiders, or scrapers) without our express written permission" and no reproduction "in any form"; no public API, only an iframe embed that exposes no data. (Agent-verified from indexed ToS; site blocked.) Written permission from info@chordify.net is the only compliant route. |
| GuitarTuna / Yousician            | chords                                                                  | check                                      | App-first; no public API found. Read terms before Phase 3; default drop.                                                                                                                                                                                                                                                                                     |
| Songsterr                         | tab metadata, tempo; no chords                                          | use via API, low value                     | Keyless public JSON search API is documented on their site; secondary sources say non-commercial use is permitted (confirm the official wording, page blocked from here). Tempo/time signature only.                                                                                                                                                         |
| E-Chords, Chordie                 | chords                                                                  | check                                      | Terms not yet read (sites blocked from here). Default drop until read.                                                                                                                                                                                                                                                                                       |
| Hooktheory / TheoryTab            | numerals + structure per song                                           | **drop** for per-song data                 | The official API exposes only aggregate chord-probability "trends", not a song's TheoryTab; terms: no third party may "copy, scrape, bulk-download, text-and-data mine, or redistribute … the TheoryTab database".                                                                                                                                           |
| Yalp                              | chords + timing                                                         | check                                      | Terms not yet read.                                                                                                                                                                                                                                                                                                                                          |
| GetSongBPM                        | bpm, key, time signature                                                | **use via official API**                   | Free key, 3,000 req/hour, JSON; the one condition is a visible backlink to GetSongBPM.com; the database is stated to be CC BY 4.0. (Agent-verified from indexed API page.)                                                                                                                                                                                   |
| SongBPM                           | bpm, key                                                                | **drop**                                   | Terms: "Automated access to this Service is strictly prohibited. This includes scraping, crawling, bots, scripts, and any form of automated data collection." No API. (Agent-verified.)                                                                                                                                                                      |
| Tunebat                           | bpm, key                                                                | **drop** (unless paid API)                 | Terms forbid "any robots, spider, crawler, scraper or other automated means"; a commercial Music Metadata API exists at tunebat.com/API. Revisit only if it has a free tier.                                                                                                                                                                                 |
| MusicBrainz                       | canonical title/artist/year                                             | **use via official API**                   | Open data; documented etiquette is 1 request/second with a descriptive User-Agent. Metadata only.                                                                                                                                                                                                                                                            |
| Deezer API                        | bpm, duration, year                                                     | check, likely drop                         | Public JSON endpoints still answer without a token and carry a bpm field, but new developer app registrations are not being issued (community thread, May 2026), and the API terms assume a registered app.                                                                                                                                                  |
| Spotify audio-features / analysis | tempo, key, sections                                                    | **drop**                                   | Removed for new apps on 27 Nov 2024; restrictions tightened again Feb 2026; no replacement.                                                                                                                                                                                                                                                                  |
| Chordonomicon (Hugging Face)      | 666k progressions with section labels, genre, release date, Spotify IDs | check licence, then likely **use offline** | Built from user-generated chord repositories; per the paper the progressions themselves are non-copyrightable. The dataset licence could not be read from here (huggingface.co blocked). If permissive, this is the strongest chord + structure source we have, and it needs **no live scraping at all**.                                                    |
| McGill Billboard, Isophonics      | chords                                                                  | skip                                       | Research corpora with little coverage of a 2025 setlist.                                                                                                                                                                                                                                                                                                     |

**The honest consequence.** The two sites the reference leaned on for chords and
bar counts (Chordify for the beat grid, Ultimate Guitar for chords) are both out on
their terms. What remains programmatically is thin on chords: Chordonomicon offline
(if its licence allows) plus whichever of E-Chords / Chordie / Yalp / Yousician turn
out to permit it. Tempo, key and metadata are well covered (GetSongBPM, MusicBrainz,
Songsterr). So the ●◐○ rule will often top out at ◐ for chords from automated
sources alone. Two things keep the thesis intact without scraping:

1. **"Paste what you see" as a source.** You open a chord site yourself, in your
   browser, for your own use, and paste the progression and section list into the
   app; it is stored as one `Evidence` row tagged with that site's name and counts
   toward agreement exactly like an adapter. Personal use, no automation, and it
   keeps the footer honest ("Ultimate Guitar (pasted)").
2. **The audio module becomes worth more.** With Chordify's beat grid gone, a
   downbeat/bar counter over a recording you own is the only automated route to
   bar counts. Still flagged, still Phase 4, still one source among several, but
   it moves up in value.

### 1.4 Hosting recommendation

**What Cloudflare says now (2026):** Workers with static assets reached feature
parity with Pages for static sites, SPAs, custom domains and git-driven builds in
March 2026; Cloudflare recommends **Workers for new projects** and keeps Pages fully
supported for existing ones. (developers.cloudflare.com is blocked from here; this
is from Cloudflare's migration guide as indexed and several 2026 write-ups that
quote it.)

**Recommendation: one Cloudflare Worker with static assets**, deployed by Workers
Builds from this repo, custom domain `charts.singolab.com` (the zone is already on
Cloudflare, so the dashboard creates the DNS record). The same Worker serves the
Vite build from `apps/charts/dist` and answers `/api/*` for source lookups, so there
is one project, one domain, one deploy, and no CORS between app and backend. Free
tier (100k requests/day) is far more than one person and a 17-song setlist need.

**Fallback (zero novelty):** a third Pages project exactly like `drive.singolab.com`
plus a separate tiny Worker for `/api`. Both paths are cheap to switch between; I
will scaffold for the Worker and note the Pages settings in the README.

You create the Cloudflare project and attach the domain (Cloudflare auth stays with
you, as in your other repos); I supply the `wrangler` config and the exact dashboard
settings.

**Audio module (Phase 4 only):** cannot run on Workers. Cheapest sensible home is a
scale-to-zero container (Fly.io machine or Modal) or local-only with the flag on.
Decided only if Phase 4 happens.

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
evidence into that page's JSON.

Name proposal: **Low Book** (a Real Book for the low end; your site already says
"Low end, on the weekends"). Alternatives: _Bottom Line_, _Slash Book_. Used below as
the package name `lowbook`; trivial to rename.

---

## 3. Architecture

### 3.1 Shape

```
lowbook/                          (this repo, renamed when you say so)
  apps/charts/        Vite + React + TypeScript SPA → charts.singolab.com
  packages/chart-core/ pure TS: Chart JSON schema (zod), chartToAbc(), ABC lint,
                       Nashville numbers, cross-check maths. Zero DOM. 100% unit-tested.
  workers/site/       Cloudflare Worker: serves apps/charts/dist as static assets and
                       /api/* (source adapters, KV cache, rate limit)
  charts/             seed Chart JSON, one file per song (7 from the reference)
  prompts/            versioned prompt files: system.v1.md, generate.v1.md, …
  reference/          bcg-band-bass-charts.html frozen + golden ABC per song + baseline PNGs
  audio/              empty until Phase 4 (README pointing at tag v0-transcriber)
  .github/workflows/  ci.yml (lint, typecheck, unit, visual)
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
  auth: { kind: 'oauth-pkce' } | { kind: 'api-key' } | { kind: 'none' };
  listModels(): Promise<string[]>;
  generateJson(req: { system: string; user: string; schema: JsonSchema }): Promise<unknown>;
}
```

All four are called **from the browser** with the user's own credential (§1.2), so
no model key ever touches a server. Credentials live in the browser only (IndexedDB,
wrapped with WebCrypto under a passphrase you set once per device); there is no user
database. OpenRouter gets the one OAuth button; the others get key fields; Ollama
local gets a URL field and a one-line `OLLAMA_ORIGINS` instruction.

Prompts are files in `prompts/` with a version in the name; the system prompt carries
the §1 content rules (slashes only, no lyrics or melody, confidence marks are given
to the model, not invented by it, footer names real sources).

### 3.4 Source gathering and cross-check

Each approved source is a `SourceAdapter` returning normalised evidence; pasted
evidence (§1.3) uses the same shape:

```ts
type Evidence = {
  source: string;
  url?: string;
  kind: 'api' | 'dataset' | 'pasted' | 'audio';
  gives: ('chords' | 'beat-grid' | 'key' | 'bpm' | 'structure')[];
  key?: string;
  bpm?: number;
  timeSig?: string;
  sections?: { label: string; bars?: number; chords?: string[] }[];
};
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
`layout: { barsPerLine?: 4 | 8 }` hint, and `sources[].fetchedAt` / `sources[].kind`.
The "numbers" line stays a string (author-editable) but Phase 3 generates it from
the chords with a small roman-numeral helper (`tonal` if its slash- and
borrowed-chord handling holds up in a spike, otherwise ~80 lines hand-rolled on the
pitch-class logic already in `chords.py`).

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
self-hosts its fonts), print CSS at Letter, fit-to-page policy from §4; Worker
config; CI green; you create the Cloudflare project and it goes live at
`charts.singolab.com`.
Acceptance: golden tests pass, visual diff vs reference within tolerance for all 7,
browser print of a chart is one page for the songs the policy can fit.

**Phase 2: library.** IndexedDB library (`idb`), add/edit/delete, a form editor
plus a raw JSON editor with live schema validation, bulk paste ("Title — Artist"
per line, one stub chart each), export/import of the whole library as JSON, one
route per chart, print one or print all. No backend.

**Phase 3: generation.** `/api` adapters for the approved sources only (GetSongBPM,
MusicBrainz, Songsterr; Chordonomicon offline if its licence allows; any of the
"check" sites whose terms turn out to permit it), KV cache, rate limit; the
"paste what you see" evidence input; `crossCheck`; `ModelProvider` with the four
implementations and the settings screen; `prompts/v1`; the generate flow shows the
evidence table before it calls the model, then the rendered chart with real
confidence marks and a real footer; "generate all" for a pasted setlist.
Acceptance: the seven seed songs regenerate to charts whose form, key and bpm agree
with the seeds, and every mark on the page is traceable to a row in the evidence
table.

**Phase 4: audio, flagged, default off.** Only if you ask after 1–3 are solid.
Keepers come back from the tag into `audio/` as a separate Python package with
extras, reachable behind `VITE_FEATURE_AUDIO` and a separate deploy target; it emits
one more `Evidence` object (`kind: 'audio'`) with its own weight and never a
note-for-note line.

Order of commits inside each phase: scaffold → pure code + tests → UI → deploy
config → docs. Short commits, conventional messages, a DECISIONS.md entry per
non-obvious call.

---

## 6. Decisions I am making myself (going into DECISIONS.md at Phase 1 start)

- Vite + React + TypeScript for the app, matching `drive.singolab.com`; no Astro
  (no content pages to justify it).
- One Worker with static assets rather than Pages + Worker, per Cloudflare's 2026
  guidance for new projects; Pages settings documented as the fallback.
- npm workspaces, vitest, zod, Hono on Workers, `idb`, ESLint + Prettier.
- abcjs pinned to 6.4.4 for reference parity in Phase 1; upgrade attempted as a
  separate commit once the visual test exists.
- Print via the browser print dialog and `@page { size: letter }`; the old
  jsPDF + svg2pdf export is dropped (the reference already prints correctly).
- Keys client-side only; model calls browser-direct; no accounts, no server storage
  of anything per user.
- Sources that forbid automated access are dropped, not proxied or "politely"
  scraped; pasted evidence is the escape hatch.
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
5. **Cloudflare:** when Phase 1 is ready to deploy, create the Worker project
   pointing at this repo (I will give you the settings) and add
   `charts.singolab.com` as its custom domain.
6. **Chordify:** if you want its beat grid back as a source, the only compliant
   route is asking them (info@chordify.net) for written permission or an API
   licence. Your call whether that email is worth sending; the plan does not
   depend on it.
