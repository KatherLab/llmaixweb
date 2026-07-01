// src/stores/toast.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Global toast notification store.
 *
 * Backs the `useToast()` composable. Lives in a Pinia store (rather than a
 * component) so toasts can be fired from anywhere — including non-setup
 * contexts like the Axios response interceptor in `services/api.ts` — without
 * needing `getCurrentInstance()`.
 */

/** Default auto-dismiss delay (ms). Matches the previous global config. */
const DEFAULT_TIMEOUT = 4000

/** Maximum toasts shown at once; older ones are pruned to avoid flooding. */
const MAX_TOASTS = 5

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  message: string
  type: ToastType | string
  timeout: number
}

export interface ToastOptions {
  type?: ToastType
  timeout?: number
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  // Monotonic id counter — deterministic, no Math.random/Date.now.
  let seq = 0
  /** Pending dismissal timers keyed by toast id, so dismiss() can cancel them. */
  const timers = new Map<number, ReturnType<typeof setTimeout>>()

  function dismiss(id: number) {
    const handle = timers.get(id)
    if (handle) {
      clearTimeout(handle)
      timers.delete(id)
    }
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  /**
   * Push a toast.
   * @returns The toast id (for programmatic dismiss).
   */
  function add(message: string, { type = 'info', timeout = DEFAULT_TIMEOUT }: ToastOptions = {}) {
    const id = ++seq
    toasts.value.push({ id, message, type, timeout })

    // Prune oldest when over capacity.
    while (toasts.value.length > MAX_TOASTS) {
      const oldest = toasts.value[0]
      if (oldest) dismiss(oldest.id)
    }

    if (timeout > 0) {
      const handle = setTimeout(() => dismiss(id), timeout)
      timers.set(id, handle)
    }
    return id
  }

  function clear() {
    for (const handle of timers.values()) clearTimeout(handle)
    timers.clear()
    toasts.value = []
  }

  return { toasts, add, dismiss, clear }
})
