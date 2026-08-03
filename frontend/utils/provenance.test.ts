import { describe, it, expect } from 'vitest'
import {
  bestMatch,
  boundedLevenshtein,
  dateCandidates,
  flattenResultLeaves,
  foldText,
  locateValue,
  numericCandidates,
  type ProvenanceKind,
} from './provenance'

/** The span a match points at, so assertions read as "it found this text". */
function span(text: string, value: unknown, options = {}): string | null {
  const m = bestMatch(locateValue(text, value, options))
  return m ? text.slice(m.start, m.end) : null
}

function kind(text: string, value: unknown, options = {}): ProvenanceKind | null {
  return bestMatch(locateValue(text, value, options))?.kind ?? null
}

describe('flattenResultLeaves', () => {
  it('produces backend-compatible paths for nested objects and arrays', () => {
    const leaves = flattenResultLeaves({
      patient: { name: 'Sarah Lee' },
      medications: [{ dose: '5 mg' }, { dose: '10 mg' }],
      tags: ['a', 'b'],
    })
    expect(leaves.map((l) => l.path)).toEqual([
      'patient.name',
      'medications[0].dose',
      'medications[1].dose',
      'tags[0]',
      'tags[1]',
    ])
  })

  it('labels leaves from their key', () => {
    const [leaf] = flattenResultLeaves({ date_of_birth: '1961-04-03' })
    expect(leaf.label).toBe('Date Of Birth')
  })

  it('marks null and blank values empty so they stay out of coverage counts', () => {
    const leaves = flattenResultLeaves({ a: null, b: '   ', c: 'x', d: false })
    expect(leaves.filter((l) => l.isEmpty).map((l) => l.path)).toEqual(['a', 'b'])
  })
})

describe('foldText', () => {
  it('maps folded offsets back onto the original text', () => {
    const text = 'Patient:   Sarah  LEE'
    const folded = foldText(text)
    expect(folded.text).toBe('patient: sarah lee')
    const i = folded.text.indexOf('sarah')
    expect(text.slice(folded.starts[i], folded.ends[i + 4])).toBe('Sarah')
  })

  it('rejoins words broken by a line-wrap hyphen', () => {
    expect(foldText('pulmo-\nnary embolism').text).toBe('pulmonary embolism')
  })

  it('strips accents so OCR that lost an umlaut still matches', () => {
    expect(foldText('Müller').text).toBe('muller')
  })
})

describe('locateValue — literal tiers', () => {
  const text = 'Diagnosis: Pulmonary embolism - bilateral. Patient: Sarah Lee.'

  it('finds a verbatim value', () => {
    expect(span(text, 'Sarah Lee')).toBe('Sarah Lee')
    expect(kind(text, 'Sarah Lee')).toBe('exact')
  })

  it('finds a value that differs only in case', () => {
    expect(span(text, 'pulmonary embolism')).toBe('Pulmonary embolism')
    expect(kind(text, 'pulmonary embolism')).toBe('normalized')
  })

  it('finds a value across a collapsed line break', () => {
    const wrapped = 'the patient has pulmonary\n   embolism today'
    expect(kind(wrapped, 'pulmonary embolism')).toBe('normalized')
    expect(span(wrapped, 'pulmonary embolism')).toBe('pulmonary\n   embolism')
  })

  it('returns nothing for a value with no grounding in the text', () => {
    expect(locateValue(text, 'myocardial infarction')).toEqual([])
  })

  it('reports every occurrence of a repeated value', () => {
    const repeated = 'aspirin in the morning, then aspirin at night'
    expect(locateValue(repeated, 'aspirin')).toHaveLength(2)
  })

  it('requires a word boundary for very short values', () => {
    // "II" must not match inside "IIIrd" or "skIIng".
    expect(locateValue('stage IIIrd disease', 'II')).toEqual([])
    expect(span('tumour stage II confirmed', 'II')).toBe('II')
  })

  it('ignores null, undefined and blank values', () => {
    expect(locateValue(text, null)).toEqual([])
    expect(locateValue(text, '   ')).toEqual([])
  })
})

describe('locateValue — numeric tier', () => {
  it('matches a number written with thousands separators', () => {
    expect(span('Total volume was 1,234.50 mL', 1234.5)).toBe('1,234.50')
    expect(kind('Total volume was 1,234.50 mL', 1234.5)).toBe('numeric')
  })

  it('matches German decimal notation', () => {
    expect(span('Gewicht: 72,5 kg', 72.5)).toBe('72,5')
  })

  it('matches an integer stored with a trailing decimal', () => {
    expect(span('Count: 12', 12.0)).toBe('12')
  })

  it('prefers a verbatim hit over a numeric reinterpretation', () => {
    expect(kind('Value 5 and 5.0 both appear', 5)).toBe('exact')
  })

  it('does not match a different number', () => {
    expect(locateValue('Total 1,234.50 mL', 1234.6)).toEqual([])
  })
})

describe('locateValue — date tier', () => {
  it('links an ISO date back to the slash-formatted original', () => {
    const text = 'Patient: Sarah Lee, DOB: 03/04/1961'
    expect(span(text, '1961-04-03')).toBe('03/04/1961')
    expect(kind(text, '1961-04-03')).toBe('date')
  })

  it('links an ISO date back to a German written date', () => {
    expect(span('Aufnahme am 3. April 1961 erfolgt', '1961-04-03')).toBe('3. April 1961')
  })

  it('links an ISO date back to an English written date', () => {
    expect(span('Admitted January 5, 2024 for review', '2024-01-05')).toBe('January 5, 2024')
  })

  it('matches a dotted German date', () => {
    expect(span('Geburtsdatum 03.04.1961', '1961-04-03')).toBe('03.04.1961')
  })

  it('does not match a different day', () => {
    expect(locateValue('DOB: 03/04/1961', '1962-04-03')).toEqual([])
  })

  it('accepts either reading of an ambiguous numeric date', () => {
    // 03/04/1961 is 3 April (D/M) or 4 March (M/D) — both are legitimate.
    expect(kind('DOB: 03/04/1961', '1961-03-04')).toBe('date')
  })
})

describe('dateCandidates / numericCandidates', () => {
  it('offers both readings of an ambiguous numeric date', () => {
    expect(dateCandidates('03/04/1961').sort()).toEqual(['1961-03-04', '1961-04-03'])
  })

  it('offers both locale readings of an ambiguous separator', () => {
    expect(numericCandidates('1.234').sort()).toEqual([1.234, 1234])
  })

  it('reads a comma decimal', () => {
    expect(numericCandidates('72,5')).toContain(72.5)
  })
})

describe('locateValue — label tier', () => {
  it('points at the field wording when a boolean was inferred', () => {
    const text = 'Presenting symptoms: Chest pain and shortness of breath.'
    expect(span(text, true, { label: 'Chest Pain' })).toBe('Chest pain')
    expect(kind(text, true, { label: 'Chest Pain' })).toBe('label')
  })

  it('finds nothing for a boolean whose field is never mentioned', () => {
    expect(locateValue('Nothing relevant here.', false, { label: 'Leg Swelling' })).toEqual([])
  })

  it('never claims a boolean is a verbatim hit', () => {
    // The word "true" appearing in prose is not evidence for a true value.
    expect(locateValue('It is true that the sky is blue.', true)).toEqual([])
  })
})

describe('locateValue — evidence quotes', () => {
  const text = 'Impression: the patient has a bilateral pulmonary embolism.'

  it('anchors on the model-cited quote and reports it as such', () => {
    const m = bestMatch(locateValue(text, 'PE', { quote: 'bilateral pulmonary embolism' }))
    expect(m?.kind).toBe('quote')
    expect(text.slice(m!.start, m!.end)).toBe('bilateral pulmonary embolism')
  })

  it('falls back to value matching when the quote was paraphrased', () => {
    expect(kind(text, 'pulmonary embolism', { quote: 'the patient suffers from a clot' })).toBe(
      'exact',
    )
  })

  it('outranks a verbatim value hit, because the model named the source', () => {
    const t = 'History: embolism in 2019. Impression: embolism, bilateral, acute.'
    const m = bestMatch(locateValue(t, 'embolism', { quote: 'embolism, bilateral, acute' }))
    expect(m?.kind).toBe('quote')
    expect(t.slice(m!.start, m!.end)).toBe('embolism, bilateral, acute')
  })
})

describe('locateValue — fuzzy tier', () => {
  it('finds a span with a typo or OCR damage', () => {
    const text = 'Impression: bilateral pulmonaru embolisrn of the lower lobe.'
    const m = bestMatch(locateValue(text, 'bilateral pulmonary embolism'))
    expect(m?.kind).toBe('fuzzy')
    expect(m!.score).toBeGreaterThan(0.75)
    expect(text.slice(m!.start, m!.end)).toContain('pulmonaru')
  })

  it('does not invent a match for unrelated text', () => {
    expect(
      locateValue('The weather today is quite pleasant.', 'bilateral pulmonary embolism'),
    ).toEqual([])
  })

  it('skips fuzzy matching for short values, where it would be noise', () => {
    expect(locateValue('the cat sat on the mat', 'bat')).toEqual([])
  })
})

describe('boundedLevenshtein', () => {
  it('measures small edits', () => {
    expect(boundedLevenshtein('kitten', 'sitting', 5)).toBe(3)
    expect(boundedLevenshtein('same', 'same', 2)).toBe(0)
  })

  it('abandons once the budget is exceeded', () => {
    expect(boundedLevenshtein('abcdefgh', 'zzzzzzzz', 2)).toBeGreaterThan(2)
  })

  it('handles empty inputs', () => {
    expect(boundedLevenshtein('', 'abc', 5)).toBe(3)
  })
})

describe('bestMatch', () => {
  it('prefers the stronger tier over the higher score', () => {
    const best = bestMatch([
      { start: 0, end: 5, kind: 'fuzzy', score: 1 },
      { start: 9, end: 14, kind: 'exact', score: 0.9 },
    ])
    expect(best?.kind).toBe('exact')
  })

  it('returns null for no matches', () => {
    expect(bestMatch([])).toBeNull()
  })
})

describe('performance guard', () => {
  it('stays fast on a large document', () => {
    const text = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(3000)
    const started = performance.now()
    locateValue(text, 'a value that is definitely not present anywhere here')
    expect(performance.now() - started).toBeLessThan(1500)
  })
})
