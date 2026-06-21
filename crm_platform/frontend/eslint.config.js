import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    rules: {
      // The existing app layer is intentionally permissive for dynamic API payloads.
      '@typescript-eslint/no-explicit-any': 'off',
      // The current screens intentionally derive local form state inside effects.
      'react-hooks/set-state-in-effect': 'off',
      // Legacy pages intentionally control effect execution manually.
      'react-hooks/exhaustive-deps': 'off',
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
