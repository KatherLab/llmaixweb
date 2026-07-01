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
    wrapper:
      'bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden',
    /** The `<table>` element. */
    table: 'min-w-full divide-y divide-slate-200 dark:divide-slate-700',
    /** `<thead>` — header row background. */
    thead: 'bg-slate-50 dark:bg-slate-800',
    /** `<th>` — header cell. */
    th: `${cellPadding} text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider`,
    /** `<tbody>` — body rows. */
    tbody: 'bg-white dark:bg-slate-900 divide-y divide-slate-200 dark:divide-slate-700',
    /** `<tr>` — body row (hover highlight). */
    tr: 'hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors',
    /** `<td>` — body cell. */
    td: `${cellPadding} text-sm text-slate-700 dark:text-slate-300`,
  }
}
