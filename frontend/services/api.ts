import axios, { type AxiosRequestConfig } from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

// In dev mode (Vite dev server), use absolute URL to backend.
// In production (nginx serves SPA), use relative path — nginx proxies /api/ to backend.
const getBaseURL = () => {
  if (import.meta.env.DEV) {
    return 'http://localhost:8000/api/v1'
  }
  return '/api/v1'
}

/** Axios request config extended with internal retry bookkeeping. */
interface RetryableRequestConfig extends AxiosRequestConfig {
  _retried?: boolean
}

export const api = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor to add token from storage (works with Pinia too)
api.interceptors.request.use((config) => {
  // You may want to fetch token from store for SSR/reactivity
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor: on 401, attempt a silent refresh once before
// logging out; on 403 (forbidden, but authenticated) just reject.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config as RetryableRequestConfig | undefined

    // Only attempt refresh on a 401 from a real API call (not the refresh
    // endpoint itself, to avoid loops), and only once per request.
    const isRefreshCall = originalRequest?.url?.includes('/auth/refresh')
    if (status === 401 && !isRefreshCall && !originalRequest?._retried) {
      const authStore = useAuthStore()
      const newToken = await authStore.refresh()
      if (newToken && originalRequest) {
        originalRequest._retried = true
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      }
      // Refresh failed → fall through to logout.
      await authStore.logout({ serverSide: false })
      if (router.currentRoute.value.path !== '/login') {
        const toast = useToast()
        toast.error('Session expired. Please sign in again.', {
          timeout: 4000,
        })
        router.push('/login')
      }
    } else if (status === 401 || status === 403) {
      // 403 (authenticated but not allowed) or an unrefreshable 401: log out.
      const authStore = useAuthStore()
      await authStore.logout({ serverSide: status !== 403 })
      if (router.currentRoute.value.path !== '/login') {
        const toast = useToast()
        toast.error('Session expired. Please sign in again.', {
          timeout: 4000,
        })
        router.push('/login')
      }
    }
    // All errors are still available to the calling code
    return Promise.reject(error)
  },
)
