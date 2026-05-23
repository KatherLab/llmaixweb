/**
 * Composable for locking/unlocking body scroll when modals are open.
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

export function useScrollLock(options = {}) {
  const { autoLock = false, watch: watchRef = null } = options

  function lockScroll() {
    document.body.style.overflow = 'hidden'
  }

  function unlockScroll() {
    document.body.style.overflow = ''
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
    }
  }

  // Auto-lock as soon as the component mounts
  if (autoLock) {
    onMounted(lockScroll)
    onUnmounted(unlockScroll)
  }

  return { lockScroll, unlockScroll }
}
