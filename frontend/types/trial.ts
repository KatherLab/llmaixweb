import type { ISODateString, QueryParams } from './api'
import type { TrialStatus, TrialResultStatus } from './enums'
import type { Prompt } from './prompt'
import type { DocumentSet } from './documentSet'

/** LLM advanced options (temperature, max_tokens, reasoning_effort, etc.). */
export type TrialAdvancedOptions = Record<string, unknown> & {
  temperature?: number
  max_tokens?: number
  max_completion_tokens?: number
  reasoning_effort?: 'low' | 'medium' | 'high'
}

/** Trial.meta — holds eta_seconds during processing. */
export interface TrialMeta {
  eta_seconds?: number
  [key: string]: unknown
}

export interface TrialResult {
  id: number
  trial_id: number
  document_id: number
  /** Extracted LLM output. */
  result: Record<string, unknown> | null
  status: TrialResultStatus | string | null
  additional_content: Record<string, unknown> | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface TrialResultItem extends TrialResult {
  document_name: string | null
  original_file_name: string | null
}

/** Response for `GET /trials/{id}/results`. */
export interface PaginatedTrialResults {
  items: TrialResultItem[]
  total: number
  total_usage: Record<string, unknown> | null
}

export interface Trial {
  id: number
  project_id: number
  name: string | null
  description: string | null
  schema_id: number
  prompt_id: number
  document_ids: number[] | null
  document_set_id: number | null
  llm_model: string | null
  /** api_key / base_url are excluded from the response. */
  bypass_celery: boolean
  advanced_options: TrialAdvancedOptions | null
  status: TrialStatus | string
  created_at: ISODateString
  updated_at: ISODateString
  results: TrialResult[]
  prompt: Prompt | null
  document_set: DocumentSet | null
  docs_done: number | null
  progress: number | null
  started_at: ISODateString | null
  finished_at: ISODateString | null
  meta: TrialMeta | null
  schema_snapshot: Record<string, unknown> | null
  prompt_snapshot: Record<string, unknown> | null
}

/** Lightweight trial row for list views. */
export interface TrialSummary {
  id: number
  project_id: number
  name: string | null
  description: string | null
  schema_id: number
  prompt_id: number
  document_ids: number[] | null
  document_set_id: number | null
  llm_model: string | null
  bypass_celery: boolean
  advanced_options: TrialAdvancedOptions | null
  status: TrialStatus | string
  created_at: ISODateString
  updated_at: ISODateString
  docs_done: number | null
  progress: number | null
  started_at: ISODateString | null
  finished_at: ISODateString | null
  meta: TrialMeta | null
  schema_snapshot: Record<string, unknown> | null
  prompt_snapshot: Record<string, unknown> | null
  prompt: Prompt | null
  document_set: DocumentSet | null
  documents_count: number
  results_count: number
  last_result_at: ISODateString | null
  error_count: number | null
  has_failures: boolean | null
}

/** Response for `GET /trials`. */
export interface PaginatedTrials {
  items: TrialSummary[]
  total: number
}

export interface TrialCreate {
  name?: string | null
  description?: string | null
  schema_id: number
  prompt_id: number
  document_ids?: number[] | null
  document_set_id?: number | null
  llm_model?: string | null
  api_key?: string | null
  base_url?: string | null
  bypass_celery?: boolean
  advanced_options?: TrialAdvancedOptions | null
}

export interface TrialUpdate {
  name?: string | null
  description?: string | null
}

export interface TrialFilter extends QueryParams {
  search?: string
  status?: TrialStatus | string
  date_from?: string
  date_to?: string
}
