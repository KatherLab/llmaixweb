// src/stores/publicSettings.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/services/authApi'
import type { PublicAuthSettings } from '@/types'

/**
 * Holds the unauthenticated public settings (`GET /auth/settings`) — including
 * the site-wide banner config — so any page (logged in or not) can read them
 * without each component re-fetching. Fetched once on app load.
 */
export const usePublicSettingsStore = defineStore('publicSettings', () => {
  const settings = ref<PublicAuthSettings | null>(null)
  const loaded = ref(false)

  async function fetch(force = false) {
    if (loaded.value && !force) return settings.value
    try {
      const res = await authApi.getSettings()
      settings.value = res.data
    } catch (e) {
      // Best-effort: a missing/errored settings call just means no banner.
      console.error('Failed to load public settings:', e)
    } finally {
      loaded.value = true
    }
    return settings.value
  }

  return { settings, loaded, fetch }
})
