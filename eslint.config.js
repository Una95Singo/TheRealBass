import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      '**/dist/**',
      '**/node_modules/**',
      '**/.wrangler/**',
      'reference/**',
      '**/playwright-report/**',
      '**/test-results/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['apps/**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks, 'react-refresh': reactRefresh },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'react-refresh/only-export-components': 'warn',
    },
  },
  {
    // Node scripts that also run code inside a browser page (Playwright evaluate callbacks).
    files: ['**/e2e/**/*.mjs', '**/*.config.{js,mjs,ts}'],
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.browser,
        // Globals of the frozen reference page, used by the baseline script.
        songs: 'readonly',
        ABCJS: 'readonly',
      },
    },
  },
);
