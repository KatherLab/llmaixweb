/**
 * API service for admin resources (`/admin/*`).
 * Covers runtime settings (DB-backed overrides) and Celery monitoring.
 */
import { api } from './api'

export const adminApi = {
  // Settings
  getSettings() {
    return api.get('/admin/settings')
  },
  // Bulk update of non-secret, non-readonly settings.
  updateSettings(payload) {
    return api.put('/admin/settings', payload)
  },
  // Set a single secret value.
  setSecret(key, value) {
    return api.put('/admin/settings', { [key]: value })
  },
  // Clear a single secret (empty string = unset on the backend).
  clearSecret(key) {
    return api.put('/admin/settings', { [key]: '' })
  },
  deleteSetting(key) {
    return api.delete(`/admin/settings/${key}`)
  },

  // Celery monitoring
  celeryWorkers() {
    return api.get('/admin/celery/workers')
  },
  celeryQueues() {
    return api.get('/admin/celery/queues')
  },
  celeryTask(taskId) {
    return api.get(`/admin/celery/tasks/${taskId}`)
  },
  revokeTask(taskId) {
    return api.post(`/admin/celery/revoke/${taskId}`)
  },
  celeryFailedTasks() {
    return api.get('/admin/celery/failed-tasks')
  },
}
