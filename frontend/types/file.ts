import type { ISODateString, Paginated, QueryParams } from './api'
import type { FileCreator, FileStorageType, FileType, PreprocessingStrategy } from './enums'

/**
 * CSV/XLSX import configuration stored on `File.file_metadata`.
 * Shape varies by strategy; modeled loosely as the frontend only reads a few keys.
 */
export type FileMetadata = Record<string, unknown> & {
  text_columns?: string[]
  case_id_column?: string | null
  delimiter?: string
  encoding?: string
  sheet?: string
  has_header?: boolean
}

export interface File {
  id: number
  project_id: number
  file_name: string | null
  file_type: FileType | string | null
  file_uuid: string | null
  file_storage_type: FileStorageType | string | null
  description: string | null
  file_size: number | null
  file_hash: string | null
  file_metadata: FileMetadata | null
  preprocessing_strategy: PreprocessingStrategy | null
  file_creator: FileCreator
  created_at: ISODateString
  updated_at: ISODateString
}

export type PaginatedFiles = Paginated<File>

/** Query params for `GET /files`. */
export interface FileFilter extends QueryParams {
  search?: string
  file_type?: string
  file_creator?: FileCreator
  date_from?: string
  date_to?: string
  min_size?: number
  max_size?: number
}
