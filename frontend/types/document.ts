import type { ISODateString, QueryParams } from './api'
import type { File } from './file'
import type { PreprocessingConfiguration } from './preprocessing'

/** Document metadata (page_number, row_number, source_columns, ocr method, etc.). */
export type DocumentMetaData = Record<string, unknown> & {
  page_number?: number
  row_number?: number
  source_columns?: string[]
  ocr_method?: string
  extraction_method?: string
}

/** Full document, including extracted text. Returned by `GET /document/{id}`. */
export interface Document {
  id: number
  project_id: number
  text: string
  document_name: string | null
  meta_data: DocumentMetaData | null
  original_file_id: number
  original_file: File | null
  preprocessed_file_id: number | null
  preprocessed_file: File | null
  preprocessing_config_id: number
  preprocessing_config: PreprocessingConfiguration | null
  is_latest: boolean
  version_of: number | null
  created_at: ISODateString
  updated_at: ISODateString
}

/** Lightweight document row (no `text`) used in list/picker views. */
export interface DocumentListItem {
  id: number
  project_id: number
  document_name: string | null
  meta_data: DocumentMetaData | null
  original_file_id: number
  original_file: File | null
  preprocessed_file_id: number | null
  preprocessed_file: File | null
  preprocessing_config_id: number
  preprocessing_config: PreprocessingConfiguration | null
  is_latest: boolean
  version_of: number | null
  created_at: ISODateString
  updated_at: ISODateString
}

/** Response for `GET /document`. */
export interface PaginatedDocuments {
  items: DocumentListItem[]
  total: number
  recent_count: number | null
  today_count: number | null
  week_count: number | null
  month_count: number | null
}

/** Count of affected resources plus a few names for display. */
export interface DocumentDependencyGroup {
  count: number
  names: string[]
}

/** Impact preview for a cascade delete (`POST /document/dependencies`). */
export interface DocumentDependencies {
  trials: DocumentDependencyGroup
  document_sets: DocumentDependencyGroup
  trial_results: number
  evaluation_metrics: number
  evaluations: number
}

export interface DocumentCreate {
  original_file_id: number
  text: string
  document_name?: string | null
  meta_data?: DocumentMetaData | null
}

export interface DocumentFilter extends QueryParams {
  search?: string
  preprocessing_config_id?: number
  preprocessing_task_id?: number
  date_from?: string
  date_to?: string
  file_ids?: number[]
  status?: string
  tags?: string[]
  document_set_id?: number
  compute_stats?: boolean
  sort?: 'created_desc' | 'created_asc'
}

export interface DocumentBulkAction {
  action: 'add_to_set' | 'remove_from_set' | 'delete' | 'reprocess'
  document_ids: number[]
  target_set_id?: number | null
  force?: boolean
}

export interface SmartDocumentSelection {
  mode: string
  source_trial_id?: number | null
  preprocessing_config_id?: number | null
  date_from?: string | null
  date_to?: string | null
  tags?: string[] | null
  limit?: number | null
  exclude_ids?: number[]
}
