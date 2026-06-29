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

  // Auto-lock based on a reactive ref.
  // Tracks whether THIS instance currently holds a lock, so the unmount hook
  // only releases what it acquired (the counter is shared/module-level).
  if (watchRef !== null) {
    let holdsLock = false

    // If already open at mount, acquire the lock immediately.
    if (typeof watchRef === 'function' ? watchRef() : watchRef.value) {
      onMounted(() => {
        lockScroll()
        holdsLock = true
      })
    }

    watch(watchRef, (val) => {
      if (val) {
        lockScroll()
        holdsLock = true
      } else {
        unlockScroll()
        holdsLock = false
      }
    })

    // Safety net: if the component unmounts while still open (e.g. a tab/route
    // switch tears down a component whose modal is open, or a leave-transition
    // is interrupted), release the lock so body scroll isn't stuck forever.
    onUnmounted(() => {
      if (holdsLock) {
        unlockScroll()
        holdsLock = false
      }
    })
  }

  // Auto-lock as soon as the component mounts
  if (autoLock) {
    onMounted(lockScroll)
    onUnmounted(unlockScroll)
  }

  return { lockScroll, unlockScroll }
}
