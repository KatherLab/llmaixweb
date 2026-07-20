import { onBeforeUnmount, onMounted, type Ref } from 'vue'

/**
 * Invoke `callback` when a click lands outside the `target` element.
 *
 * Replaces the broken `@click.outside` template usages — Vue has no `.outside`
 * modifier, so those silently compiled to a plain `@click` on the panel itself
 * (i.e. the inverted behavior: clicking *inside* closed the panel).
 *
 * Attach `target` to a wrapper that contains BOTH the trigger button and the
 * popover panel, otherwise clicking the trigger while open closes the panel
 * via this handler and immediately re-opens it via the trigger's own @click.
 *
 * The listener runs in the capture phase so `stopPropagation()` inside
 * unrelated components can't swallow the event. Must be called during
 * component setup (registers mount/unmount hooks).
 */
export function useClickOutside(
  target: Ref<HTMLElement | null>,
  callback: (event: MouseEvent) => void,
): void {
  const handler = (event: MouseEvent): void => {
    const el = target.value
    if (!el) return
    if (event.target instanceof Node && !el.contains(event.target)) {
      callback(event)
    }
  }

  onMounted(() => document.addEventListener('click', handler, true))
  onBeforeUnmount(() => document.removeEventListener('click', handler, true))
}
