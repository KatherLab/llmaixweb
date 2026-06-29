// src/stores/toast.js

import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Global toast notification store.
 *
 * Backs the `useToast()` composable. Lives in a Pinia store (rather than a
 * component) so toasts can be fired from anywhere — including non-setup
 * contexts like the Axios response interceptor in `services/api.js` — without
 * needing `getCurrentInstance()`.
 *
 * Replaces the unmaintained `vue-toastification@2.0.0-rc.5` dependency. The
 * public surface (`success` / `error` / `warning` / `info`) is intentionally
 * kept identical to ease the migration.
 */

/** Default auto-dismiss delay (ms). Matches the previous global config. */
const DEFAULT_TIMEOUT = 4000

/** Maximum toasts shown at once; older ones are pruned to avoid flooding. */
const MAX_TOASTS = 5

export const useToastStore = defineStore('toast', () => {
  /** @type {import('vue').Ref<Array<{id: number, message: string, type: string, timeout: number}>>} */
  const toasts = ref([])

  // Monotonic id counter — deterministic, no Math.random/Date.now.
  let seq = 0
  /** Pending dismissal timers keyed by toast id, so dismiss() can cancel them. */
  const timers = new Map()

  function dismiss(id) {
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
   * @param {string} message - Toast body text.
   * @param {{type?: string, timeout?: number}} [opts]
   * @returns {number} The toast id (for programmatic dismiss).
   */
  function add(message, { type = 'info', timeout = DEFAULT_TIMEOUT } = {}) {
    const id = ++seq
    toasts.value.push({ id, message, type, timeout })

    // Prune oldest when over capacity.
    while (toasts.value.length > MAX_TOASTS) {
      const oldest = toasts.value[0]
      dismiss(oldest.id)
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
