/**
 * Shared string-literal-union types mirroring the backend enums in
 * `backend/src/utils/enums.py` and `backend/src/models/project.py`.
 *
 * The ORM stores these as Python enums; the Pydantic response schemas
 * serialize them to their string values, so the frontend always sees the
 * bare string.
 */

export type UserRole = 'admin' | 'user'

export type FileCreator = 'user' | 'system'

export type FileStorageType = 'local' | 's3'

export type ProjectStatus = 'active' | 'inactive' | 'completed' | 'archived'

export type PreprocessingStrategy = 'full_document' | 'row_by_row' | 'custom'

/** Status shared by PreprocessingTask, FilePreprocessingTask (and the legacy PreprocessingStatus enum). */
export type PreprocessingStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'

export type TrialStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'

export type TrialResultStatus =
  | 'success'
  | 'failed'
  | 'incomplete'
  | 'invalid_json'
  | 'schema_invalid'
  | 'refused'
  | 'provider_error'

export type FieldType = 'string' | 'number' | 'boolean' | 'category' | 'date' | 'array' | 'object'

export type ComparisonMethod = 'exact' | 'fuzzy' | 'numeric' | 'boolean' | 'category' | 'date'

/** MIME-like file type strings from FileType enum. `mixed` is used for aggregated rows. */
export type FileType =
  | 'application/pdf'
  | 'application/msword'
  | 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  | 'application/vnd.ms-excel'
  | 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  | 'image/jpeg'
  | 'image/png'
  | 'image/svg+xml'
  | 'text/plain'
  | 'text/csv'
  | 'mixed'
  | 'application/xml'
  | 'application/json'
  | 'text/rtf'

/** OCR engine identifiers stored on Document.meta_data / PreprocessingConfiguration.additional_settings. */
export type PreprocessingMethod = 'tesseract' | 'vision_ocr' | 'marker'
