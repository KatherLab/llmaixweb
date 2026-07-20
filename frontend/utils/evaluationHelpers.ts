/**
 * Shared helpers for the Evaluation UI.
 *
 * The backend returns evaluation payloads in slightly different shapes
 * depending on the endpoint:
 *   - `EvaluationSummary` (evaluate / list) → `overall_metrics` + `document_summaries`
 *   - `Evaluation` (legacy / detail)       → `metrics` + `document_metrics`
 *   - the optimistic row pushed after evaluate sets BOTH for safety.
 *
 * These helpers paper over that difference so every component reads accuracy
 * and document counts the same way (previously three call sites had three
 * different assumptions, one of which produced "NaN% accuracy" in the export
 * modal).
 */
import type { Evaluation, EvaluationSummary, DocumentEvaluationDetail } from '@/types'

/**
 * Structural supertype covering both `Evaluation` and `EvaluationSummary`
 * payloads (and the optimistic row that sets BOTH metric maps for safety).
 * Each field is optional so helpers can read either shape uniformly.
 */
type EvaluationLike = (Evaluation | EvaluationSummary) & {
  overall_metrics?: Record<string, unknown>
  metrics?: Record<string, unknown>
  document_summaries?: DocumentEvaluationDetail[]
  document_metrics?: Record<string, unknown>[]
  document_count?: number
}

/** Evaluation payload (or null/undefined) as accepted by these helpers. */
type EvaluationArg = EvaluationLike | null | undefined

/**
 * Read the overall accuracy (0–1 float) from any evaluation-shaped object.
 * @param {object} evaluation
 * @returns {number}
 */
export function getEvaluationAccuracy(evaluation: EvaluationArg): number {
  if (!evaluation) return 0
  const accuracy = evaluation.overall_metrics?.accuracy ?? evaluation.metrics?.accuracy ?? 0
  return typeof accuracy === 'number' && !isNaN(accuracy) ? accuracy : 0
}

/**
 * Accuracy as a percentage string with one decimal (e.g. "92.5%").
 * @param {object} evaluation
 * @param {number} [digits=1]
 * @returns {string}
 */
export function getEvaluationAccuracyPct(evaluation: EvaluationArg, digits = 1): string {
  return `${(getEvaluationAccuracy(evaluation) * 100).toFixed(digits)}%`
}

/**
 * Number of scored documents in an evaluation payload, regardless of shape.
 * @param {object} evaluation
 * @returns {number}
 */
export function getEvaluationDocumentCount(evaluation: EvaluationArg): number {
  if (!evaluation) return 0
  // Prefer the explicit `document_count` (present on the list payload, which
  // omits the heavy per-document arrays) so the count survives a page reload;
  // fall back to `metrics.total_documents`, then to the array lengths that the
  // freshly-evaluated / detail payloads carry.
  if (typeof evaluation.document_count === 'number') return evaluation.document_count
  const totalDocs = evaluation.metrics?.total_documents
  if (typeof totalDocs === 'number') return totalDocs
  return evaluation.document_summaries?.length || evaluation.document_metrics?.length || 0
}

/**
 * The document-level entries list, regardless of payload shape.
 * @param {object} evaluation
 * @returns {object[]}
 */
export function getEvaluationDocuments(evaluation: EvaluationArg): DocumentEvaluationDetail[] {
  if (!evaluation) return []
  return (
    evaluation.document_summaries ||
    (evaluation.document_metrics as unknown as DocumentEvaluationDetail[]) ||
    []
  )
}

/**
 * Prettify a dot/bracket field path for display — takes the last segment
 * and Title-Cases it, splitting on _ - and camelCase boundaries.
 *   "patient.age_years" → "Age Years"
 *   "lab_results[0].name" → "Name"
 * @param {string} key
 * @returns {string}
 */
export function prettifyField(key: string | null | undefined): string {
  if (!key) return ''
  const last =
    String(key)
      .split(/[.[\]]/)
      .filter(Boolean)
      .pop() || key
  return last
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// ─── Accuracy / status tiers ────────────────────────────────────────────────
// The 0.5 / 0.9 thresholds were previously duplicated across
// EvaluationAnalysisPage, FailureDetailDrawer, and the status-filter options,
// so the "OK / Low / Partial" wording and colours could drift apart. These
// keep the three views in lockstep.

/** Accuracy thresholds shared across the evaluation UI. */
export const ACCURACY_THRESHOLDS = {
  HIGH: 0.9,
  LOW: 0.5,
}

/**
 * Tailwind text-colour class for an accuracy value (0–1).
 * @param {number|null|undefined} acc
 * @returns {string}
 */
export function accuracyColor(acc: number | null | undefined): string {
  if (acc === null || acc === undefined || isNaN(acc)) return 'text-slate-400'
  if (acc >= ACCURACY_THRESHOLDS.HIGH) return 'text-green-600 dark:text-green-400'
  if (acc < ACCURACY_THRESHOLDS.LOW) return 'text-red-600 dark:text-red-400'
  return 'text-yellow-600 dark:text-yellow-400'
}

/**
 * Short human label for a document's accuracy tier.
 *   ≥0.9 → 'OK', <0.5 → 'Low', else → 'Partial'.
 * Documents that failed to score (`has_error`/`error`) → 'Error'.
 * @param {object} doc  a document-eval row ({ accuracy, has_error, error })
 * @returns {string}
 */
export function documentStatusLabel(doc: DocumentEvaluationDetail | null | undefined): string {
  if (!doc) return ''
  if (doc.has_error || doc.error) return 'Error'
  if (doc.accuracy == null) return ''
  if (doc.accuracy >= ACCURACY_THRESHOLDS.HIGH) return 'OK'
  if (doc.accuracy < ACCURACY_THRESHOLDS.LOW) return 'Low'
  return 'Partial'
}

/**
 * StatusBadge `color` for a document-eval row.
 * @param {object} doc
 * @returns {'red'|'green'|'yellow'}
 */
export function documentStatusColor(
  doc: DocumentEvaluationDetail | null | undefined,
): 'red' | 'green' | 'yellow' {
  const label = documentStatusLabel(doc)
  if (label === 'Error' || label === 'Low') return 'red'
  if (label === 'OK') return 'green'
  return 'yellow'
}

/**
 * Prettify a raw error_type enum (e.g. `fuzzy_mismatch`) for inline display.
 * Kept here so chips/labels across the UI show the same wording as the
 * tooltips in metricsDefinitions.js.
 * @param {string|null|undefined} errorType
 * @returns {string}
 */
export function prettifyErrorType(errorType: string | null | undefined): string {
  if (!errorType) return ''
  return String(errorType)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}
