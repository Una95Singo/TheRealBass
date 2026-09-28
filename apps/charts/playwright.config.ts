import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: true,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  // Baselines are generated from the reference page by `npm run baseline`
  // and committed under reference/baseline/.
  snapshotPathTemplate: '../../reference/baseline/{arg}{ext}',
  expect: {
    // The exact SVG-markup comparison is the gate; the PNG guards glyph rendering and
    // tolerates anti-aliasing differences between machines.
    toHaveScreenshot: { maxDiffPixelRatio: 0.03, animations: 'disabled', scale: 'css' },
  },
  use: {
    ...devices['Desktop Chrome'],
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1000, height: 1400 },
    deviceScaleFactor: 1,
    colorScheme: 'light',
  },
  projects: [{ name: 'chromium' }],
  webServer: {
    // Bind explicitly: on some runners `localhost` resolves to ::1 while the URL below is IPv4.
    command: `npm run preview -- --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
