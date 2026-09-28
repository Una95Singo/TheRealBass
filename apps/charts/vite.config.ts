import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const repoRoot = fileURLToPath(new URL('../..', import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    // The seed charts live at the repo root (charts/*.json); let the dev server read them.
    fs: { allow: [repoRoot] },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
