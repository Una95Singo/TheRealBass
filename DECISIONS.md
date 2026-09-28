# Decisions

Calls made while building, newest first. Anything that touches the product
thesis (PLAN.md §1) is a question for Una, not an entry here.

## 2026-09-28 — Phase 1: renderer

- **`%%barsperstaff` is out of the dialect.** The reference used it, but with it
  abcjs ignores the source line breaks, re-flows every N bar lines and counts a
  leading `|:` as one of them, so the last bar of every repeated section spills
  onto the next line (and two reference charts end in a one-bar orphan line).
  Without it abcjs honours our line breaks exactly. `chartToAbc` writes explicit
  lines, the lint rejects the directive, and the golden test compares against
  the reference ABC with that one line removed. Everything else stays byte for
  byte.
- **abcjs is loaded as a classic script, not bundled.** Its prebuilt bundle
  assigns an undeclared variable (`i is not defined` in `cleanUp`) and only
  works in sloppy mode, which is how the reference loads it from cdnjs. The
  file still comes from the pinned npm package and is served from our origin.
- **Fit-to-page policy.** Reference layout (4 bars per line) → 8 bars per line →
  two pages at 4 bars per line split at a section boundary, balanced by
  staff-line count and nudged toward the overflowing page → two pages at 8. The
  staff is never shrunk: 8 bars per line keeps every symbol at the reference
  size; a smaller staff is unreadable on a music stand. (`scale` has no effect
  under abcjs's responsive resize; `staffwidth` shrinks chord symbols to ~8pt
  and was dropped.) Result on the seeds: four charts fit one page at 8 bars per
  line, two at 4, "Since U Been Gone" is two pages at 4, "12 to 12" two pages at 8. Split charts say "2 pp." in the header and page 2 carries a small
  continuation header.
- **Print geometry equals screen geometry.** The sheet's on-screen padding is
  the print page margin (0.45in / 0.5in / 0.4in, the reference's values), so
  the content column is 7.5in in both and the fit check can measure the
  on-screen sheet: it fits if the box is ≤ 11in tall. The parity test also
  prints each chart to PDF and asserts the page count.
- **Parity is checked on SVG markup first, pixels second.** Same ABC, same
  abcjs, same font files must give identical markup; the PNG comparison (with
  the SVG snapped to a whole-pixel top so anti-aliasing does not depend on the
  page above it) guards glyph rendering. Baselines are re-rendered from the
  reference's own data with the two reference defects corrected.
- **Part-label duplicates removed after render.** abcjs 6.4.4 and 6.7.1 both
  re-emit a repeated section's boxed letter on every later staff line. Each
  letter is written once per chart, so dropping every box after the first
  occurrence of its letter is exact and tested. Upstream report to follow.
- **A chord event means "print this symbol here".** A bar with an empty `chords`
  list continues the previous chord and prints nothing (Real Book convention),
  so Chart JSON serialises to ABC one-to-one and the golden test can be exact.
  Where a chart re-prints the same chord (a new phrase starting on the chord
  already sounding) the JSON says so explicitly.
- **Sections are written once and referenced from the form.** V2 and V1 share a
  letter; the roadmap carries the counts. Form counts that do not equal the
  section's written (or written × 2 with repeat) bar count are a lint
  _warning_, because the seeds legitimately do this ("Int 4" pointing at the
  12-bar intro vamp).
- **Free-text footer kept.** `verify.text` prints verbatim when present so the
  seven seeds match the reference word for word; the structured `agree` /
  `check` fields exist for Phase 3, and the renderer composes the footer from
  them when `text` is absent.
- **Billie Jean note trimmed.** The reference spelled the riff pitch by pitch;
  that is a note-for-note line and outside the content rules, so the seed
  describes the shape and role instead. Flagged to Una in PLAN.md §7.
- **Old code goes behind a tag, not into `archive/`.** Tagged `v0-transcriber`
  locally (the git proxy in the build environment refuses tag pushes; the same
  commit, `37d361f`, is on `claude/general-session-SsMKd` on GitHub). Phase 4
  pulls the Demucs wrapper, section-label merging and beat-grid snapping back
  from there.
- **abcjs pinned to 6.4.4** for parity with the reference. Upgrading is a
  separate commit now that the parity test exists.
- **Stack.** Vite + React + TypeScript (matches drive.singolab.com), npm
  workspaces, zod, vitest, Playwright, ESLint + Prettier, one Cloudflare Worker
  with static assets (Cloudflare's 2026 guidance for new projects; Pages is the
  fallback and works unchanged with the same `dist`).
- **Fonts self-hosted** via @fontsource, as the personal site does; no runtime
  request to Google Fonts.
- **Print via the browser**, `@page { size: letter }`. The old jsPDF export is
  gone.
- **Only x/4 metres for now.** The slash bar is `L:1/4` quarter slashes; 6/8
  and friends need a different bar template and are rejected by the lint until
  a chart needs them.
