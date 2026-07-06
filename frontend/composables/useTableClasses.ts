/**
 * Shared class strings for the custom HTML `<table>` components.
 *
 * Collapses the drift across FilesTable, DocumentsTable, DocumentsGroups,
 * EvaluationView, ViewDocumentGroupModal
 * and FilePreviewModal — which each hand-rolled slightly different radius,
 * padding, header weight, divider and dark-mode classes (several with no dark
 * variants at all, leaving tables unreadable in dark mode).
 *
 * Usage:
 *   const t = useTableClasses()
 *   // <div :class="t.wrapper"><table :class="t.table">…
 *   const t = useTableClasses({ density: 'compact' }) // denser rows for previews
 *
 * Callers compose extra classes onto these (e.g. a sortable `<th>` adds
 * `'cursor-pointer select-none'`, an actions column adds `'text-right'`).
 *
 * @param options
 * @param options.density  row/cell padding
 */
interface UseTableClassesOptions {
  /** Row/cell padding. */
  density?: 'default' | 'compact'
}

interface TableClasses {
  /** Card wrapper around a table (with overflow clipping for sticky headers). */
  wrapper: string
  /** The `<table>` element. */
  table: string
  /** `<thead>` — header row background. */
  thead: string
  /** `<th>` — header cell. */
  th: string
  /** `<tbody>` — body rows. */
  tbody: string
  /** `<tr>` — body row (hover highlight). */
  tr: string
  /** `<td>` — body cell. */
  td: string
}

export function useTableClasses({
  density = 'default',
}: UseTableClassesOptions = {}): TableClasses {
  const cellPadding = density === 'compact' ? 'px-3 py-2' : 'px-4 py-3'

  return {
    /** Card wrapper around a table (with overflow clipping for sticky headers). */
    wrapper: 'bg-surface rounded-card border border-default shadow-sm overflow-hidden',
    /** The `<table>` element. */
    table: 'min-w-full divide-y divide-default',
    /** `<thead>` — header row background. */
    thead: 'bg-surface-muted',
    /** `<th>` — header cell. */
    th: `${cellPadding} text-left text-xs font-semibold text-content-muted uppercase tracking-wider`,
    /** `<tbody>` — body rows. */
    tbody: 'bg-surface divide-y divide-default',
    /** `<tr>` — body row (hover highlight). */
    tr: 'hover:bg-surface-muted transition-colors',
    /** `<td>` — body cell. */
    td: `${cellPadding} text-sm text-content`,
  }
}
