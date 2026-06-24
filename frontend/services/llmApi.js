/**
 * API service for LLM resources (`/project/llm/*`).
 * Model listing + connection/schema testing for trial creation.
 */
import { api } from './api'

export const llmApi = {
  // All `/project/llm/*` routes are POST and read credentials from the request
  // body (LLMConnectionRequest & friends) rather than query params — that keeps
  // api_key / base_url out of URLs and access logs. Send `params` as the JSON
  // body, not as query string.
  models(params = {}) {
    return api.post('/project/llm/models', params)
  },
  testConnection(params = {}) {
    return api.post('/project/llm/test-connection', params)
  },
  testModelSchema(params = {}) {
    return api.post('/project/llm/test-model-schema', params)
  },
}
