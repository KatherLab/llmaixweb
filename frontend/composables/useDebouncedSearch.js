import { onBeforeUnmount } from 'vue'

/**
 * Debounce a search input — emits `onInput(value)` after `delay` ms of quiet.
 * Replaces the hand-rolled timer pattern duplicated across FilesFilterBar etc.
 *
 * @param {Function} onInput - called with the latest input value after the debounce window
 * @param {number} [delay=300]
 * @returns {{ schedule: (value: string) => void, cancel: () => void }}
 */
export function useDebouncedSearch(onInput, delay = 300) {
  let timer = null

  const schedule = (value) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => onInput(value), delay)
  }

  const cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  onBeforeUnmount(cancel)

  return { schedule, cancel }
}
