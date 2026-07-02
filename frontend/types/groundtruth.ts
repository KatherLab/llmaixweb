import type { ISODateString } from './api'
import type { ComparisonMethod, FieldType } from './enums'

export interface FieldMapping {
  id: number
  ground_truth_id: number
  schema_id: number
  schema_field: string
  ground_truth_field: string
  field_type: FieldType
  comparison_method: ComparisonMethod
  comparison_options: Record<string, unknown> | null
  created_at: ISODateString | null
}

export interface FieldMappingCreate {
  schema_field: string
  ground_truth_field: string
  schema_id: number
  field_type: FieldType
  comparison_method: ComparisonMethod
  comparison_options?: Record<string, unknown> | null
}

export interface GroundTruth {
  id: number
  project_id: number
  name: string | null
  format: string | null
  file_uuid: string
  field_mappings: FieldMapping[]
  id_column_name: string | null
  created_at: ISODateString
  updated_at: ISODateString
}

export interface GroundTruthCreate {
  name: string
  format: string
}

export interface GroundTruthUpdate {
  name?: string | null
  field_mappings?: FieldMappingCreate[] | null
}

/** Response for `GET /groundtruth/{id}/preview`. */
export interface GroundTruthPreview {
  /** Dotted field paths discovered in the ground-truth data. */
  fields: string[]
  /** `{ "path": "type" }` for each discovered field. */
  field_types: Record<string, string>
  /** Up to 3 sample ground-truth records. */
  preview_data: Record<string, unknown>
  /** File columns available as the ID column (CSV/XLSX only). */
  available_columns: string[]
  /** Currently configured ID column (may be null). */
  current_id_column: string | null
}

/** Response for `GET /groundtruth/{id}/schema/{schemaId}/mapping/status`. */
export interface FieldMappingStatus {
  has_mappings: boolean
  mapping_count: number
  schema_field_count: number
  mapping_complete: boolean
  groundtruth_name: string | null
  schema_name: string | null
}
