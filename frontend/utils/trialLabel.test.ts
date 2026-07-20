import { describe, expect, it } from 'vitest'
import { trialLabel } from './trialLabel'

describe('trialLabel', () => {
  it('prefers a non-blank user-set name', () => {
    expect(trialLabel({ name: 'My Trial' })).toBe('My Trial')
  })

  it('ignores a blank name and uses the per-project number', () => {
    expect(trialLabel({ name: '   ', project_trial_number: 3 })).toBe('Trial #3')
    expect(trialLabel({ project_trial_number: 7 })).toBe('Trial #7')
  })

  it('falls back to the provided id only when nothing else is available', () => {
    expect(trialLabel({}, 42)).toBe('Trial #42')
    expect(trialLabel(null, 42)).toBe('Trial #42')
  })

  it('degrades to a bare label with no name, number, or id', () => {
    expect(trialLabel({})).toBe('Trial')
    expect(trialLabel(null)).toBe('Trial')
  })
})
