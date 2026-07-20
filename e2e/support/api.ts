// API helpers + fixtures for the e2e smoke.
//
// The UI never exposes `bypass_celery`, and the backend runs broker-free
// (DISABLE_CELERY), so the two async *executions* — preprocessing and the
// trial — are driven through the admin API with `bypass_celery: true` (which
// runs them synchronously in-process). Everything else is driven through the
// browser; these helpers only cover the API-side steps and read-backs.
import { readFileSync } from 'node:fs'
import path from 'node:path'
import type { APIRequestContext } from '@playwright/test'

// Origin only — paths below carry the /api/v1 prefix. (Playwright resolves a
// leading-slash path against the origin via new URL(), which would otherwise
// drop a base path segment.)
export const API_BASE = 'http://localhost:8000'
export const FAKE_LLM_BASE = 'http://127.0.0.1:9099/v1'

export const ADMIN = {
  email: 'e2e-admin@example.com',
  password: 'Passw0rd!23',
  fullName: 'E2E Admin',
}

export const CSV_NAME = 'reports_with_groundtruth.csv'
export const CSV_PATH = path.resolve(process.cwd(), 'backend/tests/files', CSV_NAME)

/** The `report` text column (case id = `id`) yields 8 documents. */
export const EXPECTED_DOCUMENTS = 8

const BOOLEAN_FIELDS = [
  'shortness of breath',
  'chest pain',
  'leg pain or swelling',
  'heart palpitations',
  'cough',
  'dizziness',
]
const ENUM_FIELDS = ['location', 'side']

/** The 8-field lung-embolism schema from the usage tutorial. */
export const SCHEMA_DEFINITION = {
  type: 'object',
  properties: {
    'shortness of breath': { type: 'boolean' },
    'chest pain': { type: 'boolean' },
    'leg pain or swelling': { type: 'boolean' },
    'heart palpitations': { type: 'boolean' },
    cough: { type: 'boolean' },
    dizziness: { type: 'boolean' },
    location: { type: 'string', enum: ['main', 'segmental', 'unknown'] },
    side: { type: 'string', enum: ['left', 'right', 'bilateral'] },
  },
  required: [...BOOLEAN_FIELDS, ...ENUM_FIELDS],
}

export const USER_PROMPT = [
  'From the following medical report, extract the requested fields as JSON:',
  '- shortness of breath, chest pain, leg pain or swelling, heart palpitations, cough, dizziness: true / false',
  '- location: main / segmental / unknown',
  '- side: left / right / bilateral',
].join('\n')

/** Ground-truth → schema field mappings (column names match the schema keys). */
function fieldMappings(schemaId: number) {
  return [
    ...BOOLEAN_FIELDS.map((f) => ({
      schema_field: f,
      ground_truth_field: f,
      schema_id: schemaId,
      field_type: 'boolean',
      comparison_method: 'boolean',
      comparison_options: {},
    })),
    ...ENUM_FIELDS.map((f) => ({
      schema_field: f,
      ground_truth_field: f,
      schema_id: schemaId,
      field_type: 'string',
      comparison_method: 'exact',
      comparison_options: {},
    })),
  ]
}

async function ok(res: Awaited<ReturnType<APIRequestContext['get']>>, label: string) {
  if (!res.ok()) throw new Error(`${label} failed: ${res.status()} ${await res.text()}`)
  return res
}

function csvUpload() {
  return { name: CSV_NAME, mimeType: 'text/csv', buffer: readFileSync(CSV_PATH) }
}

export async function uploadCsv(ctx: APIRequestContext, projectId: number): Promise<number> {
  const res = await ctx.post(`/api/v1/project/${projectId}/file`, {
    multipart: {
      file: csvUpload(),
      file_info: JSON.stringify({ file_name: CSV_NAME, file_type: 'text/csv' }),
    },
  })
  await ok(res, 'uploadCsv')
  return (await res.json()).id
}

/** Runs synchronously (bypass_celery); documents exist when it returns. */
export async function preprocess(
  ctx: APIRequestContext,
  projectId: number,
  fileId: number,
): Promise<number> {
  const res = await ctx.post(`/api/v1/project/${projectId}/preprocess`, {
    data: {
      file_ids: [fileId],
      inline_config: { name: 'e2e-preprocess', additional_settings: {} },
      bypass_celery: true,
    },
  })
  await ok(res, 'preprocess')
  const body = await res.json()
  return body.documents_count ?? body.processed_files
}

export async function listDocumentIds(
  ctx: APIRequestContext,
  projectId: number,
): Promise<number[]> {
  const res = await ctx.get(`/api/v1/project/${projectId}/document?limit=500&sort=created_asc`)
  await ok(res, 'listDocuments')
  return (await res.json()).items.map((d: { id: number }) => d.id)
}

/** First id from a plain-array resource list (schema / prompt). */
export async function firstId(
  ctx: APIRequestContext,
  projectId: number,
  resource: 'schema' | 'prompt',
): Promise<number> {
  const res = await ctx.get(`/api/v1/project/${projectId}/${resource}`)
  await ok(res, `list ${resource}`)
  const body = await res.json()
  const arr = Array.isArray(body) ? body : body.items
  return arr[0].id
}

export async function createTrial(
  ctx: APIRequestContext,
  projectId: number,
  opts: { schemaId: number; promptId: number; documentIds: number[] },
): Promise<number> {
  const res = await ctx.post(`/api/v1/project/${projectId}/trial`, {
    data: {
      name: 'e2e-extract',
      schema_id: opts.schemaId,
      prompt_id: opts.promptId,
      document_ids: opts.documentIds,
      llm_model: 'fake-model',
      api_key: 'sk-fake',
      base_url: FAKE_LLM_BASE,
      bypass_celery: true,
    },
  })
  await ok(res, 'createTrial')
  return (await res.json()).id
}

export async function trialSuccessCount(
  ctx: APIRequestContext,
  projectId: number,
  trialId: number,
): Promise<number> {
  const res = await ctx.get(
    `/api/v1/project/${projectId}/trial/${trialId}/results?status=success&limit=500`,
  )
  await ok(res, 'trialResults')
  return (await res.json()).total
}

export async function uploadGroundTruth(
  ctx: APIRequestContext,
  projectId: number,
): Promise<number> {
  const res = await ctx.post(`/api/v1/project/${projectId}/groundtruth`, {
    multipart: { file: csvUpload(), format: 'csv', name: 'e2e-ground-truth' },
  })
  await ok(res, 'uploadGroundTruth')
  return (await res.json()).id
}

export async function configureGroundTruth(
  ctx: APIRequestContext,
  projectId: number,
  gtId: number,
  schemaId: number,
): Promise<void> {
  await ok(
    await ctx.put(`/api/v1/project/${projectId}/groundtruth/${gtId}/id-column`, {
      data: { id_column: 'id' },
    }),
    'setIdColumn',
  )
  await ok(
    await ctx.post(`/api/v1/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`, {
      data: fieldMappings(schemaId),
    }),
    'saveMappings',
  )
}

/** Evaluation is synchronous (no Celery); returns overall accuracy (0–1). */
export async function evaluate(
  ctx: APIRequestContext,
  projectId: number,
  trialId: number,
  gtId: number,
): Promise<number> {
  const res = await ctx.post(
    `/api/v1/project/${projectId}/trial/${trialId}/evaluate?groundtruth_id=${gtId}&force_recalculate=true`,
  )
  await ok(res, 'evaluate')
  return (await res.json()).overall_metrics.accuracy
}
