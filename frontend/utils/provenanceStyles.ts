/**
 * Shared visual language for provenance confidence.
 *
 * The dot next to a value in the Result pane and the highlight in the Source
 * pane must read as the same statement, so both take their colours and their
 * wording from this one table. Colour carries confidence: green = the text
 * says exactly this, amber = the same fact written differently, orange =
 * approximate or field-level only.
 */
import type { ProvenanceKind } from './provenance'

export interface ProvenanceStyle {
  /** Classes for a <mark> in the source text. */
  mark: string
  /** Classes for the small confidence dot beside a value. */
  dot: string
  /** i18n key for the tier name ("Verbatim", "Approximate", …). */
  labelKey: string
  /** i18n key for the one-line explanation shown on hover. */
  descKey: string
}

export const PROVENANCE_STYLES: Record<ProvenanceKind, ProvenanceStyle> = {
  quote: {
    mark: 'bg-emerald-200/80 text-emerald-950 dark:bg-emerald-500/35 dark:text-emerald-50',
    dot: 'bg-emerald-500',
    labelKey: 'trials.provenance.kind.quote',
    descKey: 'trials.provenance.desc.quote',
  },
  exact: {
    mark: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-500/25 dark:text-emerald-100',
    dot: 'bg-emerald-500',
    labelKey: 'trials.provenance.kind.exact',
    descKey: 'trials.provenance.desc.exact',
  },
  normalized: {
    mark: 'bg-amber-100 text-amber-900 dark:bg-amber-400/25 dark:text-amber-100',
    dot: 'bg-amber-500',
    labelKey: 'trials.provenance.kind.normalized',
    descKey: 'trials.provenance.desc.normalized',
  },
  numeric: {
    mark: 'bg-amber-100 text-amber-900 dark:bg-amber-400/25 dark:text-amber-100',
    dot: 'bg-amber-500',
    labelKey: 'trials.provenance.kind.numeric',
    descKey: 'trials.provenance.desc.numeric',
  },
  date: {
    mark: 'bg-amber-100 text-amber-900 dark:bg-amber-400/25 dark:text-amber-100',
    dot: 'bg-amber-500',
    labelKey: 'trials.provenance.kind.date',
    descKey: 'trials.provenance.desc.date',
  },
  label: {
    mark: 'bg-orange-100/70 text-orange-900 underline decoration-dotted dark:bg-orange-400/20 dark:text-orange-100',
    dot: 'bg-orange-400',
    labelKey: 'trials.provenance.kind.label',
    descKey: 'trials.provenance.desc.label',
  },
  fuzzy: {
    mark: 'bg-orange-100/70 text-orange-900 underline decoration-dashed dark:bg-orange-400/20 dark:text-orange-100',
    dot: 'bg-orange-400',
    labelKey: 'trials.provenance.kind.fuzzy',
    descKey: 'trials.provenance.desc.fuzzy',
  },
}

/**
 * Dot for a value with no citation but a note from the model.
 *
 * There is deliberately no style for "could not be located": a value the text
 * search cannot place is not a finding. Booleans and derived answers are often
 * correct with nothing to quote, and telling the user it "was not found in the
 * text" reads as a warning about the extraction rather than a limit of the
 * search. Values without a citation simply show nothing.
 */
export const PROVENANCE_NOTE_ONLY = 'bg-transparent border border-content-subtle'
