import axios from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'vue-toastification'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Add request interceptor to add token from storage (works with Pinia too)
api.interceptors.request.use(config => {
  // You may want to fetch token from store for SSR/reactivity
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Add response interceptor: show toast and auto-logout on 401/403
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      const authStore = useAuthStore()
      await authStore.logout()
      // Show toast only if not already on login
      if (router.currentRoute.value.path !== '/login') {
        const toast = useToast()
        toast.error('Session expired. Please sign in again.', {
          timeout: 4000,
          position: 'top-right'
        })
        router.push('/login')
      }
    }
    // All errors are still available to the calling code
    return Promise.reject(error)
  }
)
