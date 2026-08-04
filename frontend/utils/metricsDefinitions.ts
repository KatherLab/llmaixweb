/**
 * Plain-language definitions for evaluation metrics + error types.
 *
 * Single source of truth so the failure examiner, field tables, and any
 * summary view stay consistent. Used via the `Tooltip` component and as
 * inline helper text.
 *
 * All user-visible prose lives in the i18n catalog
 * (`evaluation.metric_defs.*`, `evaluation.error_types.*`,
 * `groundtruth.comparison_methods.*`); this module resolves the keys via the
 * global i18n instance — same outside-setup pattern as `utils/errors.ts`.
 */
import { i18n } from '@/i18n'

const t = (key: string): string => i18n.global.t(key)

/** Metrics with catalog-backed definitions (`evaluation.metric_defs.<key>`). */
const METRIC_KEYS = new Set(['accuracy', 'precision', 'recall', 'f1_score', 'confidence'])

/**
 * Get the tooltip text (long definition + guidance) for a metric key.
 * @param {string} key
 * @returns {string}
 */
export function getMetricTooltip(key: string | null | undefined): string {
  if (!key || !METRIC_KEYS.has(key)) return ''
  return `${t(`evaluation.metric_defs.${key}.long`)}\n${t(`evaluation.metric_defs.${key}.guidance`)}`
}

/**
 * `error_type` enums with catalog-backed texts
 * (`evaluation.error_types.<type>.{label,description,suggestion}`).
 * Unknown types fall back to `evaluation.error_types.unknown.*`.
 */
export const KNOWN_ERROR_TYPES = new Set([
  'missing',
  'mismatch',
  'fuzzy_mismatch',
  'numeric_mismatch',
  'boolean_mismatch',
  'category_mismatch',
  'date_mismatch',
  'type_error',
  'extra',
  'date_parse_error',
])

/**
 * Human-readable description for an error_type from EvaluationMetric.
 * @param {string|null} errorType
 * @returns {string}
 */
export function getErrorTypeDescription(errorType: string | null | undefined): string {
  const key = errorType && KNOWN_ERROR_TYPES.has(errorType) ? errorType : 'unknown'
  return t(`evaluation.error_types.${key}.description`)
}

/**
 * Actionable suggestion for an error_type.
 * @param {string|null} errorType
 * @returns {string}
 */
export function getErrorSuggestion(errorType: string | null | undefined): string {
  const key = errorType && KNOWN_ERROR_TYPES.has(errorType) ? errorType : 'unknown'
  return t(`evaluation.error_types.${key}.suggestion`)
}

/**
 * Comparison methods offered in the mapping configurator, in select order.
 * Labels/descriptions live under `groundtruth.comparison_methods.<method>`.
 */
export const COMPARISON_METHODS = [
  'exact',
  'fuzzy',
  'numeric',
  'category',
  'date',
  'boolean',
] as const

/**
 * Localized short label for a comparison method (e.g. the select options in
 * the mapping list). Unknown methods fall through as the raw value.
 * @param {string} method
 * @returns {string}
 */
export function getComparisonMethodLabel(method: string | null | undefined): string {
  if (!method || !(COMPARISON_METHODS as readonly string[]).includes(method)) return method || ''
  return t(`groundtruth.comparison_methods.${method}.label`)
}

/**
 * Plain-language description of a comparison method (used in the mapping
 * configurator so users understand what "fuzzy" vs "exact" actually does).
 * @param {string} method
 * @returns {string}
 */
export function getComparisonMethodDescription(method: string | null | undefined): string {
  if (!method || !(COMPARISON_METHODS as readonly string[]).includes(method)) return ''
  return t(`groundtruth.comparison_methods.${method}.description`)
}

/**
 * Format a metric value (0–1 float) as a percentage string, handling
 * null/undefined. Replaces the inlined `(x * 100).toFixed(1) + '%'` pattern.
 * @param {number|null|undefined} value
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatMetricPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}
