import { test, expect, request, type APIRequestContext, type Page } from '@playwright/test'
import {
  ADMIN,
  API_BASE,
  CSV_NAME,
  EXPECTED_DOCUMENTS,
  SCHEMA_DEFINITION,
  USER_PROMPT,
  configureGroundTruth,
  createTrial,
  evaluate,
  firstId,
  listDocumentIds,
  preprocess,
  trialSuccessCount,
  uploadCsv,
  uploadGroundTruth,
} from '../support/api'

// End-to-end smoke of the core workflow:
//   login → project → upload + import-config → preprocess → documents →
//   schema → prompt → trial → evaluation
//
// UI drives everything a browser can do broker-free; the two async executions
// (preprocess, trial) and the ground-truth/evaluation setup go through the
// admin API with bypass_celery (see support/api.ts for why).

// Adaptive auth: hitting a guarded route redirects to /first-admin on a fresh
// backend (no admin yet) or to /login once the admin exists (e.g. a retry).
// Handle whichever the app shows, then confirm we're authenticated.
async function ensureLoggedIn(page: Page): Promise<void> {
  await page.goto('/projects')
  await page.waitForURL(/\/(first-admin|login)/)

  if (page.url().includes('first-admin')) {
    await page.getByPlaceholder('Full name').fill(ADMIN.fullName)
    await page.locator('input[type="email"]').fill(ADMIN.email)
    await page.getByPlaceholder('Password', { exact: true }).fill(ADMIN.password)
    await page.getByPlaceholder('Confirm password', { exact: true }).fill(ADMIN.password)
    await page.getByRole('button', { name: 'Create Admin Account' }).click()
  } else {
    await page.locator('input[type="email"]').fill(ADMIN.email)
    await page.locator('input[type="password"]').fill(ADMIN.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
  }

  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('token')), { timeout: 15_000 })
    .toBeTruthy()
  await page.goto('/projects')
}

async function createProject(page: Page, name: string): Promise<number> {
  await page.getByRole('button', { name: '+ Create Project' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('#projectName').fill(name)
  await dialog.getByRole('button', { name: 'Create Project', exact: true }).click()
  await page.waitForURL(/\/projects\/\d+/)
  const match = page.url().match(/\/projects\/(\d+)/)
  if (!match) throw new Error(`no project id in URL: ${page.url()}`)
  return Number(match[1])
}

async function authedApi(page: Page): Promise<APIRequestContext> {
  const token = await page.evaluate(() => localStorage.getItem('token'))
  if (!token) throw new Error('no auth token in localStorage after login')
  return request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
}

async function configureImport(page: Page, projectId: number): Promise<void> {
  await page.goto(`/projects/${projectId}?tab=files`)
  await expect(page.getByText(CSV_NAME)).toBeVisible()

  await page.getByRole('button', { name: 'Configure' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('input[type="radio"][value="row_by_row"]').check()
  // Text-column checkboxes are label-wrapped with sample text (no clean
  // accessible name); pick the label that holds a checkbox and the `report` name.
  await dialog
    .locator('label:has(input[type="checkbox"])')
    .filter({ hasText: 'report' })
    .click()
  // Option value is the bare column name; the visible label may add " (Recommended)".
  await dialog.locator('#import-case-id').selectOption('id')
  await dialog.getByRole('button', { name: /^Save/ }).click()
  await expect(dialog).toBeHidden()
}

async function createSchema(page: Page, projectId: number): Promise<void> {
  await page.goto(`/projects/${projectId}?tab=schemas`)
  await page.getByRole('button', { name: 'Create Schema' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('#schema-name').fill('Lung Embolism')
  await dialog.getByRole('button', { name: 'Advanced' }).click()
  await dialog.getByRole('button', { name: 'Raw JSON' }).click()
  await dialog.locator('textarea').first().fill(JSON.stringify(SCHEMA_DEFINITION, null, 2))
  await dialog.getByRole('button', { name: 'Create', exact: true }).click()
  await expect(dialog).toBeHidden()
}

async function createPrompt(page: Page, projectId: number): Promise<void> {
  await page.goto(`/projects/${projectId}?tab=schemas`)
  await page.getByRole('button', { name: 'Extraction Prompts' }).click()
  await page.getByRole('button', { name: 'Create Prompt' }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('#prompt-name').fill('Lung Embolism Extraction')
  await dialog.locator('#simple-prompt').fill(USER_PROMPT)
  await dialog.getByRole('button', { name: 'Create', exact: true }).click()
  await expect(dialog).toBeHidden()
}

test('core workflow: upload → preprocess → trial → evaluation', async ({ page }) => {
  // 1. Login / first-admin setup (UI)
  await ensureLoggedIn(page)

  // 2. Create a project (UI)
  const projectId = await createProject(page, `E2E ${Date.now()}`)
  const api = await authedApi(page)

  try {
    // 3. Upload the CSV (API) + configure row-by-row import (UI)
    const fileId = await uploadCsv(api, projectId)
    await configureImport(page, projectId)

    // 4. Preprocess row-by-row → 8 documents (API, synchronous)
    const documentCount = await preprocess(api, projectId, fileId)
    expect(documentCount).toBe(EXPECTED_DOCUMENTS)
    const documentIds = await listDocumentIds(api, projectId)
    expect(documentIds).toHaveLength(EXPECTED_DOCUMENTS)

    // 5. Documents render (UI)
    await page.goto(`/projects/${projectId}?tab=documents`)
    await expect(page.getByText('9874562.pdf')).toBeVisible()

    // 6. Schema + prompt (UI)
    await createSchema(page, projectId)
    await createPrompt(page, projectId)

    // 7. Run the extraction trial against the fake LLM (API, synchronous)
    const schemaId = await firstId(api, projectId, 'schema')
    const promptId = await firstId(api, projectId, 'prompt')
    const trialId = await createTrial(api, projectId, { schemaId, promptId, documentIds })
    expect(await trialSuccessCount(api, projectId, trialId)).toBe(EXPECTED_DOCUMENTS)

    // 8. Trial renders as completed (UI)
    await page.goto(`/projects/${projectId}?tab=trials`)
    await expect(page.getByText('e2e-extract')).toBeVisible()

    // 9. Ground truth + mappings + evaluation (API; evaluation is synchronous)
    const gtId = await uploadGroundTruth(api, projectId)
    await configureGroundTruth(api, projectId, gtId, schemaId)
    const accuracy = await evaluate(api, projectId, trialId, gtId)
    expect(accuracy).toBeGreaterThanOrEqual(0)

    // 10. Evaluation renders with a percentage (UI)
    await page.goto(`/projects/${projectId}?tab=evaluation`)
    await expect(page.getByText(/\d+(\.\d+)?%/).first()).toBeVisible()
  } finally {
    await api.dispose()
  }
})
