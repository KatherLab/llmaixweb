import { onBeforeUnmount } from 'vue'

/**
 * Debounce a search input — emits `onInput(value)` after `delay` ms of quiet.
 * Replaces the hand-rolled timer pattern duplicated across FilesFilterBar etc.
 *
 * @param onInput - called with the latest input value after the debounce window
 * @param delay
 * @returns {{ schedule: (value: string) => void, cancel: () => void }}
 */
export function useDebouncedSearch(
  onInput: (value: string) => void,
  delay = 300,
): {
  schedule: (value: string) => void
  cancel: () => void
} {
  let timer: ReturnType<typeof setTimeout> | null = null

  const schedule = (value: string): void => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => onInput(value), delay)
  }

  const cancel = (): void => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  onBeforeUnmount(cancel)

  return { schedule, cancel }
}
