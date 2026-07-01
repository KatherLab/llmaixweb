import js from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier'
import eslintPluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import globals from 'globals'

export default [
  {
    ignores: [
      '**/dist/**',
      '**/dist-*/**',
      '**/coverage/**',
      '**/node_modules/**',
    ],
  },

  // Base JS recommended rules for all frontend JS/TS/Vue files.
  {
    files: ['frontend/**/*.{js,ts,vue}'],
    ...js.configs.recommended,
  },

  // TypeScript rules for .ts and .vue (script blocks) files.
  ...tseslint.configs.recommended.map((config) => ({
    ...config,
    files: ['frontend/**/*.{ts,vue}'],
  })),

  // Vue rules for SFC files only (the Vue config sets vue-eslint-parser as the
  // parser, which must not apply to plain .ts/.js files).
  ...eslintPluginVue.configs['flat/recommended'].map((config) => ({
    ...config,
    files: ['frontend/**/*.vue'],
  })),

  // Shared language options + non-Vue rule overrides for all frontend files.
  {
    files: ['frontend/**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      'no-unused-vars': 'off',
    },
  },

  // Vue-specific rule overrides (the vue plugin is registered above for .vue).
  {
    files: ['frontend/**/*.vue'],
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/require-toggle-inside-transition': 'warn',
      'vue/valid-v-on': ['warn', { modifiers: ['outside'] }],
      // All v-html usages render output of `renderMarkdown` (utils/markdown.ts),
      // which sanitizes via DOMPurify, or a pre-sanitized `safeMarkdown` prop.
      'vue/no-v-html': 'off',
    },
  },

  // TypeScript-specific rule overrides (plugin is registered above for these files).
  {
    files: ['frontend/**/*.{ts,vue}'],
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },

  // Use the TS parser inside Vue SFC <script> blocks so TS syntax is accepted.
  {
    files: ['frontend/**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },

  // Ensure .d.ts ambient declaration files use the TS parser.
  {
    files: ['frontend/**/*.d.ts'],
    languageOptions: {
      parser: tseslint.parser,
    },
  },

  // Node-context build scripts.
  {
    files: [
      'frontend/vite.config.js',
      'frontend/tailwind.config.js',
      'frontend/update-version.js',
    ],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },

  eslintConfigPrettier,
]
