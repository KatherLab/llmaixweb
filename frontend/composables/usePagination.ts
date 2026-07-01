/**
 * Composable for client/server-side pagination state.
 * Replaces the duplicated currentPage/totalPages/visiblePages logic
 * in DocumentsManagement and DocumentsGroups.
 *
 * Usage:
 *   const { currentPage, totalPages, visiblePages, reset } = usePagination({
 *     getTotal: () => totalCount.value,
 *     pageSize: 10,
 *   })
 *
 * Note: `getTotal` is read once during setup (the internal `watch(totalPages)`
 * registers its source eagerly), so any ref it references — e.g. `totalCount` —
 * MUST be declared before this call. Declaring it after throws a temporal-dead-zone
 * ReferenceError ("can't access lexical declaration before initialization").
 */
import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'

/**
 * Pure ellipsis-window pagination algorithm: returns the page numbers (and
 * '...' gaps) to display for a given current page / total. Shared by
 * usePagination's `visiblePages` and any component that owns its own page
 * state (e.g. server-side offset/limit pagination in EvaluationView,
 * ViewDocumentGroupModal) so the algorithm isn't copy-pasted.
 *
 * @param current - 1-indexed current page
 * @param total   - total number of pages (>= 1)
 * @returns pages to render
 */
export function computeVisiblePages(current: number, total: number): (number | '...')[] {
  const pages: (number | '...')[] = []
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else if (current <= 3) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  } else if (current >= total - 2) {
    pages.push(1)
    pages.push('...')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    pages.push('...')
    for (let i = current - 1; i <= current + 1; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  }
  return pages.filter((p) => p === '...' || (p >= 1 && p <= total))
}

interface UsePaginationOptions {
  /** Returns the total item count (drives `totalPages`). */
  getTotal?: () => number
  /** Page size used to compute total pages and the offset. */
  pageSize?: number
}

interface UsePaginationReturn {
  currentPage: Ref<number>
  totalPages: ComputedRef<number>
  offset: ComputedRef<number>
  visiblePages: ComputedRef<(number | '...')[]>
  next: () => void
  prev: () => void
  first: () => void
  last: () => void
  reset: () => void
}

export function usePagination(options: UsePaginationOptions = {}): UsePaginationReturn {
  const { getTotal = () => 0, pageSize = 10 } = options

  const currentPage = ref(1)
  const totalPages = computed(() => Math.max(1, Math.ceil(getTotal() / pageSize)))
  const offset = computed(() => (currentPage.value - 1) * pageSize)

  const visiblePages = computed(() => computeVisiblePages(currentPage.value, totalPages.value))

  function next(): void {
    if (currentPage.value < totalPages.value) currentPage.value++
  }
  function prev(): void {
    if (currentPage.value > 1) currentPage.value--
  }
  function first(): void {
    currentPage.value = 1
  }
  function last(): void {
    currentPage.value = totalPages.value
  }
  function reset(): void {
    currentPage.value = 1
  }

  // Clamp page if total shrinks below current page
  watch(totalPages, (total) => {
    if (currentPage.value > total) currentPage.value = total
  })

  return {
    currentPage,
    totalPages,
    offset,
    visiblePages,
    next,
    prev,
    first,
    last,
    reset,
  }
}
