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

  interface TimerEntry {
    /** Absent while the timer is paused. */
    handle?: ReturnType<typeof setTimeout>
    startedAt: number
    remaining: number
  }
  /** Pending dismissal timers keyed by toast id, so dismiss() can cancel them. */
  const timers = new Map<number, TimerEntry>()

  function startTimer(id: number, ms: number) {
    timers.set(id, {
      handle: setTimeout(() => dismiss(id), ms),
      startedAt: Date.now(),
      remaining: ms,
    })
  }

  function dismiss(id: number) {
    const entry = timers.get(id)
    if (entry) {
      if (entry.handle) clearTimeout(entry.handle)
      timers.delete(id)
    }
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  /** Pause the auto-dismiss countdown (e.g. while the toast is hovered/focused). */
  function pause(id: number) {
    const entry = timers.get(id)
    if (!entry?.handle) return
    clearTimeout(entry.handle)
    entry.handle = undefined
    entry.remaining -= Date.now() - entry.startedAt
  }

  /** Resume a paused countdown with the time it had left. */
  function resume(id: number) {
    const entry = timers.get(id)
    if (!entry || entry.handle) return
    startTimer(id, Math.max(entry.remaining, 500))
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

    if (timeout > 0) startTimer(id, timeout)
    return id
  }

  function clear() {
    for (const entry of timers.values()) {
      if (entry.handle) clearTimeout(entry.handle)
    }
    timers.clear()
    toasts.value = []
  }

  return { toasts, add, dismiss, pause, resume, clear }
})
