/**
 * Composable for locking/unlocking body scroll when modals are open.
 *
 * Uses a module-level counter so that nested/stacked modals don't prematurely
 * unlock the body scroll: each lock() increments, each unlock() decrements,
 * and the overflow is only restored when the count returns to zero.
 *
 * Usage:
 *   const { lockScroll, unlockScroll } = useScrollLock();
 *
 * Auto-lock on mount + unlock on unmount (most common pattern):
 *   useScrollLock({ autoLock: true });
 *
 * Watch a reactive ref (e.g. props.open):
 *   useScrollLock({ watch: () => props.open });
 *
 * Or use the returned functions manually:
 *   const { lockScroll, unlockScroll } = useScrollLock();
 *   onMounted(lockScroll);
 *   onUnmounted(unlockScroll);
 */
import { watch, onMounted, onUnmounted } from 'vue'

// Module-level lock counter shared across all useScrollLock consumers.
let lockCount = 0

export function useScrollLock(options = {}) {
  const { autoLock = false, watch: watchRef = null } = options

  function lockScroll() {
    lockCount++
    if (lockCount === 1) {
      document.body.style.overflow = 'hidden'
    }
  }

  function unlockScroll() {
    if (lockCount === 0) return
    lockCount--
    if (lockCount === 0) {
      document.body.style.overflow = ''
    }
  }

  // Auto-lock based on a reactive ref
  if (watchRef !== null) {
    watch(watchRef, (val) => {
      if (val) {
        lockScroll()
      } else {
        unlockScroll()
      }
    })
    // Also check initial value
    if (typeof watchRef === 'function' ? watchRef() : watchRef.value) {
      onMounted(lockScroll)
      onUnmounted(unlockScroll)
    }
  }

  // Auto-lock as soon as the component mounts
  if (autoLock) {
    onMounted(lockScroll)
    onUnmounted(unlockScroll)
  }

  return { lockScroll, unlockScroll }
}
