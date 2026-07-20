// Vitest config for the frontend unit/component suite.
//
// Kept separate from `frontend/vite.config.js` (the build/dev config) so the
// test toolchain never leaks into the production bundle. Mirrors the `@` alias
// so tests import app code the same way components do.
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

export default defineConfig({
  plugins: [vue()],
  // Match the app build: full vue-i18n bundle + feature flags so specs that
  // touch i18n (e.g. formatters) behave like production.
  define: {
    __VUE_I18N_FULL_INSTALL__: true,
    __VUE_I18N_LEGACY_API__: false,
    __INTLIFY_PROD_DEVTOOLS__: false,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'frontend'),
      'vue-i18n': 'vue-i18n/dist/vue-i18n.esm-bundler.js',
    },
  },
  test: {
    // jsdom gives composables/components a DOM (document, timers, lifecycle).
    environment: 'jsdom',
    // Co-locate specs next to the code they cover (utils/, composables/, …).
    include: ['frontend/**/*.{test,spec}.ts'],
    // Explicit imports from 'vitest' in every spec (no ambient globals) keeps
    // eslint/tsconfig happy without widening their `types`.
    globals: false,
    clearMocks: true,
    restoreMocks: true,
  },
})
