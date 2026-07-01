/**
 * Response from `POST /llm/models`.
 *
 * The backend returns `models` as a flat list of model-id strings
 * (`[model.id for model in response.data]` in `get_available_models`),
 * NOT an array of objects — so `models` is `string[]`.
 */
export interface LlmModelsResponse {
  success: boolean
  models: string[]
  message?: string
  error_type?: string
}

export interface LlmConnectionResponse {
  success: boolean
  message: string
  error_type?: string
}

export interface LlmModelSchemaTestResponse {
  success: boolean
  message: string
  error_type?: string
  [key: string]: unknown
}

export interface LlmConnectionRequest {
  api_key?: string | null
  base_url?: string | null
}

export interface LlmModelTestRequest extends LlmConnectionRequest {
  llm_model?: string | null
}

export interface LlmModelSchemaTestRequest extends LlmModelTestRequest {
  project_id: number
  schema_id?: number | null
  max_completion_tokens?: number | null
  temperature?: number | null
  reasoning_effort?: 'low' | 'medium' | 'high' | null
}
