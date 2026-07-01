// src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { websocketService } from '@/services/websocket'
import type { LogoutOptions } from '@/types'
import type { UserResponse } from '@/types'

const REFRESH_KEY = 'refreshToken'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserResponse | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const isInitialized = ref(false)
  // Guards the silent-refresh path so concurrent 401s only trigger one refresh.
  let _refreshing: Promise<string | null> | null = null

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

  async function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  /**
   * Set both access + refresh tokens and load the user. Used by the SSO
   * callback route and any flow that receives a token pair at once.
   */
  async function setSession(accessToken: string, newRefreshToken?: string | null) {
    await setToken(accessToken)
    if (newRefreshToken) {
      refreshToken.value = newRefreshToken
      localStorage.setItem(REFRESH_KEY, newRefreshToken)
    }
    return fetchUser()
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
      console.error('Failed to fetch user:', (error as Error)?.message || error)
      await logout()
      return false
    }
  }

  /**
   * Silently refresh the access token using the stored refresh token.
   * Returns the new access token, or null if refresh failed (caller should
   * log out). Concurrent callers share a single in-flight refresh.
   */
  async function refresh(): Promise<string | null> {
    const storedRefresh = localStorage.getItem(REFRESH_KEY)
    if (!storedRefresh) {
      return null
    }
    if (_refreshing) {
      return _refreshing
    }
    _refreshing = (async () => {
      try {
        const resp = await authApi.refresh(storedRefresh)
        await setToken(resp.data.access_token)
        if (resp.data.refresh_token) {
          refreshToken.value = resp.data.refresh_token
          localStorage.setItem(REFRESH_KEY, resp.data.refresh_token)
        }
        return resp.data.access_token
      } catch (e) {
        console.error('Token refresh failed:', e)
        return null
      } finally {
        _refreshing = null
      }
    })()
    return _refreshing
  }

  async function logout(opts: LogoutOptions = { serverSide: true, everywhere: false }) {
    // Best-effort server-side revoke. Don't block UI on it; if it fails the
    // token is still cleared client-side and will expire naturally.
    if (opts.serverSide && refreshToken.value) {
      try {
        await authApi.logout(refreshToken.value, !!opts.everywhere)
      } catch {
        /* ignore — clearing locally is the source of truth */
      }
    }
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem(REFRESH_KEY)
    delete api.defaults.headers.common['Authorization']
    // Tear down the WebSocket so it doesn't linger with a now-revoked token.
    websocketService.disconnect()
    isInitialized.value = false
  }

  return {
    user,
    token,
    refreshToken,
    isAuthenticated,
    isAdmin,
    setToken,
    setSession,
    fetchUser,
    refresh,
    logout,
    initialize,
  }
})
