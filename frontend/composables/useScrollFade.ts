import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue'

/**
 * Toggle per-side edge-fade classes on a horizontally-scrollable element so the
 * fade only appears on the side that actually has content off-screen.
 *
 * The old `.scroll-fade-x` mask faded *both* edges unconditionally, which made
 * the first/last item of short (non-overflowing) strips — e.g. the project
 * workflow tabs — look dimmed for no reason. This adds `.scroll-fade-start` /
 * `.scroll-fade-end` (see assets/main.css) only when there's room to scroll in
 * that direction.
 *
 * Attach the returned nothing — just pass the element ref. Recomputes on scroll,
 * resize, and content changes (via ResizeObserver on the element).
 */
export function useScrollFade(target: Ref<HTMLElement | null>): void {
  let observer: ResizeObserver | null = null

  const update = (): void => {
    const el = target.value
    if (!el) return
    // A 1px threshold avoids sub-pixel rounding leaving a phantom fade.
    const hasStart = el.scrollLeft > 1
    const hasEnd = el.scrollLeft < el.scrollWidth - el.clientWidth - 1
    el.classList.toggle('scroll-fade-start', hasStart)
    el.classList.toggle('scroll-fade-end', hasEnd)
  }

  const attach = (el: HTMLElement | null): void => {
    if (!el) return
    el.addEventListener('scroll', update, { passive: true })
    observer = new ResizeObserver(update)
    observer.observe(el)
    update()
  }

  const detach = (el: HTMLElement | null): void => {
    if (el) el.removeEventListener('scroll', update)
    observer?.disconnect()
    observer = null
  }

  onMounted(() => {
    attach(target.value)
    window.addEventListener('resize', update, { passive: true })
  })

  // The element may mount after the composable (e.g. behind a v-if).
  watch(target, (el, prev) => {
    detach(prev ?? null)
    attach(el)
  })

  onBeforeUnmount(() => {
    detach(target.value)
    window.removeEventListener('resize', update)
  })
}
