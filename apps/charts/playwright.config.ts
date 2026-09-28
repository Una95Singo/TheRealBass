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
    command: `npm run preview -- --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
