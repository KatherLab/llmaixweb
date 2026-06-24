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
import { ref, computed, watch } from 'vue'

export function usePagination(options = {}) {
  const { getTotal = () => 0, pageSize = 10 } = options

  const currentPage = ref(1)
  const totalPages = computed(() => Math.max(1, Math.ceil(getTotal() / pageSize)))
  const offset = computed(() => (currentPage.value - 1) * pageSize)

  const visiblePages = computed(() => {
    const pages = []
    const total = totalPages.value
    const current = currentPage.value

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
  })

  function next() {
    if (currentPage.value < totalPages.value) currentPage.value++
  }
  function prev() {
    if (currentPage.value > 1) currentPage.value--
  }
  function first() {
    currentPage.value = 1
  }
  function last() {
    currentPage.value = totalPages.value
  }
  function reset() {
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
