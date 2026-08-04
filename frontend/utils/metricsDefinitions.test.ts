import { describe, expect, it, vi } from 'vitest'
import {
  formatMetricPercent,
  getComparisonMethodDescription,
  getComparisonMethodLabel,
  getErrorSuggestion,
  getErrorTypeDescription,
  getMetricTooltip,
} from './metricsDefinitions'

// All prose is resolved through the global i18n instance; stub it so the
// assertions are locale-catalog-independent (t returns the key).
vi.mock('@/i18n', () => ({
  i18n: { global: { t: (key: string) => key } },
}))

describe('getMetricTooltip', () => {
  it('joins the long definition and guidance keys for known metrics', () => {
    expect(getMetricTooltip('accuracy')).toBe(
      'evaluation.metric_defs.accuracy.long\nevaluation.metric_defs.accuracy.guidance',
    )
  })

  it('returns empty for unknown or missing keys', () => {
    expect(getMetricTooltip('nope')).toBe('')
    expect(getMetricTooltip(null)).toBe('')
  })
})

describe('error type texts', () => {
  it('resolves known error types', () => {
    expect(getErrorTypeDescription('missing')).toBe('evaluation.error_types.missing.description')
    expect(getErrorSuggestion('fuzzy_mismatch')).toBe(
      'evaluation.error_types.fuzzy_mismatch.suggestion',
    )
  })

  it('falls back to the unknown entry', () => {
    expect(getErrorTypeDescription('nope')).toBe('evaluation.error_types.unknown.description')
    expect(getErrorTypeDescription(null)).toBe('evaluation.error_types.unknown.description')
    expect(getErrorSuggestion('nope')).toBe('evaluation.error_types.unknown.suggestion')
  })
})

describe('comparison method texts', () => {
  it('resolves known methods', () => {
    expect(getComparisonMethodLabel('fuzzy')).toBe('groundtruth.comparison_methods.fuzzy.label')
    expect(getComparisonMethodDescription('exact')).toBe(
      'groundtruth.comparison_methods.exact.description',
    )
  })

  it('passes through / blanks unknown methods', () => {
    expect(getComparisonMethodLabel('nope')).toBe('nope')
    expect(getComparisonMethodLabel(null)).toBe('')
    expect(getComparisonMethodDescription('nope')).toBe('')
    expect(getComparisonMethodDescription(null)).toBe('')
  })
})

describe('formatMetricPercent', () => {
  it('formats a 0–1 float as a percentage', () => {
    expect(formatMetricPercent(0.925)).toBe('92.5%')
    expect(formatMetricPercent(1, 0)).toBe('100%')
  })

  it('returns a dash for missing values', () => {
    expect(formatMetricPercent(null)).toBe('—')
    expect(formatMetricPercent(undefined)).toBe('—')
    expect(formatMetricPercent(NaN)).toBe('—')
  })
})
