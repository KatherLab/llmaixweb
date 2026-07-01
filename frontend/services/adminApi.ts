/**
 * API service for admin resources (`/admin/*`).
 * Covers runtime settings (DB-backed overrides) and Celery monitoring.
 */
import { api } from './api'
import type { ApiBody } from '@/types'
import type {
  AdminSettingDeleted,
  AdminSettings,
  AdminSettingsUpdate,
  AdminSettingsUpdated,
  CeleryQueuesResponse,
  CeleryTaskRevokeResponse,
  CeleryWorkersResponse,
} from '@/types'

export const adminApi = {
  // Settings
  getSettings() {
    return api.get('/admin/settings') as Promise<ApiBody<AdminSettings>>
  },
  // Bulk update of non-secret, non-readonly settings.
  updateSettings(payload: AdminSettingsUpdate) {
    return api.put('/admin/settings', payload) as Promise<ApiBody<AdminSettingsUpdated>>
  },
  // Set a single secret value.
  setSecret(key: string, value: string) {
    return api.put('/admin/settings', { [key]: value }) as Promise<ApiBody<AdminSettingsUpdated>>
  },
  // Clear a single secret (empty string = unset on the backend).
  clearSecret(key: string) {
    return api.put('/admin/settings', { [key]: '' }) as Promise<ApiBody<AdminSettingsUpdated>>
  },
  deleteSetting(key: string) {
    return api.delete(`/admin/settings/${key}`) as Promise<ApiBody<AdminSettingDeleted>>
  },

  // Celery monitoring
  celeryWorkers() {
    return api.get('/admin/celery/workers') as Promise<ApiBody<CeleryWorkersResponse>>
  },
  celeryQueues() {
    return api.get('/admin/celery/queues') as Promise<ApiBody<CeleryQueuesResponse>>
  },
  celeryTask(taskId: string) {
    return api.get(`/admin/celery/tasks/${taskId}`) as Promise<ApiBody<Record<string, unknown>>>
  },
  revokeTask(taskId: string) {
    return api.post(`/admin/celery/revoke/${taskId}`) as Promise<ApiBody<CeleryTaskRevokeResponse>>
  },
  celeryFailedTasks() {
    return api.get('/admin/celery/failed-tasks') as Promise<ApiBody<Record<string, unknown>[]>>
  },
}
