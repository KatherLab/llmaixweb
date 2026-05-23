import js from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier'
import eslintPluginVue from 'eslint-plugin-vue'
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
  {
    files: ['frontend/**/*.{js,vue}'],
    ...js.configs.recommended,
  },
  ...eslintPluginVue.configs['flat/recommended'].map((config) => ({
    ...config,
    files: ['frontend/**/*.{js,vue}'],
  })),
  {
    files: ['frontend/**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/require-toggle-inside-transition': 'warn',
      'vue/valid-v-on': ['warn', { modifiers: ['outside'] }],
    },
  },
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
