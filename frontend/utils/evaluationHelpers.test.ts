import { describe, expect, it, vi } from 'vitest'
import {
  accuracyBarColor,
  accuracyColor,
  documentStatusColor,
  documentStatusLabel,
  documentStatusTier,
  getEvaluationAccuracy,
  getEvaluationAccuracyPct,
  getEvaluationDocumentCount,
  prettifyErrorType,
  prettifyField,
} from './evaluationHelpers'

// The helpers resolve localized labels through the global i18n instance;
// stub it so assertions are locale-catalog-independent (t returns the key).
vi.mock('@/i18n', () => ({
  i18n: { global: { t: (key: string) => key } },
}))

// These helpers deliberately accept loosely-shaped payloads at runtime; the
// exported signatures require the full Evaluation types, so route the partial
// fixtures through these casts rather than constructing complete objects.
const ev = (o: unknown) => o as Parameters<typeof getEvaluationAccuracy>[0]
const doc = (o: unknown) => o as Parameters<typeof documentStatusLabel>[0]

describe('getEvaluationAccuracy', () => {
  it('reads either payload shape and guards against NaN', () => {
    expect(getEvaluationAccuracy(ev({ overall_metrics: { accuracy: 0.5 } }))).toBe(0.5)
    expect(getEvaluationAccuracy(ev({ metrics: { accuracy: 0.8 } }))).toBe(0.8)
    expect(getEvaluationAccuracy(ev({ overall_metrics: { accuracy: NaN } }))).toBe(0)
    expect(getEvaluationAccuracy(null)).toBe(0)
  })

  it('formats as a percentage string', () => {
    expect(getEvaluationAccuracyPct(ev({ overall_metrics: { accuracy: 0.925 } }))).toBe('92.5%')
    expect(getEvaluationAccuracyPct(null)).toBe('0.0%')
  })
})

describe('getEvaluationDocumentCount', () => {
  it('prefers explicit document_count, then total_documents, then array lengths', () => {
    expect(getEvaluationDocumentCount(ev({ document_count: 5 }))).toBe(5)
    expect(getEvaluationDocumentCount(ev({ metrics: { total_documents: 3 } }))).toBe(3)
    expect(getEvaluationDocumentCount(ev({ document_summaries: [{}, {}] }))).toBe(2)
    expect(getEvaluationDocumentCount(ev({ document_metrics: [{}] }))).toBe(1)
    expect(getEvaluationDocumentCount(null)).toBe(0)
  })
})

describe('prettifyField', () => {
  it('takes the last path segment and title-cases it', () => {
    expect(prettifyField('patient.age_years')).toBe('Age Years')
    expect(prettifyField('lab_results[0].name')).toBe('Name')
    expect(prettifyField('camelCase')).toBe('Camel Case')
    expect(prettifyField('')).toBe('')
    expect(prettifyField(null)).toBe('')
  })
})

describe('prettifyErrorType', () => {
  it('resolves known error types through the i18n catalog', () => {
    expect(prettifyErrorType('fuzzy_mismatch')).toBe('evaluation.error_types.fuzzy_mismatch.label')
    expect(prettifyErrorType(null)).toBe('')
  })

  it('title-cases unknown error types as a fallback', () => {
    expect(prettifyErrorType('weird_new_type')).toBe('Weird New Type')
  })
})

describe('accuracy tiers', () => {
  it('colours by the shared 0.5 / 0.9 thresholds', () => {
    expect(accuracyColor(0.95)).toContain('green')
    expect(accuracyColor(0.7)).toContain('yellow')
    expect(accuracyColor(0.3)).toContain('red')
    expect(accuracyColor(null)).toContain('slate')
    expect(accuracyColor(NaN)).toContain('slate')
  })

  it('uses matching background tiers for bars', () => {
    expect(accuracyBarColor(0.95)).toContain('green')
    expect(accuracyBarColor(0.7)).toContain('yellow')
    expect(accuracyBarColor(0.3)).toContain('red')
    expect(accuracyBarColor(undefined)).toContain('slate')
  })
})

describe('document status', () => {
  it('assigns a tier by the shared thresholds', () => {
    expect(documentStatusTier(doc({ accuracy: 0.95 }))).toBe('ok')
    expect(documentStatusTier(doc({ accuracy: 0.7 }))).toBe('partial')
    expect(documentStatusTier(doc({ accuracy: 0.3 }))).toBe('low')
    expect(documentStatusTier(doc({ has_error: true }))).toBe('error')
    expect(documentStatusTier(doc({ accuracy: null }))).toBe('')
    expect(documentStatusTier(null)).toBe('')
  })

  it('labels a document via the status_labels catalog keys', () => {
    expect(documentStatusLabel(doc({ accuracy: 0.95 }))).toBe('evaluation.status_labels.ok')
    expect(documentStatusLabel(doc({ accuracy: 0.7 }))).toBe('evaluation.status_labels.partial')
    expect(documentStatusLabel(doc({ accuracy: 0.3 }))).toBe('evaluation.status_labels.low')
    expect(documentStatusLabel(doc({ has_error: true }))).toBe('evaluation.status_labels.error')
    expect(documentStatusLabel(doc({ accuracy: null }))).toBe('')
    expect(documentStatusLabel(null)).toBe('')
  })

  it('maps labels to badge colours', () => {
    expect(documentStatusColor(doc({ accuracy: 0.95 }))).toBe('green')
    expect(documentStatusColor(doc({ accuracy: 0.7 }))).toBe('yellow')
    expect(documentStatusColor(doc({ accuracy: 0.3 }))).toBe('red')
    expect(documentStatusColor(doc({ has_error: true }))).toBe('red')
  })
})
