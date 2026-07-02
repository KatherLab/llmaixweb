import type { ISODateString, QueryParams } from './api'

export interface Evaluation {
  id: number
  trial_id: number
  groundtruth_id: number
  metrics: Record<string, unknown>
  field_metrics: Record<string, unknown>
  document_metrics: Record<string, unknown>[]
  created_at: ISODateString
}

export interface EvaluationDetail {
  id: number
  trial_id: number
  groundtruth_id: number
  model: string
  metrics: Record<string, unknown>
  document_count: number
  fields: Record<string, unknown>
  documents: Record<string, unknown>[]
  confusion_matrices: Record<string, unknown> | null
  created_at: ISODateString
}

export interface EvaluationMetricDetail {
  document_id: number
  field_name: string
  ground_truth_value: string | null
  predicted_value: string | null
  is_correct: boolean
  error_type: string | null
  confidence_score: number | null
}

export interface DocumentEvaluationDetail {
  document_id: number
  accuracy: number
  correct_fields: number
  total_fields: number
  missing_fields: string[]
  incorrect_fields: string[]
  field_details: Record<string, EvaluationMetricDetail>
  error: string | null
  has_error: boolean
  document_name: string | null
}

export interface FieldEvaluationSummary {
  field_name: string
  accuracy: number
  total_count: number
  correct_count: number
  error_distribution: Record<string, number>
  sample_errors: Record<string, unknown>[]
  error_count: number | null
}

export interface EvaluationSummary {
  id: number
  trial_id: number
  groundtruth_id: number
  overall_metrics: Record<string, unknown>
  field_summaries: FieldEvaluationSummary[]
  document_summaries: DocumentEvaluationDetail[]
  confusion_matrices: Record<string, unknown> | null
  created_at: ISODateString
  total_errors: number | null
  error_documents: number[] | null
  warnings: string[] | null
}

export interface EvaluationError {
  document_id: number
  document_name: string | null
  error_type: string
  field_name: string | null
  ground_truth_value: string | null
  predicted_value: string | null
  confidence_score: number | null
  context: string | null
}

export interface EvaluationErrorSummary {
  evaluation_id: number
  total_errors: number
  error_types: Record<string, number>
  affected_documents: number
  errors: EvaluationError[]
}

export interface EvaluationCreate {
  trial_id: number
  groundtruth_id: number
  metrics: Record<string, unknown>
  field_metrics: Record<string, unknown>
  document_metrics: Record<string, unknown>[]
}

export interface EvaluationFilter extends QueryParams {
  search?: string
  date_from?: string
  date_to?: string
}
