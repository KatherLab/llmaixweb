// src/composables/useToast.js

import { useToastStore } from '@/stores/toast'

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
 * @returns {{
 *   success: (msg: string, opts?: {timeout?: number, position?: string}) => number,
 *   error:   (msg: string, opts?: {timeout?: number, position?: string}) => number,
 *   warning: (msg: string, opts?: {timeout?: number, position?: string}) => number,
 *   info:    (msg: string, opts?: {timeout?: number, position?: string}) => number,
 *   dismiss: (id: number) => void,
 *   clear:   () => void,
 * }}
 */
export function useToast() {
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
