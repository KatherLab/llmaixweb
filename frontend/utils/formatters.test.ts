import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  formatDate,
  formatDateTime,
  formatDuration,
  formatFileSize,
  formatRelativeTime,
  truncateText,
} from './formatters'

describe('formatFileSize', () => {
  it('returns the fallback for missing/invalid input', () => {
    expect(formatFileSize(0)).toBe('0 B')
    expect(formatFileSize(null)).toBe('0 B')
    expect(formatFileSize(undefined)).toBe('0 B')
    expect(formatFileSize(NaN)).toBe('0 B')
    expect(formatFileSize(0, '—')).toBe('—')
  })

  it('scales through units with one decimal', () => {
    expect(formatFileSize(500)).toBe('500.0 B')
    expect(formatFileSize(1024)).toBe('1.0 KB')
    expect(formatFileSize(1536)).toBe('1.5 KB')
    expect(formatFileSize(1024 * 1024)).toBe('1.0 MB')
    expect(formatFileSize(1024 * 1024 * 1024)).toBe('1.0 GB')
  })
})

describe('truncateText', () => {
  it('returns empty string for nullish input', () => {
    expect(truncateText(null)).toBe('')
    expect(truncateText(undefined)).toBe('')
  })

  it('leaves short text untouched', () => {
    expect(truncateText('hello', 10)).toBe('hello')
  })

  it('truncates and appends an ellipsis past the limit', () => {
    expect(truncateText('hello world', 5)).toBe('hello...')
  })
})

describe('formatDuration', () => {
  it('returns zero clock for missing/invalid input', () => {
    expect(formatDuration(0)).toBe('00:00:00')
    expect(formatDuration(null)).toBe('00:00:00')
    expect(formatDuration(NaN)).toBe('00:00:00')
  })

  it('formats seconds as HH:MM:SS', () => {
    expect(formatDuration(332)).toBe('00:05:32')
    expect(formatDuration(3661)).toBe('01:01:01')
  })
})

describe('formatDate / formatDateTime', () => {
  it('returns empty string for missing input', () => {
    expect(formatDate('')).toBe('')
    expect(formatDate(null)).toBe('')
  })

  it('flags unparseable input', () => {
    expect(formatDate('not-a-date')).toBe('Invalid date')
  })

  it('formats a valid ISO date in en-US', () => {
    // Midday UTC so the local date does not shift across CI/dev timezones.
    expect(formatDate('2025-01-15T12:00:00Z')).toBe('Jan 15, 2025')
  })

  it('includes time when requested', () => {
    const out = formatDateTime('2025-01-15T12:00:00Z')
    expect(out).toContain('Jan 15, 2025')
    expect(out).toMatch(/\d{2}:\d{2}/)
  })
})

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-06-15T12:00:00Z'))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns empty string for missing/invalid input', () => {
    expect(formatRelativeTime(null)).toBe('')
    expect(formatRelativeTime('not-a-date')).toBe('')
  })

  it('bucketizes recent timestamps', () => {
    expect(formatRelativeTime('2025-06-15T11:59:30Z')).toBe('just now')
    expect(formatRelativeTime('2025-06-15T11:58:00Z')).toBe('2m ago')
    expect(formatRelativeTime('2025-06-15T10:00:00Z')).toBe('2h ago')
    expect(formatRelativeTime('2025-06-13T12:00:00Z')).toBe('2d ago')
  })

  it('falls back to an absolute date beyond 30 days', () => {
    expect(formatRelativeTime('2025-01-15T12:00:00Z')).toBe('Jan 15, 2025')
  })
})
