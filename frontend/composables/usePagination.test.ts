import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'
import { computeVisiblePages, usePagination } from './usePagination'

describe('computeVisiblePages', () => {
  it('lists every page when there are seven or fewer', () => {
    expect(computeVisiblePages(1, 5)).toEqual([1, 2, 3, 4, 5])
    expect(computeVisiblePages(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it('shows a leading window near the start', () => {
    expect(computeVisiblePages(2, 10)).toEqual([1, 2, 3, 4, 5, '...', 10])
  })

  it('shows a trailing window near the end', () => {
    expect(computeVisiblePages(10, 10)).toEqual([1, '...', 6, 7, 8, 9, 10])
  })

  it('shows a centered window in the middle', () => {
    expect(computeVisiblePages(6, 10)).toEqual([1, '...', 5, 6, 7, '...', 10])
  })
})

describe('usePagination', () => {
  it('computes total pages and offset from the total and page size', () => {
    const total = ref(25)
    const { totalPages, offset, currentPage } = usePagination({
      getTotal: () => total.value,
      pageSize: 10,
    })
    expect(totalPages.value).toBe(3)
    expect(offset.value).toBe(0)
    currentPage.value = 3
    expect(offset.value).toBe(20)
  })

  it('navigates without stepping out of bounds', () => {
    const { currentPage, next, prev, first, last } = usePagination({
      getTotal: () => 25,
      pageSize: 10,
    })
    prev()
    expect(currentPage.value).toBe(1)
    next()
    next()
    next()
    expect(currentPage.value).toBe(3)
    last()
    expect(currentPage.value).toBe(3)
    first()
    expect(currentPage.value).toBe(1)
  })

  it('clamps the current page when the total shrinks below it', async () => {
    const total = ref(25)
    const { currentPage, last } = usePagination({ getTotal: () => total.value, pageSize: 10 })
    last()
    expect(currentPage.value).toBe(3)
    total.value = 5
    await nextTick()
    expect(currentPage.value).toBe(1)
  })

  it('stays reactive to a ref page size', () => {
    const size = ref(10)
    const { totalPages } = usePagination({ getTotal: () => 25, pageSize: size })
    expect(totalPages.value).toBe(3)
    size.value = 25
    expect(totalPages.value).toBe(1)
  })
})
