// Generates reference/baseline/<id>-staff.png from the frozen reference page,
// rendered with the SAME abcjs build and the SAME font files the app ships, and
// with the same duplicate-part-label cleanup the app applies. The parity test
// compares the app's staff against these.
//
// Also writes <id>-sheet.png (whole page) for eyeballing; tests do not use them.
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { readFileSync, mkdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..');
const outDir = join(repoRoot, 'reference', 'baseline');
mkdirSync(outDir, { recursive: true });
const require = createRequire(import.meta.url);

const MIME = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
};
const server = createServer((req, res) => {
  const path = join(repoRoot, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  try {
    if (!path.startsWith(repoRoot) || !statSync(path).isFile()) throw new Error('nope');
    res.writeHead(200, { 'content-type': MIME[extname(path)] ?? 'application/octet-stream' });
    res.end(readFileSync(path));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

// Same font files the app imports (@fontsource), served from node_modules.
function fontCss(pkg, file) {
  const cssPath = require.resolve(`${pkg}/${file}`);
  const dir = '/' + relative(repoRoot, dirname(cssPath)).split('\\').join('/');
  return readFileSync(cssPath, 'utf8').replace(/url\(\.\//g, `url(${base}${dir}/`);
}
const css = [
  fontCss('@fontsource/architects-daughter', 'index.css'),
  fontCss('@fontsource/nunito-sans', '400.css'),
  fontCss('@fontsource/nunito-sans', '700.css'),
].join('\n');
const abcjsPath = require.resolve('abcjs/dist/abcjs-basic-min.js');

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1000, height: 1400 },
  deviceScaleFactor: 1,
  colorScheme: 'light',
});
await page.route('https://cdnjs.cloudflare.com/**', (route) =>
  route.fulfill({ path: abcjsPath, contentType: 'application/javascript' }),
);
await page.route('https://fonts.googleapis.com/**', (route) =>
  route.fulfill({ body: css, contentType: 'text/css' }),
);
await page.goto(`${base}/reference/bcg-band-bass-charts.html`, { waitUntil: 'load' });
await page.evaluate(async () => {
  await Promise.all(
    ['13px "Architects Daughter"', '400 12px "Nunito Sans"', '700 12px "Nunito Sans"'].map((f) =>
      document.fonts.load(f),
    ),
  );
  await document.fonts.ready;
});

// The page rendered before the fonts arrived; render again exactly as it does,
// now with fonts loaded, with the app's part-label cleanup, and WITHOUT the
// reference's `%%barsperstaff 4` line (it makes abcjs ignore the source line
// breaks and miscount `|:`, spilling the last bar of repeated sections; the
// app's dialect breaks lines explicitly instead — see reference/README.md).
const ids = await page.evaluate(() => {
  const dedupe = (root) => {
    const seen = new Set();
    for (const el of Array.from(root.querySelectorAll('.abcjs-part'))) {
      const t = el.textContent.trim();
      if (seen.has(t)) el.remove();
      else seen.add(t);
    }
  };
  return songs.map((s, i) => {
    const abc = `X:${i + 1}\nM:4/4\nL:1/4\nQ:1/4=${s.bpm}\nK:${s.keysig} clef=bass style=rhythm\n${s.abc.trim()}\n`;
    const el = document.getElementById(`staff-${s.id}`);
    el.innerHTML = '';
    ABCJS.renderAbc(el, abc, {
      responsive: 'resize',
      scale: 0.78,
      paddingtop: 0,
      paddingbottom: 0,
      paddingleft: 0,
      paddingright: 0,
      add_classes: true,
      format: { partsfont: 'Architects Daughter 13 box', gchordfont: 'Architects Daughter 13' },
    });
    dedupe(el);
    return s.id;
  });
});
await page.waitForTimeout(300);
for (const id of ids) {
  const svg = page.locator(`#staff-${id} svg`);
  // Exact markup is the primary baseline; the PNG guards glyph rendering.
  writeFileSync(join(outDir, `${id}-staff.svg`), await svg.evaluate((el) => el.outerHTML));
  // Snap the SVG's top to a whole pixel so anti-aliasing does not depend on
  // whatever sits above it (the app's header differs from the reference's).
  await svg.evaluate((el) => {
    const top = el.getBoundingClientRect().top;
    el.style.position = 'relative';
    el.style.top = `${Math.floor(top) - top}px`;
  });
  await svg.screenshot({ path: join(outDir, `${id}-staff.png`) });
  await page.locator(`main[id="${id}"]`).screenshot({ path: join(outDir, `${id}-sheet.png`) });
  console.log('baseline', id);
}
writeFileSync(
  join(outDir, 'README.md'),
  `# Baselines\n\nGenerated by \`npm run baseline -w @lowbook/charts\` from \`reference/bcg-band-bass-charts.html\`\nusing the app's abcjs build and font files. \`<id>-staff.png\` is what the parity test\ncompares against; \`<id>-sheet.png\` is for eyeballing only. Regenerate when abcjs, the\nfonts or the render options change, and look at the diff before committing.\n`,
);
await browser.close();
server.close();
