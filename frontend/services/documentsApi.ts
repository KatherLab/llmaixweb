/**
 * API service for document resources.
 * Replaces inline `api.get(\`/project/${projectId}/document\`)` calls.
 */
import { api } from './api'
import type { ApiBody, DocumentFilter } from '@/types'
import type { Document, DocumentDependencies, PaginatedDocuments } from '@/types'

export const documentsApi = {
  list(projectId: number | string, params: DocumentFilter = {}) {
    return api.get(`/project/${projectId}/document`, {
      params,
    }) as Promise<ApiBody<PaginatedDocuments>>
  },
  get(projectId: number | string, documentId: number | string) {
    return api.get(`/project/${projectId}/document/${documentId}`) as Promise<ApiBody<Document>>
  },
  // Promote an archived version to the new latest by copying its content — no
  // reprocessing. Returns the newly created latest document.
  restoreVersion(projectId: number | string, documentId: number | string) {
    return api.post(`/project/${projectId}/document/${documentId}/restore`) as Promise<
      ApiBody<Document>
    >
  },
  delete(projectId: number | string, documentId: number | string, cascade = false) {
    return api.delete(`/project/${projectId}/document/${documentId}`, {
      params: cascade ? { cascade: true } : undefined,
    }) as Promise<ApiBody<unknown>>
  },
  // Preview what a cascade delete of these documents would also remove.
  checkDependencies(projectId: number | string, documentIds: number[]) {
    return api.post(`/project/${projectId}/document/dependencies`, {
      document_ids: documentIds,
    }) as Promise<ApiBody<DocumentDependencies>>
  },
}
