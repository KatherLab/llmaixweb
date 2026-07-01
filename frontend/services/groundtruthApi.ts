/**
 * API service for ground-truth resources (`/project/{projectId}/groundtruth/*`).
 * Includes the nested schema-mapping sub-resource used during evaluation setup.
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type {
  FieldMapping,
  FieldMappingCreate,
  FieldMappingStatus,
  GroundTruth,
  GroundTruthPreview,
} from '@/types'

const MULTIPART = { 'Content-Type': 'multipart/form-data' }

export const groundtruthApi = {
  list(projectId: number | string) {
    return api.get(`/project/${projectId}/groundtruth`) as Promise<ApiBody<GroundTruth[]>>
  },
  get(projectId: number | string, gtId: number | string) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}`) as Promise<ApiBody<GroundTruth>>
  },
  // Multipart upload. `formData` includes `file`, `name`, `format`.
  upload(projectId: number | string, formData: FormData) {
    return api.post(`/project/${projectId}/groundtruth`, formData, {
      headers: MULTIPART,
    }) as Promise<ApiBody<GroundTruth>>
  },
  // Rename via multipart FormData (only the `name` field is sent).
  update(projectId: number | string, gtId: number | string, formData: FormData) {
    return api.put(`/project/${projectId}/groundtruth/${gtId}`, formData, {
      headers: MULTIPART,
    }) as Promise<ApiBody<GroundTruth>>
  },
  delete(projectId: number | string, gtId: number | string) {
    return api.delete(`/project/${projectId}/groundtruth/${gtId}`) as Promise<ApiBody<unknown>>
  },

  preview(projectId: number | string, gtId: number | string) {
    return api.get(`/project/${projectId}/groundtruth/${gtId}/preview`) as Promise<
      ApiBody<GroundTruthPreview>
    >
  },
  setIdColumn(projectId: number | string, gtId: number | string, payload: Record<string, unknown>) {
    return api.put(`/project/${projectId}/groundtruth/${gtId}/id-column`, payload) as Promise<
      ApiBody<GroundTruth>
    >
  },

  // Schema field mappings
  getMappings(projectId: number | string, gtId: number | string, schemaId: number | string) {
    return api.get(
      `/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`,
    ) as Promise<ApiBody<FieldMapping[]>>
  },
  setMappings(
    projectId: number | string,
    gtId: number | string,
    schemaId: number | string,
    mappings: FieldMappingCreate[],
  ) {
    return api.post(
      `/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping`,
      mappings,
    ) as Promise<ApiBody<FieldMapping[]>>
  },
  getMappingStatus(projectId: number | string, gtId: number | string, schemaId: number | string) {
    return api.get(
      `/project/${projectId}/groundtruth/${gtId}/schema/${schemaId}/mapping/status`,
    ) as Promise<ApiBody<FieldMappingStatus>>
  },
}
