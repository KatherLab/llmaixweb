/**
 * API service for the version endpoint (`/version`).
 * Used by the app footer to display backend version + git commit.
 */
import { api } from './api'
import type { ApiBody } from '@/types'

export interface VersionResponse {
  backend_version?: string
  backend_git_commit?: string
  backend_description?: string
  /** Legacy fallbacks — the backend sends the `backend_*` fields above. */
  version?: string
  commit?: string
  [key: string]: unknown
}

export const versionApi = {
  get() {
    return api.get('/version') as Promise<ApiBody<VersionResponse>>
  },
}
