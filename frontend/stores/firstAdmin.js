// src/stores/firstAdmin.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { usersApi } from '@/services/usersApi'

export const useFirstAdminStore = defineStore('firstAdmin', () => {
  const needsFirstAdmin = ref(false)
  const checked = ref(false)
  // Set when the first-admin check itself failed (e.g. backend unreachable).
  // The router guard still proceeds (best-effort) so the app isn't hard-blocked
  // on a transient network error, but callers can surface this to the user.
  const checkError = ref(null)

  async function checkFirstAdmin() {
    try {
      const res = await usersApi.firstAdminCheck()
      needsFirstAdmin.value = !!res.data.allow_first_admin_setup
      checkError.value = null
    } catch (e) {
      // Don't block the app on a transient error — assume no first-admin needed
      // so login proceeds, but record the failure so the UI can warn the user.
      needsFirstAdmin.value = false
      checkError.value = e
      console.error('Failed to check first-admin state:', e)
    } finally {
      checked.value = true
    }
    return needsFirstAdmin.value
  }

  function reset() {
    checked.value = false
    needsFirstAdmin.value = false
    checkError.value = null
  }

  return { needsFirstAdmin, checked, checkError, checkFirstAdmin, reset }
})
