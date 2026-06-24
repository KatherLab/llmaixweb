/**
 * API service for the version endpoint (`/version`).
 * Used by the app footer to display backend version + git commit.
 */
import { api } from './api'

export const versionApi = {
  get() {
    return api.get('/version')
  },
}
