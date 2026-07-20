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
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'frontend'),
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
