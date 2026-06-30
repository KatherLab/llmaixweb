/**
 * Plain-language definitions for evaluation metrics + error types.
 *
 * Single source of truth so the failure examiner, field tables, and any
 * summary view stay consistent. Used via the `Tooltip` component and as
 * inline helper text.
 */

/**
 * Metric definitions: { metric: { short, long, guidance } }
 *  - short: one-line label (tooltip headline)
 *  - long: plain-language definition
 *  - guidance: "what this means for you"
 */
export const METRIC_DEFINITIONS = {
  accuracy: {
    short: 'Accuracy',
    long: 'Share of all extracted fields that exactly match the ground truth.',
    guidance: 'High accuracy = most fields are correct overall.',
  },
  precision: {
    short: 'Precision',
    long: 'Of the values the model extracted, the fraction that were correct.',
    guidance: 'Low precision means the model often extracts wrong values (false positives).',
  },
  recall: {
    short: 'Recall',
    long: 'Of the values that should have been extracted, the fraction the model got right.',
    guidance:
      'Low recall means the model misses fields, or extracts the wrong value where a value was expected (false negatives).',
  },
  f1_score: {
    short: 'F1 Score',
    long: 'Harmonic mean of precision and recall — balances both into one number.',
    guidance: 'Use F1 to compare fields when you care about both missing and wrong values.',
  },
  confidence: {
    short: 'Confidence',
    long: 'The model’s self-reported certainty for the extracted value (0–1).',
    guidance: 'Low confidence on a correct value can hint at borderline cases worth reviewing.',
  },
}

/**
 * Get the tooltip text (long + guidance) for a metric key.
 * @param {string} key
 * @returns {string}
 */
export function getMetricTooltip(key) {
  const def = METRIC_DEFINITIONS[key]
  if (!def) return ''
  return `${def.long}\n${def.guidance}`
}

/**
 * Human-readable description for an error_type from EvaluationMetric.
 * Extracted from the former FieldErrorAnalysis.vue inline map.
 * @param {string|null} errorType
 * @returns {string}
 */
export function getErrorTypeDescription(errorType) {
  const descriptions = {
    missing: 'Field was not extracted from the document',
    mismatch: 'Extracted value does not match ground truth',
    fuzzy_mismatch: 'Extracted value is similar but not close enough to ground truth',
    numeric_mismatch: 'Numeric value is outside acceptable tolerance',
    boolean_mismatch: 'Boolean value is incorrect',
    category_mismatch: 'Category value does not match expected options',
    date_mismatch: 'Date value is incorrect or in wrong format',
    type_error: 'Value type is incorrect (e.g., text instead of number)',
    extra: 'Field was extracted but not expected in ground truth',
    date_parse_error: 'Date could not be parsed for comparison',
  }
  return descriptions[errorType] || 'Unknown error type'
}

/**
 * Actionable suggestion for an error_type.
 * Extracted from the former FieldErrorAnalysis.vue inline map.
 * @param {string|null} errorType
 * @returns {string}
 */
export function getErrorSuggestion(errorType) {
  const suggestions = {
    missing: 'Check if the field exists in the document or improve extraction prompts',
    mismatch: 'Review extraction accuracy or ground truth data',
    fuzzy_mismatch: 'Consider adjusting fuzzy matching threshold or improving extraction',
    numeric_mismatch: 'Check numeric parsing or adjust tolerance settings',
    boolean_mismatch: 'Review boolean value mapping or extraction logic',
    category_mismatch: 'Verify category mappings or improve classification',
    date_mismatch: 'Check date format parsing or improve date extraction',
    type_error: 'Review data type conversion or schema definition',
    extra: 'Check if this field should be included in ground truth',
    date_parse_error: 'Check date format parsing or improve date extraction',
  }
  return suggestions[errorType] || 'Review extraction logic and ground truth data'
}

/**
 * Plain-language description of a comparison method (used in the mapping
 * configurator so users understand what "fuzzy" vs "exact" actually does).
 * @param {string} method
 * @returns {string}
 */
export function getComparisonMethodDescription(method) {
  const descriptions = {
    exact: 'Exact text match (case-insensitive by default). Use for IDs, codes, enums.',
    fuzzy:
      'Approximate string match. Correct if similarity ≥ threshold (default 85). Use for free text with minor variations.',
    numeric:
      'Numeric comparison within a tolerance (default 0.001, absolute). Use for measurements, counts, lab values.',
    boolean: 'True/false comparison (true/yes/1 vs false/no/0).',
    category: 'Categorical match with optional synonym mappings. Builds a confusion matrix.',
    date: 'Date equality across common formats (e.g. 2024-01-02 vs 02/01/2024).',
  }
  return descriptions[method] || ''
}

/**
 * Format a metric value (0–1 float) as a percentage string, handling
 * null/undefined. Replaces the inlined `(x * 100).toFixed(1) + '%'` pattern.
 * @param {number|null|undefined} value
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatMetricPercent(value, digits = 1) {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}
