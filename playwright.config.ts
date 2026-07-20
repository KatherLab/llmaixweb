import { defineConfig, devices } from '@playwright/test'

// Playwright e2e smoke config. Boots three servers: a fake OpenAI-compatible
// LLM (9099), the FastAPI backend broker-free on SQLite (8000, via
// backend/.env.e2e), and the Vite dev server (3000). The frontend's dev API
// base URL is hardcoded to http://localhost:8000, so the backend must be on
// 8000 and its CORS must allow http://localhost:3000 (set in .env.e2e).
//
// Run with `npm run test:e2e` (which resets the backend state first).
const CI = !!process.env.CI

export default defineConfig({
  testDir: './e2e/tests',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'node e2e/support/fake-llm.mjs',
      port: 9099,
      // e2e-specific server: never reuse, so a stale process can't mask changes.
      reuseExistingServer: false,
      env: { FAKE_LLM_PORT: '9099' },
    },
    {
      command: 'uv run uvicorn backend.src.main:app --host 127.0.0.1 --port 8000',
      port: 8000,
      // e2e-specific config (SQLite + fake LLM): never reuse a dev backend, and
      // fail fast if something else already holds 8000.
      reuseExistingServer: false,
      timeout: 120_000,
      env: { ENV_PATH: 'backend/.env.e2e' },
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      // The dev server is the same app regardless of run; reuse it locally for
      // faster iteration, but always start fresh in CI.
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
  ],
})
