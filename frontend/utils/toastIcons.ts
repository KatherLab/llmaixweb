/**
 * Shared toast type → icon + color metadata.
 *
 * Mirrors the `utils/schemaTypeIcons.js` pattern: a single source of truth for
 * the visual treatment of each toast variant, so `ToastItem` stays declarative.
 *
 * Icons are sourced from `@lucide/vue` (the single icon set used app-wide).
 */
import type { Component } from 'vue'
import { CircleCheckBig, CircleAlert, AlertTriangle, Info } from '@lucide/vue'

export interface ToastVisual {
  /** Lucide icon component. */
  icon: Component
  /** Tailwind classes tinting the icon glyph. */
  iconClass: string
  /** Tailwind classes for the tinted icon background chip. */
  chipClass: string
  /** Tailwind classes for the left accent + progress bar. */
  accentClass: string
}

/** @type {Record<string, ToastVisual>} */
export const TOAST_VISUALS: Record<string, ToastVisual> = {
  success: {
    icon: CircleCheckBig,
    iconClass: 'text-green-600 dark:text-green-400',
    chipClass: 'bg-green-100 dark:bg-green-500/15',
    accentClass: 'bg-green-500',
  },
  error: {
    icon: CircleAlert,
    iconClass: 'text-red-600 dark:text-red-400',
    chipClass: 'bg-red-100 dark:bg-red-500/15',
    accentClass: 'bg-red-500',
  },
  warning: {
    icon: AlertTriangle,
    iconClass: 'text-amber-600 dark:text-amber-400',
    chipClass: 'bg-amber-100 dark:bg-amber-500/15',
    accentClass: 'bg-amber-500',
  },
  info: {
    icon: Info,
    iconClass: 'text-blue-600 dark:text-blue-400',
    chipClass: 'bg-blue-100 dark:bg-blue-500/15',
    accentClass: 'bg-blue-500',
  },
}

/** Fallback visual for unknown types. */
const DEFAULT_VISUAL: ToastVisual = TOAST_VISUALS.info ?? {
  icon: Info,
  iconClass: 'text-blue-600 dark:text-blue-400',
  chipClass: 'bg-blue-100 dark:bg-blue-500/15',
  accentClass: 'bg-blue-500',
}

/**
 * Look up the visual metadata for a toast type.
 * @param {string} type
 * @returns {ToastVisual}
 */
export function getToastVisual(type: string | null | undefined): ToastVisual {
  return (type && TOAST_VISUALS[type]) || DEFAULT_VISUAL
}
