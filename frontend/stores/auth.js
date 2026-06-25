// src/stores/auth.js

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'
import { usersApi } from '@/services/usersApi'
import { websocketService } from '@/services/websocket'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))
  const isInitialized = ref(false)

  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function initialize() {
    if (isInitialized.value) {
      return true
    }

    if (token.value) {
      try {
        await fetchUser()
      } catch (error) {
        console.error('Failed to fetch user during init:', error)
        await logout()
        return false
      }
    }

    isInitialized.value = true
    return true
  }

  async function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  async function fetchUser() {
    const storedToken = localStorage.getItem('token')
    if (!storedToken) {
      await logout()
      return false
    }

    api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`

    try {
      const response = await usersApi.me()
      user.value = response.data
      return true
    } catch (error) {
      console.error('Failed to fetch user:', error.message || error)
      await logout()
      return false
    }
  }

  async function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    // Tear down the WebSocket so it doesn't linger with a now-revoked token.
    websocketService.disconnect()
    isInitialized.value = false
  }

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    setToken,
    fetchUser,
    logout,
    initialize,
  }
})
