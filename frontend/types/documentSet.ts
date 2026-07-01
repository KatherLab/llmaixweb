import type { ISODateString, Paginated, QueryParams } from './api'
import type { Document } from './document'
import type { PreprocessingConfiguration } from './preprocessing'

export interface DocumentSet {
  id: number
  project_id: number
  name: string
  description: string | null
  tags: string[]
  is_auto_generated: boolean
  preprocessing_config_id: number | null
  created_at: ISODateString
  updated_at: ISODateString
  documents: Document[]
}

export interface DocumentSetSummary {
  id: number
  project_id: number
  name: string
  description: string | null
  tags: string[]
  is_auto_generated: boolean
  preprocessing_config: PreprocessingConfiguration | null
  created_at: ISODateString
  updated_at: ISODateString
  document_count: number
  trials_count: number
}

export type PaginatedDocumentSets = Paginated<DocumentSetSummary>

export interface DocumentSetStats {
  trials_count: number
  extractions_count: number
  last_used: ISODateString | null
}

export interface DocumentSetDetail extends DocumentSet {
  usage_stats: DocumentSetStats
  preprocessing_config: PreprocessingConfiguration | null
}

export interface DocumentSetCreate {
  name: string
  description?: string | null
  tags?: string[]
  is_auto_generated?: boolean
  preprocessing_config_id?: number | null
  trial_id?: number | null
  document_ids?: number[]
}

export interface DocumentSetUpdate {
  name?: string | null
  description?: string | null
  tags?: string[]
  document_ids?: number[]
}

export interface DocumentSetFromTrial {
  name: string
  description?: string | null
  tags?: string[]
}

export interface DocumentSetFilter extends QueryParams {
  search?: string
  date_from?: string
  date_to?: string
}
