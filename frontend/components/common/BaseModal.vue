<template>
  <Teleport to="body">
    <transition :name="transitionName">
      <div
        v-if="open"
        :class="[
          'fixed inset-0 z-[10000] bg-black/30 backdrop-blur-md',
          placement === 'right'
            ? 'flex justify-end'
            : placement === 'fullscreen'
              ? 'flex items-center justify-center p-4 md:p-8'
              : 'flex items-center justify-center p-4',
        ]"
        @click="onBackdropClick"
      >
        <div
          ref="panelRef"
          :role="role"
          aria-modal="true"
          :aria-labelledby="title && !$slots.header ? titleId : undefined"
          tabindex="-1"
          :class="[
            placement === 'right'
              ? 'relative h-full w-full flex flex-col bg-surface shadow-xl border-l border-default overflow-hidden'
              : placement === 'fullscreen'
                ? 'relative bg-surface rounded-modal shadow-2xl w-full h-full flex flex-col overflow-hidden'
                : 'relative bg-surface rounded-modal shadow-2xl w-full flex flex-col max-h-[90vh] border border-default overflow-hidden',
            sizeClass,
            panelClass,
          ]"
          @click.stop
        >
          <!-- Header -->
          <div
            v-if="$slots.header || title || closeable"
            class="flex items-center justify-between gap-4 px-6 py-4 border-b border-default"
            :class="headerClass"
          >
            <slot name="header">
              <h3 :id="titleId" class="text-lg font-semibold text-content">
                {{ title }}
              </h3>
            </slot>
            <button
              v-if="closeable"
              type="button"
              class="text-content-subtle hover:text-content transition-colors"
              aria-label="Close"
              @click="emit('close')"
            >
              <X class="h-6 w-6" />
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto" :class="bodyClass">
            <slot />
          </div>

          <!-- Footer -->
          <div
            v-if="$slots.footer"
            class="px-6 py-4 border-t border-default flex justify-end gap-3"
            :class="footerClass"
          >
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted, nextTick, useId } from 'vue'
import { X } from '@lucide/vue'
import { useScrollLock } from '@/composables/useScrollLock'

// Shared stack of currently-open modals (drawers/dialogs/confirms all build on
// BaseModal). Every instance listens on `window`, so without the stack one
// Escape press would close EVERY open layer at once, and the focus traps of
// stacked dialogs would fight each other (making the top dialog impossible to
// Tab through). Only the top-most modal handles Escape and traps Tab.
const modalStack: symbol[] = []

interface Props {
  open: boolean
  title?: string
  // Accessible role: 'dialog' (default) or 'alertdialog' (for confirmations).
  role?: 'dialog' | 'alertdialog'
  size?: string
  // 'center' (modal dialog) | 'right' (slide-in drawer) | 'fullscreen' (near-fullscreen panel)
  placement?: 'center' | 'right' | 'fullscreen'
  closeable?: boolean
  closeOnBackdrop?: boolean
  closeOnEsc?: boolean
  panelClass?: string
  headerClass?: string
  bodyClass?: string
  footerClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  role: 'dialog',
  size: 'md',
  placement: 'center',
  closeable: true,
  closeOnBackdrop: true,
  closeOnEsc: true,
  panelClass: '',
  headerClass: '',
  bodyClass: 'p-6',
  footerClass: '',
})

const emit = defineEmits<{ (e: 'close'): void }>()

const panelRef = ref<HTMLElement | null>(null)
const titleId = useId()

// Identify this instance on the shared modal stack (see below).
const stackId = Symbol('BaseModal')

function isTopModal(): boolean {
  return modalStack[modalStack.length - 1] === stackId
}

function removeFromStack(): void {
  const i = modalStack.indexOf(stackId)
  if (i !== -1) modalStack.splice(i, 1)
}

const transitionName = computed(() =>
  props.placement === 'right'
    ? 'base-drawer-slide'
    : props.placement === 'fullscreen'
      ? 'base-modal-fade'
      : 'base-modal-fade',
)

const sizeClass = computed(() => {
  // Drawers and fullscreen ignore the centered-dialog max-width map.
  if (props.placement === 'right' || props.placement === 'fullscreen') return ''
  const sizes: Record<string, string> = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    '2xl': 'max-w-5xl',
    '3xl': 'max-w-6xl',
    full: 'max-w-7xl',
  }
  return sizes[props.size] || sizes.md
})

useScrollLock({ watch: () => props.open })

function onBackdropClick() {
  if (props.closeOnBackdrop) {
    emit('close')
  }
}

function onKeydown(e: KeyboardEvent) {
  // Only the top-most open modal reacts to the keyboard — a lower layer
  // handling Escape/Tab would close or steal focus from the dialog above it.
  if (!props.open || !isTopModal()) return
  if (e.key === 'Escape' && props.closeOnEsc) {
    emit('close')
    return
  }
  // Focus trap: keep Tab (and Shift+Tab) cycling within the dialog while open.
  if (e.key === 'Tab' && panelRef.value) {
    const focusable = panelRef.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
    )
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement as HTMLElement | null
    if (e.shiftKey) {
      if (active === first || !panelRef.value.contains(active)) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (active === last || !panelRef.value.contains(active)) {
        e.preventDefault()
        first.focus()
      }
    }
  }
}

// Remember the element that had focus before the dialog opened so it can be
// restored on close — keyboard users land back on the trigger (e.g. the button
// that opened the modal) instead of the top of the page.
let previouslyFocused: HTMLElement | null = null

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      modalStack.push(stackId)
      previouslyFocused = document.activeElement as HTMLElement | null
      nextTick(() => {
        // Focus the panel (or first focusable element) for keyboard users.
        const focusable = panelRef.value?.querySelector<HTMLElement>(
          'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
        )
        ;(focusable ?? panelRef.value)?.focus?.()
      })
    } else {
      removeFromStack()
      previouslyFocused?.focus?.()
      previouslyFocused = null
    }
  },
)

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // Components mounted with `open` already true never fire the watcher above.
  if (props.open) modalStack.push(stackId)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  removeFromStack()
})
</script>

<style scoped>
.base-modal-fade-enter-active,
.base-modal-fade-leave-active {
  transition: opacity 0.2s;
}
.base-modal-fade-enter-from,
.base-modal-fade-leave-to {
  opacity: 0;
}

/* Slide-in drawer transition (right-anchored). The whole overlay fades while
   the panel translates in/out from the right edge. */
.base-drawer-slide-enter-active,
.base-drawer-slide-leave-active {
  transition: opacity 0.3s ease-in-out;
}
.base-drawer-slide-enter-active > div,
.base-drawer-slide-leave-active > div {
  transition: transform 0.3s ease-in-out;
}
.base-drawer-slide-enter-from,
.base-drawer-slide-leave-to {
  opacity: 0;
}
.base-drawer-slide-enter-from > div,
.base-drawer-slide-leave-to > div {
  transform: translateX(100%);
}
</style>
