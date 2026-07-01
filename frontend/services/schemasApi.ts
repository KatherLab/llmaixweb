/**
 * API service for schema resources (`/project/{projectId}/schema/*`).
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type { Schema, SchemaCreate, SchemaFieldTypes, SchemaUpdate } from '@/types'

export const schemasApi = {
  list(projectId: number | string) {
    return api.get(`/project/${projectId}/schema`) as Promise<ApiBody<Schema[]>>
  },
  get(projectId: number | string, schemaId: number | string) {
    return api.get(`/project/${projectId}/schema/${schemaId}`) as Promise<ApiBody<Schema>>
  },
  create(projectId: number | string, payload: SchemaCreate) {
    return api.post(`/project/${projectId}/schema`, payload) as Promise<ApiBody<Schema>>
  },
  update(projectId: number | string, schemaId: number | string, payload: SchemaUpdate) {
    return api.put(`/project/${projectId}/schema/${schemaId}`, payload) as Promise<ApiBody<Schema>>
  },
  delete(projectId: number | string, schemaId: number | string) {
    return api.delete(`/project/${projectId}/schema/${schemaId}`) as Promise<ApiBody<unknown>>
  },
  getFieldTypes(projectId: number | string, schemaId: number | string) {
    return api.get(`/project/${projectId}/schema/${schemaId}/field_types`) as Promise<
      ApiBody<SchemaFieldTypes>
    >
  },
}
