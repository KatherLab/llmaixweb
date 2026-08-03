/**
 * Provenance matching — locate an extracted value inside the source text.
 *
 * The results viewer answers "where did this come from?" by searching the
 * document text the LLM actually saw. That is best-effort by nature: a model
 * normalizes dates, rounds numbers, translates, and infers booleans that are
 * never written down. So instead of a yes/no, every hit carries a *kind* that
 * says how it was found, and the UI shows it — an approximate match must not
 * look like a verbatim one.
 *
 * Tiers, strongest first:
 *   quote      the model itself cited this span (evidence mode)
 *   exact      the value appears verbatim
 *   normalized appears modulo case, whitespace, line-wrap hyphens, accents
 *   numeric    a number token in the text has the same value ("1,234.50" ≡ 1234.5)
 *   date       a date token denotes the same day ("03/04/1961" ≡ "1961-04-03")
 *   label      only the field's own label is present — the value was inferred
 *   fuzzy      an approximate span (token-anchored, similarity scored)
 *
 * No match at all is a first-class outcome, and a useful one: a value with no
 * grounding anywhere in the document is exactly what a reviewer wants to see.
 */

export type ProvenanceKind =
  'quote' | 'exact' | 'normalized' | 'numeric' | 'date' | 'label' | 'fuzzy'

/** Strongest-first ordering, used to rank competing matches and overlaps. */
export const PROVENANCE_RANK: Record<ProvenanceKind, number> = {
  quote: 7,
  exact: 6,
  normalized: 5,
  numeric: 4,
  date: 3,
  label: 2,
  fuzzy: 1,
}

export interface ProvenanceMatch {
  /** Offsets into the ORIGINAL text (not the normalized copy). */
  start: number
  end: number
  kind: ProvenanceKind
  /** 0–1; 1 for the deterministic tiers, similarity ratio for fuzzy. */
  score: number
}

export interface ResultLeaf {
  /** JSON path, e.g. `patient.name` or `medications[0].dose`. */
  path: string
  /** Human label for the final path segment ("Date Of Birth"). */
  label: string
  value: unknown
  /** null / '' / [] — nothing to locate, and excluded from coverage counts. */
  isEmpty: boolean
}

export interface LocateOptions {
  /** Verbatim span the model cited for this value (evidence mode). */
  quote?: string
  /** Field label, used for the `label` tier on booleans and enums. */
  label?: string
  /** Cap on returned matches (default 20). */
  maxMatches?: number
}

// Values this short produce noise rather than provenance ("A", "II", 0) unless
// they land on a word boundary, so the cheap tiers below apply that guard.
const SHORT_VALUE_LEN = 3
const FUZZY_MIN_LEN = 8
const FUZZY_MIN_SCORE = 0.75
/** Fuzzy search is quadratic per candidate; these keep a click under ~50ms. */
const FUZZY_MAX_CANDIDATES = 40
const FUZZY_MAX_NEEDLE = 200
const FUZZY_MAX_TEXT = 400_000

// ---------------------------------------------------------------------------
// Result flattening
// ---------------------------------------------------------------------------

/** snake_case / camelCase → "Snake Case". Mirrors utils/schemaFieldList.ts. */
function prettify(key: string): string {
  return String(key)
    .replace(/[_-]+/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || (typeof value === 'string' && !value.trim())
}

/**
 * Flatten an extraction result into the scalar leaves a user can point at.
 *
 * Paths use the same syntax as the backend's evidence map (`a.b[0].c`), so a
 * leaf can look up its model-cited quote by path with no translation.
 */
export function flattenResultLeaves(data: unknown, prefix = '', label = ''): ResultLeaf[] {
  if (Array.isArray(data)) {
    return data.flatMap((item, i) => flattenResultLeaves(item, `${prefix}[${i}]`, label))
  }
  if (data && typeof data === 'object') {
    return Object.entries(data as Record<string, unknown>).flatMap(([key, value]) =>
      flattenResultLeaves(value, prefix ? `${prefix}.${key}` : key, prettify(key)),
    )
  }
  // Scalar (or null) — a leaf. An unnamed root value has no path to key on.
  if (!prefix) return []
  return [
    { path: prefix, label: label || prettify(prefix), value: data, isEmpty: isEmptyValue(data) },
  ]
}

// ---------------------------------------------------------------------------
// Text normalization (with an index map back to the original)
// ---------------------------------------------------------------------------

export interface FoldedText {
  text: string
  /** Original start/end offset of each folded character. */
  starts: number[]
  ends: number[]
}

const DASHES = /[\u2010-\u2015\u2212]/
const QUOTES = /[\u2018\u2019\u201B\u2032]/
const DQUOTES = /[\u201C\u201D\u201F\u2033]/

function foldChar(ch: string): string {
  if (DASHES.test(ch)) return '-'
  if (QUOTES.test(ch)) return "'"
  if (DQUOTES.test(ch)) return '"'
  // Strip combining marks so "Müller" folds to "muller" and matches an OCR
  // rendering that lost the umlaut.
  return ch
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

/**
 * Case/whitespace/accent-folded copy of `text`, plus per-character offsets back
 * into the original so a hit can be highlighted where the user can see it.
 *
 * Whitespace runs collapse to a single space and a hyphen before a line break
 * is dropped entirely, which is what makes OCR line-wrapped words findable.
 */
export function foldText(text: string): FoldedText {
  const out: string[] = []
  const starts: number[] = []
  const ends: number[] = []
  let i = 0
  let lastWasSpace = false

  while (i < text.length) {
    const ch = text[i]

    // Soft hyphen, or a hyphen that only exists because the line wrapped.
    if (ch === '\u00ad') {
      i += 1
      continue
    }
    if (ch === '-' || DASHES.test(ch)) {
      const rest = /^[ \t]*\r?\n[ \t]*/.exec(text.slice(i + 1))
      if (rest) {
        i += 1 + rest[0].length
        continue
      }
    }

    if (/\s/.test(ch)) {
      if (!lastWasSpace && out.length > 0) {
        out.push(' ')
        starts.push(i)
        ends.push(i + 1)
        lastWasSpace = true
      }
      i += 1
      continue
    }

    lastWasSpace = false
    const folded = foldChar(ch)
    for (const f of folded) {
      out.push(f)
      starts.push(i)
      ends.push(i + 1)
    }
    i += 1
  }

  // A trailing collapsed space would let a needle match past the real end.
  while (out.length && out[out.length - 1] === ' ') {
    out.pop()
    starts.pop()
    ends.pop()
  }

  return { text: out.join(''), starts, ends }
}

/** Fold a search needle with the same rules (no offset map needed). */
export function foldNeedle(value: string): string {
  return foldText(value).text
}

function toOriginalRange(folded: FoldedText, start: number, end: number): [number, number] {
  if (end <= start) return [folded.starts[start] ?? 0, folded.starts[start] ?? 0]
  return [folded.starts[start], folded.ends[end - 1]]
}

// ---------------------------------------------------------------------------
// Literal passes
// ---------------------------------------------------------------------------

const WORDISH = /[\p{L}\p{N}]/u

function isWordBounded(text: string, start: number, end: number): boolean {
  const before = start > 0 ? text[start - 1] : ''
  const after = end < text.length ? text[end] : ''
  return !(before && WORDISH.test(before)) && !(after && WORDISH.test(after))
}

function findAll(
  haystack: string,
  needle: string,
  { wordBounded = false, limit = 50 } = {},
): Array<[number, number]> {
  const hits: Array<[number, number]> = []
  if (!needle) return hits
  let from = 0
  while (hits.length < limit) {
    const idx = haystack.indexOf(needle, from)
    if (idx === -1) break
    const end = idx + needle.length
    if (!wordBounded || isWordBounded(haystack, idx, end)) hits.push([idx, end])
    from = idx + Math.max(1, needle.length)
  }
  return hits
}

// ---------------------------------------------------------------------------
// Numeric pass
// ---------------------------------------------------------------------------

const NUMBER_TOKEN = /[+-]?\d[\d.,\u00a0 ]*\d|[+-]?\d/g

/**
 * Numeric values a token could denote. Thousands separators differ by locale
 * and the same string is ambiguous ("1.234" is 1234 in German, 1.234 in
 * English), so both readings are kept and either may match.
 */
export function numericCandidates(token: string): number[] {
  const cleaned = token.replace(/[\u00a0 ]/g, '')
  if (!/\d/.test(cleaned)) return []
  const out = new Set<number>()

  const push = (s: string) => {
    const n = Number(s)
    if (Number.isFinite(n)) out.add(n)
  }

  const hasDot = cleaned.includes('.')
  const hasComma = cleaned.includes(',')

  if (hasDot && hasComma) {
    // The rightmost separator is the decimal point; the other groups thousands.
    const decimal = cleaned.lastIndexOf('.') > cleaned.lastIndexOf(',') ? '.' : ','
    const group = decimal === '.' ? ',' : '.'
    push(cleaned.split(group).join('').replace(decimal, '.'))
  } else if (hasDot || hasComma) {
    const sep = hasDot ? '.' : ','
    const parts = cleaned.split(sep)
    // Decimal reading — only meaningful with a single separator.
    if (parts.length === 2) push(cleaned.replace(sep, '.'))
    // Thousands reading, only when every group after the first has 3 digits.
    if (parts.length > 1 && parts.slice(1).every((p) => /^\d{3}$/.test(p))) {
      push(parts.join(''))
    }
  } else {
    push(cleaned)
  }

  return [...out]
}

function numbersEqual(a: number, b: number): boolean {
  if (a === b) return true
  const scale = Math.max(Math.abs(a), Math.abs(b), 1)
  return Math.abs(a - b) <= scale * 1e-9
}

// ---------------------------------------------------------------------------
// Date pass
// ---------------------------------------------------------------------------

const MONTHS: Record<string, number> = {
  jan: 1,
  january: 1,
  januar: 1,
  janvier: 1,
  enero: 1,
  feb: 2,
  february: 2,
  februar: 2,
  fevrier: 2,
  febrero: 2,
  mar: 3,
  march: 3,
  marz: 3,
  mars: 3,
  marzo: 3,
  apr: 4,
  april: 4,
  avril: 4,
  abril: 4,
  may: 5,
  mai: 5,
  mayo: 5,
  jun: 6,
  june: 6,
  juni: 6,
  juin: 6,
  junio: 6,
  jul: 7,
  july: 7,
  juli: 7,
  juillet: 7,
  julio: 7,
  aug: 8,
  august: 8,
  aout: 8,
  agosto: 8,
  sep: 9,
  sept: 9,
  september: 9,
  septembre: 9,
  septiembre: 9,
  oct: 10,
  october: 10,
  okt: 10,
  oktober: 10,
  octobre: 10,
  octubre: 10,
  nov: 11,
  november: 11,
  novembre: 11,
  noviembre: 11,
  dec: 12,
  december: 12,
  dez: 12,
  dezember: 12,
  decembre: 12,
  diciembre: 12,
}

const MONTH_NAMES = Object.keys(MONTHS).join('|')

/** Date-like spans in folded text: numeric, "5 january 1961", "january 5, 1961". */
const DATE_TOKEN = new RegExp(
  [
    '\\d{4}[-/.]\\d{1,2}[-/.]\\d{1,2}',
    '\\d{1,2}[-/.]\\d{1,2}[-/.]\\d{2,4}',
    `\\d{1,2}\\.?\\s*(?:${MONTH_NAMES})\\.?\\s+\\d{2,4}`,
    `(?:${MONTH_NAMES})\\.?\\s+\\d{1,2}(?:st|nd|rd|th)?,?\\s+\\d{2,4}`,
  ].join('|'),
  'g',
)

function iso(y: number, m: number, d: number): string | null {
  if (m < 1 || m > 12 || d < 1 || d > 31) return null
  const year = y < 100 ? (y > 30 ? 1900 + y : 2000 + y) : y
  return `${String(year).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

/**
 * Every day a date string could denote, as ISO strings. Ambiguous numeric
 * dates (`03/04/1961`) yield both the D/M and M/D readings — the whole point
 * is to link a model-normalized ISO date back to whatever the document wrote.
 */
export function dateCandidates(raw: string): string[] {
  const s = foldNeedle(raw).trim()
  const out = new Set<string>()
  const add = (v: string | null) => {
    if (v) out.add(v)
  }

  let m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(s)
  if (m) add(iso(+m[1], +m[2], +m[3]))

  m = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/.exec(s)
  if (m) {
    add(iso(+m[3], +m[2], +m[1])) // D/M/Y
    add(iso(+m[3], +m[1], +m[2])) // M/D/Y
  }

  m = new RegExp(`^(\\d{1,2})\\.?\\s*(${MONTH_NAMES})\\.?\\s+(\\d{2,4})$`).exec(s)
  if (m) add(iso(+m[3], MONTHS[m[2]], +m[1]))

  m = new RegExp(`^(${MONTH_NAMES})\\.?\\s+(\\d{1,2})(?:st|nd|rd|th)?,?\\s+(\\d{2,4})$`).exec(s)
  if (m) add(iso(+m[3], MONTHS[m[1]], +m[2]))

  return [...out]
}

// ---------------------------------------------------------------------------
// Fuzzy pass
// ---------------------------------------------------------------------------

/**
 * Levenshtein distance, abandoned as soon as it exceeds `maxDist`.
 * The cutoff is what keeps the fuzzy pass affordable: candidates that are
 * obviously unrelated cost O(n·maxDist) instead of O(n·m).
 */
export function boundedLevenshtein(a: string, b: string, maxDist: number): number {
  if (Math.abs(a.length - b.length) > maxDist) return maxDist + 1
  let prev = new Array<number>(b.length + 1)
  let curr = new Array<number>(b.length + 1)
  for (let j = 0; j <= b.length; j++) prev[j] = j

  for (let i = 1; i <= a.length; i++) {
    curr[0] = i
    const from = Math.max(1, i - maxDist)
    const to = Math.min(b.length, i + maxDist)
    if (from > 1) curr[from - 1] = maxDist + 1
    let best = maxDist + 1
    for (let j = from; j <= to; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
      if (curr[j] < best) best = curr[j]
    }
    for (let j = to + 1; j <= b.length; j++) curr[j] = maxDist + 1
    if (best > maxDist) return maxDist + 1
    const tmp = prev
    prev = curr
    curr = tmp
  }
  return prev[b.length]
}

/** Trim a window to whole words so a highlight never starts mid-token. */
function snapToWords(text: string, start: number, end: number): [number, number] {
  let s = start
  let e = end
  while (s > 0 && WORDISH.test(text[s - 1]) && WORDISH.test(text[s])) s--
  while (e < text.length && WORDISH.test(text[e]) && WORDISH.test(text[e - 1])) e++
  while (s < e && !WORDISH.test(text[s])) s++
  while (e > s && !WORDISH.test(text[e - 1])) e--
  return [s, e]
}

/**
 * Approximate matches, anchored on the needle's rarest words.
 *
 * Scanning every offset of a long document is hopeless; instead the rarest
 * tokens of the needle nominate a handful of plausible positions, and only
 * those windows are scored.
 */
function fuzzyMatches(folded: FoldedText, needle: string): ProvenanceMatch[] {
  const hay = folded.text
  if (needle.length < FUZZY_MIN_LEN || hay.length > FUZZY_MAX_TEXT) return []
  const probe = needle.slice(0, FUZZY_MAX_NEEDLE)

  const tokens = [...new Set(probe.split(/[^\p{L}\p{N}]+/u).filter((t) => t.length >= 4))]
  if (!tokens.length) return []

  const counted = tokens
    .map((token) => ({ token, hits: findAll(hay, token, { limit: 25 }) }))
    .filter((t) => t.hits.length > 0)
    .sort((a, b) => a.hits.length - b.hits.length || b.token.length - a.token.length)
    .slice(0, 3)

  const maxDist = Math.floor(probe.length * (1 - FUZZY_MIN_SCORE))
  const seen = new Set<number>()
  const found: ProvenanceMatch[] = []
  let budget = FUZZY_MAX_CANDIDATES

  for (const { token, hits } of counted) {
    const offsetInNeedle = probe.indexOf(token)
    for (const [hitStart] of hits) {
      if (budget-- <= 0) break
      const anchor = Math.max(0, hitStart - offsetInNeedle)
      // Round to a coarse grid so the same region isn't scored three times.
      const bucket = Math.floor(anchor / Math.max(8, probe.length >> 2))
      if (seen.has(bucket)) continue
      seen.add(bucket)

      let best: { start: number; end: number; dist: number } | null = null
      for (const slack of [0, maxDist, -maxDist]) {
        const start = Math.max(0, anchor)
        const end = Math.min(hay.length, start + probe.length + slack)
        if (end <= start) continue
        const dist = boundedLevenshtein(probe, hay.slice(start, end), maxDist)
        if (dist <= maxDist && (!best || dist < best.dist)) best = { start, end, dist }
      }
      if (!best) continue

      const [s, e] = snapToWords(hay, best.start, best.end)
      if (e <= s) continue
      const [origStart, origEnd] = toOriginalRange(folded, s, e)
      found.push({
        start: origStart,
        end: origEnd,
        kind: 'fuzzy',
        score: 1 - best.dist / Math.max(probe.length, 1),
      })
    }
  }

  return found.sort((a, b) => b.score - a.score).slice(0, 3)
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

function literalMatches(
  text: string,
  folded: FoldedText,
  needle: string,
  kind: ProvenanceKind,
  limit: number,
): ProvenanceMatch[] {
  const wordBounded = needle.trim().length <= SHORT_VALUE_LEN

  // Verbatim first, so an exact hit is never demoted to "normalized".
  const exact = findAll(text, needle, { wordBounded, limit })
  if (exact.length) {
    return exact.map(([start, end]) => ({ start, end, kind, score: 1 }))
  }

  const foldedNeedle = foldNeedle(needle)
  if (!foldedNeedle) return []
  return findAll(folded.text, foldedNeedle, { wordBounded, limit }).map(([s, e]) => {
    const [start, end] = toOriginalRange(folded, s, e)
    return { start, end, kind: kind === 'exact' ? 'normalized' : kind, score: 1 }
  })
}

function numericMatches(folded: FoldedText, target: number, limit: number): ProvenanceMatch[] {
  const hits: ProvenanceMatch[] = []
  NUMBER_TOKEN.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = NUMBER_TOKEN.exec(folded.text)) !== null && hits.length < limit) {
    if (numericCandidates(m[0]).some((n) => numbersEqual(n, target))) {
      const [start, end] = toOriginalRange(folded, m.index, m.index + m[0].length)
      hits.push({ start, end, kind: 'numeric', score: 1 })
    }
  }
  return hits
}

function dateMatches(folded: FoldedText, wanted: string[], limit: number): ProvenanceMatch[] {
  const target = new Set(wanted)
  const hits: ProvenanceMatch[] = []
  DATE_TOKEN.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = DATE_TOKEN.exec(folded.text)) !== null && hits.length < limit) {
    if (dateCandidates(m[0]).some((c) => target.has(c))) {
      const [start, end] = toOriginalRange(folded, m.index, m.index + m[0].length)
      hits.push({ start, end, kind: 'date', score: 1 })
    }
  }
  return hits
}

/**
 * Locate `value` in `text`, strongest tier first.
 *
 * Returns an empty array when there is no evidence for the value in the
 * document — which the UI reports rather than hides.
 */
export function locateValue(
  text: string,
  value: unknown,
  options: LocateOptions = {},
): ProvenanceMatch[] {
  if (!text || isEmptyValue(value)) return []
  const limit = options.maxMatches ?? 20
  const folded = foldText(text)

  // 1. The model told us where it read this. Trust it only if the quote is
  //    actually in the document — a paraphrased "quote" is not provenance.
  if (options.quote?.trim()) {
    const quoted = literalMatches(text, folded, options.quote.trim(), 'quote', limit)
    if (quoted.length) return quoted
  }

  const isBool = typeof value === 'boolean'

  if (!isBool) {
    const raw = String(value)

    // 2. Verbatim, then case/whitespace/accent-folded.
    const literal = literalMatches(text, folded, raw, 'exact', limit)
    if (literal.length) return literal

    // 3. Same number written differently.
    if (typeof value === 'number' || /^[+-]?[\d.,\s]+$/.test(raw.trim())) {
      const targets = typeof value === 'number' ? [value] : numericCandidates(raw)
      for (const target of targets) {
        const hits = numericMatches(folded, target, limit)
        if (hits.length) return hits
      }
    }

    // 4. Same day written differently — the common LLM normalization.
    const days = dateCandidates(raw)
    if (days.length) {
      const hits = dateMatches(folded, days, limit)
      if (hits.length) return hits
    }
  }

  // 5. Booleans and enums usually have no literal counterpart; the honest
  //    fallback is to point at the field's own wording and say so.
  if ((isBool || typeof value === 'string') && options.label) {
    const hits = literalMatches(text, folded, options.label, 'label', 3)
    if (hits.length) return hits.map((m) => ({ ...m, kind: 'label' as const, score: 0.5 }))
  }

  // 6. Last resort: an approximate span.
  if (!isBool) {
    return fuzzyMatches(folded, foldNeedle(String(value)))
  }

  return []
}

/** The strongest match of a set — what the viewer scrolls to first. */
export function bestMatch(matches: ProvenanceMatch[]): ProvenanceMatch | null {
  if (!matches.length) return null
  return [...matches].sort(
    (a, b) => PROVENANCE_RANK[b.kind] - PROVENANCE_RANK[a.kind] || b.score - a.score,
  )[0]
}
