/**
 * API service for LLM resources (`/project/llm/*`).
 * Model listing + connection/schema testing for trial creation.
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type {
  LlmConnectionRequest,
  LlmConnectionResponse,
  LlmModelSchemaTestRequest,
  LlmModelSchemaTestResponse,
  LlmModelTestRequest,
  LlmModelsResponse,
} from '@/types'

export const llmApi = {
  // All `/project/llm/*` routes are POST and read credentials from the request
  // body (LLMConnectionRequest & friends) rather than query params — that keeps
  // api_key / base_url out of URLs and access logs. Send `params` as the JSON
  // body, not as query string.
  models(params: LlmConnectionRequest = {}) {
    return api.post('/project/llm/models', params) as Promise<ApiBody<LlmModelsResponse>>
  },
  testConnection(params: LlmModelTestRequest = {}) {
    return api.post('/project/llm/test-connection', params) as Promise<
      ApiBody<LlmConnectionResponse>
    >
  },
  testModelSchema(params: LlmModelSchemaTestRequest) {
    return api.post('/project/llm/test-model-schema', params) as Promise<
      ApiBody<LlmModelSchemaTestResponse>
    >
  },
}
