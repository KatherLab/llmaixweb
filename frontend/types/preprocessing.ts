import type { ISODateString, QueryParams } from './api'
import type { PreprocessingStatus } from './enums'

export interface PreprocessingConfiguration {
  id: number
  project_id: number
  name: string
  description: string | null
  /** OCR/engine settings (engine, force_ocr, language, prompt, etc.). */
  additional_settings: Record<string, unknown> | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface PreprocessingConfigurationCreate {
  name: string
  description?: string | null
  additional_settings?: Record<string, unknown> | null
}

export interface PreprocessingConfigurationUpdate {
  name?: string | null
  description?: string | null
  additional_settings?: Record<string, unknown> | null
}

/**
 * Progress/meta payload carried on `PreprocessingTask.meta`.
 *
 * Note: the backend ORM column is `meta` (read by the WS broadcaster), but the
 * Pydantic `PreprocessingTask` response schema exposes it as `task_metadata`.
 * The frontend's WS merge (`useWsEntityUpdates.mergeWsEntity`) writes a
 * computed `meta` object onto the task at runtime with `progress` etc., and
 * the UI reads `task.meta`. We model both fields here.
 */
export interface PreprocessingTaskMeta {
  progress?: number
  total_files?: number
  completed_files?: number
  failed_files?: number
  eta_seconds?: number
  [key: string]: unknown
}

export interface FilePreprocessingTask {
  id: number
  preprocessing_task_id: number
  file_id: number
  status: PreprocessingStatus | string
  progress: number
  error_message: string | null
  document_count: number
  file_name: string | null
  processing_time: number | null
  warnings: Record<string, unknown> | null
  started_at: ISODateString | null
  completed_at: ISODateString | null
  document_ids: number[] | null
}

export interface PreprocessingTask {
  id: number
  project_id: number
  configuration_id: number | null
  rollback_on_cancel: boolean
  status: PreprocessingStatus | string
  message: string | null
  total_files: number
  processed_files: number
  failed_files: number
  skipped_files: number
  is_cancelled: boolean
  celery_task_id: string | null
  started_at: ISODateString | null
  completed_at: ISODateString | null
  estimated_completion: ISODateString | null
  created_at: ISODateString
  updated_at: ISODateString
  file_tasks: FilePreprocessingTask[]
  configuration: PreprocessingConfiguration | null
  task_metadata: Record<string, unknown> | null
  /** Runtime-computed progress meta (written by the WS merge layer). */
  meta?: PreprocessingTaskMeta | null
  /** Computed: sum of file_tasks[].document_count. */
  documents_count: number
}

export interface PreprocessingTaskCreate {
  file_ids: number[]
  configuration_id?: number | null
  inline_config?: PreprocessingConfigurationCreate | null
  force_reprocess?: boolean
  skip_existing?: boolean
  bypass_celery?: boolean
  api_key?: string | null
  base_url?: string | null
  rollback_on_cancel?: boolean
}

export interface DuplicatePreviewItem {
  file_id: number
  file_name: string
  existing_document_count: number
  existing_document_ids: number[]
  preprocessing_config_id: number | null
  config_name: string | null
}

export interface PdfEmbeddedTextInfo {
  file_id: number
  file_name: string
  has_embedded_text: boolean
  existing_document_ocr_method: string | null
}

/** Response for `POST /preprocess/preview`. */
export interface PreprocessingDuplicatePreview {
  has_duplicates: boolean
  files_with_duplicates: DuplicatePreviewItem[]
  total_files_to_process: number
  files_without_duplicates: number
  total_existing_documents: number
  pdfs_with_embedded_text: PdfEmbeddedTextInfo[]
  same_config_duplicates: DuplicatePreviewItem[]
}

/** Query params for `GET /preprocess`. */
export interface PreprocessingFilter extends QueryParams {
  search?: string
  status?: PreprocessingStatus | string
  date_from?: string
  date_to?: string
}
