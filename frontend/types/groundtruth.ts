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
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  format: string | null
}

export interface FieldMappingStatus {
  is_configured: boolean
  mappings: FieldMapping[]
  schema_fields: string[]
  ground_truth_fields: string[]
}
