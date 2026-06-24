// src/stores/firstAdmin.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { usersApi } from '@/services/usersApi'

export const useFirstAdminStore = defineStore('firstAdmin', () => {
  const needsFirstAdmin = ref(false)
  const checked = ref(false)

  async function checkFirstAdmin() {
    try {
      const res = await usersApi.firstAdminCheck()
      needsFirstAdmin.value = !!res.data.allow_first_admin_setup
    } catch (e) {
      needsFirstAdmin.value = false
    } finally {
      checked.value = true
    }
    return needsFirstAdmin.value
  }

  function reset() {
    checked.value = false
    needsFirstAdmin.value = false
  }

  return { needsFirstAdmin, checked, checkFirstAdmin, reset }
})
