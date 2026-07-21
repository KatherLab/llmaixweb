import { defineConfig, devices } from '@playwright/test'

// Documentation-screenshot harness. Boots the same three servers as the e2e
// smoke (fake OpenAI-compatible LLM on 9099, FastAPI backend broker-free on
// SQLite on 8000 via backend/.env.e2e, Vite dev server on 3000) and walks the
// full product workflow with the real sample data in backend/tests/files,
// capturing PNGs into docs/assets/screenshots/.
//
// Run with `npm run screenshots` (resets backend state first, same as e2e).
//
// Kept separate from playwright.config.ts so the smoke test stays fast and the
// screenshot run can use a fixed viewport / retina scale / light theme without
// affecting CI.
const CI = !!process.env.CI

export default defineConfig({
  testDir: './e2e/screenshots',
  // Screenshotting the whole app touches every view; give it room.
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: CI,
  retries: 0,
  reporter: [['list']],
  use: {
    // Vite runs on 3100 here (3000 is often taken by an editor/dev server).
    baseURL: 'http://localhost:3100',
    // Fixed, retina-crisp desktop frame for consistent docs images.
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    // Force light mode regardless of OS preference (docs are light-only).
    colorScheme: 'light',
    screenshot: 'off',
    trace: 'off',
    // Cap every action so a single bad selector in the guarded "extras" can't
    // consume the whole test budget (a hung click once closed the page and
    // skipped all later shots).
    actionTimeout: 8000,
    navigationTimeout: 20_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'node e2e/screenshots/support/fake-llm-realistic.mjs',
      port: 9099,
      reuseExistingServer: false,
      env: { FAKE_LLM_PORT: '9099' },
    },
    {
      command: 'uv run uvicorn backend.src.main:app --host 127.0.0.1 --port 8000',
      port: 8000,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ENV_PATH: 'backend/.env.e2e',
        // Allow the 3100 dev origin (env overrides the .env file value).
        BACKEND_CORS_ORIGINS: 'http://localhost:3100,http://127.0.0.1:3100',
      },
    },
    {
      command: 'npm run dev -- --port 3100 --strictPort',
      url: 'http://localhost:3100',
      reuseExistingServer: !CI,
      timeout: 120_000,
    },
  ],
})
