# Low Book

One-page, Real Book-style gig charts for bass. Chords over slashes on a bass-clef
staff, boxed rehearsal letters, a form roadmap with bar counts and ●◐○ confidence
marks, key / tempo / feel, a "bass notes" box and a Nashville key. No lyrics, no
melody, no note-for-note line.

`PLAN.md` is the plan and the reasoning; `DECISIONS.md` the calls made along the
way. The earlier note-for-note transcription experiment (TheRealBass) is
preserved as commit `37d361f` on `claude/general-session-SsMKd` (tagged
`v0-transcriber` locally).

## Layout

```
apps/charts/          Vite + React + TypeScript app → charts.singolab.com
packages/chart-core/  Chart JSON schema (zod), chartToAbc(), ABC dialect lint. Pure, unit-tested.
workers/site/         Cloudflare Worker: serves apps/charts/dist as static assets, answers /api/*
charts/               Seed charts, one Chart JSON per song
reference/            The frozen reference page, its ABC goldens and render baselines
prompts/              (Phase 3) versioned prompt files
audio/                (Phase 4) empty until asked for
```

## Commands

```
npm install
npm run dev              # app at http://localhost:5173
npm test                 # unit tests (chart-core: goldens, dialect rules, schema)
npm run typecheck
npm run lint
npm run format:check
npm run build            # apps/charts/dist
npm run test:visual      # Playwright: staff parity vs the reference, part boxes, page counts
npm run baseline -w @lowbook/charts   # regenerate reference/baseline from the reference page
npm run check -w @lowbook/site        # wrangler deploy --dry-run
```

Node 22. Playwright needs its Chromium once: `npx playwright install chromium`
from `apps/charts`.

## How a chart becomes a page

1. `charts/<id>.json` is validated by `ChartSchema` (`packages/chart-core`).
2. `chartToAbc(chart)` turns it into ABC in the dialect described in
   `reference/README.md`. For the seven seed songs the output equals the
   reference page's own ABC, and a golden test keeps it that way.
3. abcjs 6.4.4 renders the ABC to SVG in the browser with the options in
   `apps/charts/src/lib/render.ts`. Duplicate part boxes (an abcjs quirk) are
   removed after rendering.
4. The sheet is laid out with the reference CSS at print geometry (Letter,
   0.45in / 0.5in / 0.4in margins). If it is taller than one page it steps
   down: 8 bars per line, then a two-page split at a section boundary, first
   at 4 bars per line and then at 8. It never shrinks the staff.
5. Print with the browser's print dialog; each sheet is one page.

## Deploying (Cloudflare)

One Worker with static assets, in the same Cloudflare account as
`singolab.com` and `drive.singolab.com`. Once, in the dashboard:

- Workers & Pages → Create → Worker → connect this GitHub repository.
- Root directory `/`; build command `npm ci && npm run build`; deploy command
  `npx wrangler deploy --config workers/site/wrangler.jsonc`.
- Settings → Domains & Routes → add custom domain `charts.singolab.com`
  (the zone is on Cloudflare, so the DNS record is created for you).

Fallback that needs no Worker: a Pages project exactly like `drive.singolab.com`
with build command `npm ci && npm run build` and output directory
`apps/charts/dist`.

No secrets are needed for Phases 1 and 2; nothing is stored server-side.
