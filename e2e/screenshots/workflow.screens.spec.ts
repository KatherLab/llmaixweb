import {
  test,
  expect,
  request,
  type APIRequestContext,
  type Page,
  type Locator,
} from '@playwright/test'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { ADMIN, API_BASE, CSV_NAME, CSV_PATH, SCHEMA_DEFINITION, USER_PROMPT } from '../support/api'

// Documentation screenshots. Walks the whole product workflow with the real
// sample data (backend/tests/files) against the realistic fake LLM, capturing
// PNGs into docs/assets/screenshots/. See playwright.screenshots.config.ts.
//
// Nothing here asserts product correctness (that's the e2e smoke's job); the
// goal is to reach each meaningful UI state and photograph it. Fragile
// interactions are wrapped so a single missing element never aborts the set.

const OUT = 'docs/assets/screenshots'
const FILES_DIR = path.resolve(process.cwd(), 'backend/tests/files')
const FAKE_LLM_BASE = 'http://127.0.0.1:9099/v1'
const LLM_MODEL = 'GPT-OSS-120B'

const SCHEMA_NAME = 'Lung Embolism Findings'
const PROMPT_NAME = 'Lung Embolism Extraction'
const TRIAL_NAME = 'GPT-OSS-120B extraction'
const PROJECT_NAME = 'Lung Embolism Study'

async function shot(page: Page, name: string, opts: { fullPage?: boolean } = {}) {
  // Let animations settle and any transient toast fade before capturing.
  await page.waitForTimeout(500)
  await page.screenshot({
    path: `${OUT}/${name}.png`,
    fullPage: !!opts.fullPage,
    animations: 'disabled',
  })
}

async function shotEl(el: Locator, name: string) {
  await el.page().waitForTimeout(400)
  await el.screenshot({ path: `${OUT}/${name}.png`, animations: 'disabled' })
}

function upload(name: string, mimeType: string) {
  return { name, mimeType, buffer: readFileSync(path.join(FILES_DIR, name)) }
}

async function authedApi(page: Page): Promise<APIRequestContext> {
  const token = await page.evaluate(() => localStorage.getItem('token'))
  if (!token) throw new Error('no auth token in localStorage after login')
  return request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
}

async function ok(res: Awaited<ReturnType<APIRequestContext['post']>>, label: string) {
  if (!res.ok()) throw new Error(`${label}: ${res.status()} ${await res.text()}`)
  return res
}

test('documentation screenshots: full workflow', async ({ page }) => {
  // Force light mode before any app code runs (app toggles the `dark` class off
  // localStorage['darkMode']), and neutralize the modal backdrop so element
  // screenshots don't show the semi-transparent dark overlay through a panel's
  // rounded corners. Replace `bg-black/30 backdrop-blur-md` with an opaque light
  // field for the whole run.
  await page.addInitScript(() => {
    try {
      localStorage.setItem('darkMode', 'false')
    } catch {
      /* ignore */
    }
    const injectBackdropStyle = () => {
      const style = document.createElement('style')
      style.textContent =
        '[class*="bg-black/30"]{background-color:#eef2f6 !important;backdrop-filter:none !important;-webkit-backdrop-filter:none !important;}'
      document.documentElement.appendChild(style)
    }
    if (document.documentElement) injectBackdropStyle()
    else document.addEventListener('DOMContentLoaded', injectBackdropStyle)
  })

  const fill = (testid: string, value: string) =>
    page.getByTestId(testid).locator('input').fill(value)

  // Landing / login / register are captured at the very end (after logout);
  // on a fresh DB every route redirects to /first-admin until an admin exists.

  // ── First-admin setup (fresh install) ─────────────────────────────────
  await page.goto('/projects')
  await page.waitForURL(/\/(first-admin|login)/)
  if (page.url().includes('first-admin')) {
    await fill('first-admin-name', ADMIN.fullName)
    await fill('first-admin-email', ADMIN.email)
    await fill('first-admin-password', ADMIN.password)
    await fill('first-admin-confirm', ADMIN.password)
    await shot(page, 'first-admin-setup')
    await page.getByTestId('first-admin-submit').click()
  } else {
    await fill('login-email', ADMIN.email)
    await fill('login-password', ADMIN.password)
    await shot(page, 'login')
    await page.getByTestId('login-submit').click()
  }
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('token')), { timeout: 15_000 })
    .toBeTruthy()

  const api = await authedApi(page)

  try {
    // ── Projects overview: seed a few projects for a fuller grid ──────────
    for (const p of [
      { name: 'Radiology Reports Q2', description: 'CT pulmonary angiography reports.' },
      { name: 'Pathology Extraction Pilot', description: 'Histology report structuring.' },
    ]) {
      await ok(await api.post(`/api/v1/project`, { data: p }), 'seed project')
    }

    // Create the main project through the UI (also captures the modal).
    await page.goto('/projects')
    await page.waitForLoadState('networkidle')
    await shot(page, 'projects-overview')

    await page.getByTestId('create-project-open').first().click()
    const projDialog = page.getByRole('dialog')
    await projDialog.locator('#projectName').fill(PROJECT_NAME)
    await shotEl(projDialog, 'project-create-modal')
    await projDialog.getByTestId('create-project-submit').click()
    await page.waitForURL(/\/projects\/\d+/)
    const projectId = Number(page.url().match(/\/projects\/(\d+)/)![1])

    // ── Files: upload CSV + a PDF + a PNG for a varied table ──────────────
    await ok(
      await api.post(`/api/v1/project/${projectId}/file`, {
        multipart: {
          file: { name: CSV_NAME, mimeType: 'text/csv', buffer: readFileSync(CSV_PATH) },
          file_info: JSON.stringify({ file_name: CSV_NAME, file_type: 'text/csv' }),
        },
      }),
      'upload csv',
    )
    const csvFileId = 1 // first file in a fresh project
    for (const [fname, mime] of [
      ['9874562_text.pdf', 'application/pdf'],
      ['9874562.png', 'image/png'],
    ] as const) {
      await ok(
        await api.post(`/api/v1/project/${projectId}/file`, {
          multipart: {
            file: upload(fname, mime),
            file_info: JSON.stringify({ file_name: fname, file_type: mime }),
          },
        }),
        `upload ${fname}`,
      )
    }

    await page.goto(`/projects/${projectId}?tab=files`)
    await expect(page.getByText(CSV_NAME)).toBeVisible()
    await shot(page, 'files-list')

    // Import-config modal for the CSV (row-by-row).
    await page.getByTestId('file-configure').first().click()
    const importDialog = page.getByRole('dialog')
    await importDialog.getByTestId('import-strategy-row-by-row').check()
    await importDialog.getByTestId('import-text-column-report').check()
    await importDialog.locator('#import-case-id').selectOption('id')
    await shotEl(importDialog, 'files-import-config')
    await importDialog.getByTestId('import-save').click()
    await expect(importDialog).toBeHidden()

    // ── Preprocess the CSV → 8 documents (API, synchronous) ───────────────
    await ok(
      await api.post(`/api/v1/project/${projectId}/preprocess`, {
        data: {
          file_ids: [csvFileId],
          inline_config: { name: 'Row-by-row import', additional_settings: {} },
          bypass_celery: true,
        },
      }),
      'preprocess',
    )

    // ── Documents ─────────────────────────────────────────────────────────
    await page.goto(`/projects/${projectId}?tab=documents`)
    await expect(page.getByText('9874562.pdf')).toBeVisible()
    await shot(page, 'documents-list')

    // Open the first document's viewer via its row action button.
    try {
      const firstRow = page.locator('tbody tr').first()
      await firstRow.getByRole('button').first().click({ timeout: 5000 })
      const viewer = page.getByRole('dialog')
      await expect(viewer).toBeVisible({ timeout: 5000 })
      await shot(page, 'document-viewer')
      await page.keyboard.press('Escape')
    } catch {
      /* viewer selector may differ; table shot already captured */
    }

    // ── Schema (UI) ───────────────────────────────────────────────────────
    await page.goto(`/projects/${projectId}?tab=schemas`)
    await page.getByTestId('create-schema-open').click()
    const schemaDialog = page.getByRole('dialog')
    await schemaDialog.locator('#schema-name').fill(SCHEMA_NAME)
    await schemaDialog.getByRole('button', { name: 'Advanced' }).click()
    await schemaDialog.getByRole('button', { name: 'Raw JSON' }).click()
    await schemaDialog
      .getByTestId('schema-raw-json')
      .fill(JSON.stringify(SCHEMA_DEFINITION, null, 2))
    await shotEl(schemaDialog, 'schema-editor')
    await schemaDialog.getByTestId('schema-submit').click()
    await expect(schemaDialog).toBeHidden()
    await page.goto(`/projects/${projectId}?tab=schemas`)
    await expect(page.getByText(SCHEMA_NAME)).toBeVisible()
    await shot(page, 'schemas-list')

    // ── Prompt (UI) ───────────────────────────────────────────────────────
    await page.getByRole('button', { name: 'Extraction Prompts' }).click()
    await page.getByTestId('create-prompt-open').click()
    const promptDialog = page.getByRole('dialog')
    await promptDialog.locator('#prompt-name').fill(PROMPT_NAME)
    await promptDialog.locator('#simple-prompt').fill(USER_PROMPT)
    await shotEl(promptDialog, 'prompt-editor')
    await promptDialog.getByTestId('prompt-submit').click()
    await expect(promptDialog).toBeHidden()
    await shot(page, 'prompts-list')

    // ── Trial (API, synchronous against realistic fake LLM) ───────────────
    const schemaId = (await (await api.get(`/api/v1/project/${projectId}/schema`)).json())[0].id
    const promptId = (await (await api.get(`/api/v1/project/${projectId}/prompt`)).json())[0].id
    const docs = await (
      await api.get(`/api/v1/project/${projectId}/document?limit=500&sort=created_asc`)
    ).json()
    const documentIds = docs.items.map((d: { id: number }) => d.id)
    const trialRes = await ok(
      await api.post(`/api/v1/project/${projectId}/trial`, {
        data: {
          name: TRIAL_NAME,
          schema_id: schemaId,
          prompt_id: promptId,
          document_ids: documentIds,
          llm_model: LLM_MODEL,
          api_key: 'sk-fake',
          base_url: FAKE_LLM_BASE,
          bypass_celery: true,
        },
      }),
      'create trial',
    )
    const trialId = (await trialRes.json()).id

    await page.goto(`/projects/${projectId}?tab=trials`)
    await expect(page.getByText(TRIAL_NAME).first()).toBeVisible()
    await shot(page, 'trials-list')

    // Open trial results via the row's results-action button.
    try {
      await page
        .getByRole('button', { name: /result/i })
        .first()
        .click({ timeout: 5000 })
      const resultsDialog = page.getByRole('dialog')
      await expect(resultsDialog).toBeVisible({ timeout: 8000 })
      await page.waitForTimeout(800)
      await shot(page, 'trial-results')
      // Add the Reasoning pane (present only when the model returned reasoning)
      // to capture the chain-of-thought + token-usage view.
      try {
        await resultsDialog
          .getByRole('button', { name: 'Reasoning' })
          .first()
          .click({ timeout: 4000 })
        await page.waitForTimeout(500)
        await shot(page, 'trial-reasoning')
      } catch {
        /* no reasoning toggle in this build */
      }
      await page.keyboard.press('Escape')
    } catch {
      /* results view selector may differ; list shot already captured */
    }

    // ── Ground truth + mappings + evaluation (API) ────────────────────────
    const gtRes = await ok(
      await api.post(`/api/v1/project/${projectId}/groundtruth`, {
        multipart: {
          file: { name: CSV_NAME, mimeType: 'text/csv', buffer: readFileSync(CSV_PATH) },
          format: 'csv',
          name: 'Reference ground truth',
        },
      }),
      'upload gt',
    )
    const gtId = (await gtRes.json()).id
    await ok(
      await api.put(`/api/v1/project/${projectId}/groundtruth/${gtId}/id-column`, {
        data: { id_column: 'id' },
      }),
      'gt id column',
    )
    const boolFields = [
      'shortness of breath',
      'chest pain',
      'leg pain or swelling',
      'heart palpitations',
      'cough',
      'dizziness',
    ]
    const mappings = [
      ...boolFields.map((f) => ({
        schema_field: f,
        ground_truth_field: f,
        schema_id: schemaId,
        field_type: 'boolean',
        comparison_method: 'boolean',
        comparison_options: {},
      })),
      ...['location', 'side'].map((f) => ({
        schema_field: f,
        ground_truth_field: f,
        schema_id: schemaId,
        field_type: 'string',
        comparison_method: 'exact',
        comparison_options: {},
      })),
    ]
    await ok(
      await api.post(
        `/api/v1/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`,
        { data: mappings },
      ),
      'gt mappings',
    )
    await ok(
      await api.post(
        `/api/v1/project/${projectId}/trial/${trialId}/evaluate?groundtruth_id=${gtId}&force_recalculate=true`,
      ),
      'evaluate',
    )

    await page.goto(`/projects/${projectId}?tab=evaluation`)
    await expect(page.getByText(/\d+(\.\d+)?%/).first()).toBeVisible()
    await page.waitForTimeout(1000)
    await shot(page, 'evaluation-overview')
    await shot(page, 'evaluation-full', { fullPage: true })

    // ── Exhaustive extras (guarded): modals, groups, admin, account ───────
    // Each block opens a state and photographs it; a selector miss only skips
    // that one shot. page.goto between blocks abandons any open modal cleanly.
    const tab = (t: string) => page.goto(`/projects/${projectId}?tab=${t}`)
    const extra = async (name: string, fn: () => Promise<void>) => {
      try {
        await fn()
      } catch (e) {
        console.log(`[skip ${name}] ${String(e).split('\n')[0]}`)
      }
    }
    const dialog = () => page.getByRole('dialog')

    // Files: upload modal
    await extra('files-upload-modal', async () => {
      await tab('files')
      await page.getByRole('button', { name: 'Upload Files' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await shotEl(dialog(), 'files-upload-modal')
    })

    // Files: preview modal
    await extra('files-preview', async () => {
      await tab('files')
      await page.getByRole('button', { name: 'Preview' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await page.waitForTimeout(1200)
      await shot(page, 'files-preview')
    })

    // Files: preprocessing config panel — select the CSV row (needs no OCR, so
    // the panel shows a clean config rather than the "no OCR engine" notice a
    // PDF/PNG triggers in this offline harness).
    await extra('preprocessing-config', async () => {
      await tab('files')
      await page
        .locator('tbody tr', { hasText: 'reports_with_groundtruth' })
        .first()
        .getByRole('checkbox')
        .first()
        .check()
      await page.getByRole('button', { name: 'Configure Preprocessing' }).first().click()
      await page.waitForTimeout(800)
      await shot(page, 'preprocessing-config', { fullPage: true })
    })

    // Documents: groups tab (BaseTabGroup renders tabs as buttons; the badge
    // count is part of the accessible name, hence the regex).
    await extra('documents-groups', async () => {
      await tab('documents')
      await page
        .getByRole('button', { name: /Document Groups/ })
        .first()
        .click()
      await page.waitForTimeout(600)
      await shot(page, 'documents-groups')
    })

    // Schemas: create modal default (visual) view + templates picker
    await extra('schema-create-visual', async () => {
      await tab('schemas')
      await page.getByTestId('create-schema-open').click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await page.waitForTimeout(500)
      await shotEl(dialog(), 'schema-create-visual')
    })
    await extra('schema-templates', async () => {
      await tab('schemas')
      await page.getByTestId('create-schema-open').click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await dialog().getByRole('button', { name: 'Templates' }).first().click()
      await page.waitForTimeout(600)
      await shot(page, 'schema-templates')
    })

    // Schemas: view an existing schema
    await extra('schema-view', async () => {
      await tab('schemas')
      await page.getByText(SCHEMA_NAME).first().click()
      await expect(dialog()).toBeVisible({ timeout: 4000 })
      await shotEl(dialog(), 'schema-view')
    })

    // Trials: the full create-trial modal
    await extra('trial-create-modal', async () => {
      await tab('trials')
      await page.getByRole('button', { name: 'Start New Trial' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await page.waitForTimeout(800)
      await shotEl(dialog(), 'trial-create-modal')
    })

    // Ground truth: manager + mapping config
    await extra('groundtruth-manager', async () => {
      await tab('evaluation')
      await page.getByRole('button', { name: 'Manage' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await shotEl(dialog(), 'groundtruth-manager')
    })
    await extra('groundtruth-mapping', async () => {
      await tab('evaluation')
      await page.getByRole('button', { name: 'Edit mappings' }).first().click()
      await page.waitForTimeout(800)
      await shot(page, 'groundtruth-mapping', { fullPage: true })
    })

    // Ground truth: upload modal
    await extra('groundtruth-upload', async () => {
      await tab('evaluation')
      await page.getByRole('button', { name: 'Upload Ground Truth' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await shotEl(dialog(), 'groundtruth-upload')
    })

    // Evaluation: export modal
    await extra('evaluation-export', async () => {
      await tab('evaluation')
      await page.getByRole('button', { name: 'Export Results' }).first().click()
      await expect(dialog()).toBeVisible({ timeout: 5000 })
      await shotEl(dialog(), 'evaluation-export')
    })

    // Evaluation: analysis view (per-field metrics, confusion matrix)
    await extra('evaluation-analysis', async () => {
      await tab('evaluation')
      await page.getByText('Analysis').first().click()
      await page.waitForTimeout(1200)
      await shot(page, 'evaluation-analysis', { fullPage: true })
    })

    // Account settings
    await extra('account-settings', async () => {
      await page.goto('/account')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(600)
      await shot(page, 'account-settings', { fullPage: true })
    })

    // Admin pages. (/admin redirects to user-management, and /admin/celery shows
    // an error/empty state in this offline harness — both omitted.)
    for (const [route, name] of [
      ['/admin/settings', 'admin-settings'],
      ['/admin/user-management', 'admin-user-management'],
      ['/admin/sso', 'admin-sso'],
      ['/admin/audit', 'admin-audit'],
    ] as const) {
      await extra(name, async () => {
        await page.goto(route)
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(900)
        await shot(page, name, { fullPage: true })
      })
    }

    // Recapture the projects overview now that the main project has content
    // (documents/trials counts populated) for a richer grid.
    await page.goto('/projects')
    await expect(page.getByText(PROJECT_NAME)).toBeVisible()
    await shot(page, 'projects-overview')

    // ── Logged-out pages: landing, login, register ────────────────────────
    await page.evaluate(() => {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
    })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await shot(page, 'landing-hero')
    await shot(page, 'landing-full', { fullPage: true })

    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    await shot(page, 'login')

    await page.goto('/register')
    await page.waitForLoadState('networkidle')
    await shot(page, 'register')
  } finally {
    await api.dispose()
  }
})
