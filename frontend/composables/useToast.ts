// src/composables/useToast.ts

import { useToastStore } from '@/stores/toast'
import type { ToastOptions } from '@/stores/toast'

/** Return type of `useToast()` — mirrors the previous `vue-toastification` surface. */
export interface UseToast {
  success: (msg: string, opts?: ToastOptions) => number
  error: (msg: string, opts?: ToastOptions) => number
  warning: (msg: string, opts?: ToastOptions) => number
  info: (msg: string, opts?: ToastOptions) => number
  dismiss: (id: number) => void
  clear: () => void
}

/**
 * Toast notification composable.
 *
 * Drop-in replacement for `vue-toastification`'s `useToast`. Returns a stable
 * API object whose methods mirror the previous surface (`success` / `error` /
 * `warning` / `info`), so call sites need only change their import path.
 *
 * Unlike the old composable, this works from any context — including plain
 * modules such as `services/api.js` — because the backing state lives in a
 * Pinia store rather than relying on `getCurrentInstance()`.
 *
 * @returns toast methods backed by the toast store.
 */
export function useToast(): UseToast {
  const store = useToastStore()

  /**
   * `position` is accepted for backward compatibility with the previous API
   * but ignored — toasts always render top-right (the only position used app-wide).
   */
  return {
    success: (msg, opts) => store.add(msg, { ...opts, type: 'success' }),
    error: (msg, opts) => store.add(msg, { ...opts, type: 'error' }),
    warning: (msg, opts) => store.add(msg, { ...opts, type: 'warning' }),
    info: (msg, opts) => store.add(msg, { ...opts, type: 'info' }),
    dismiss: (id) => store.dismiss(id),
    clear: () => store.clear(),
  }
}
