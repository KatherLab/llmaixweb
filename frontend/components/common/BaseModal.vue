<template>
  <Teleport to="body">
    <transition :name="transitionName">
      <div
        v-if="open"
        :class="[
          'fixed inset-0 z-[10000] bg-black/30 backdrop-blur-md',
          placement === 'right' ? 'flex justify-end' : 'flex items-center justify-center p-4',
        ]"
        @click="onBackdropClick"
      >
        <div
          ref="panelRef"
          :class="[
            placement === 'right'
              ? 'relative h-full w-full flex flex-col bg-white shadow-xl border-l border-gray-200 overflow-hidden'
              : 'relative bg-white rounded-2xl shadow-2xl w-full flex flex-col max-h-[90vh] border border-gray-200 overflow-hidden',
            sizeClass,
            panelClass,
          ]"
          @click.stop
        >
          <!-- Header -->
          <div
            v-if="$slots.header || title || closeable"
            class="flex items-center justify-between gap-4 px-6 py-4 border-b border-gray-200"
            :class="headerClass"
          >
            <slot name="header">
              <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
            </slot>
            <button
              v-if="closeable"
              type="button"
              class="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close"
              @click="emit('close')"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto" :class="bodyClass">
            <slot />
          </div>

          <!-- Footer -->
          <div
            v-if="$slots.footer"
            class="px-6 py-4 border-t border-gray-200 flex justify-end gap-3"
            :class="footerClass"
          >
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  title: {
    type: String,
    default: '',
  },
  size: {
    type: String,
    default: 'md',
    // 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | 'full'
  },
  placement: {
    type: String,
    default: 'center',
    // 'center' (modal dialog) | 'right' (slide-in drawer)
  },
  closeable: {
    type: Boolean,
    default: true,
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true,
  },
  closeOnEsc: {
    type: Boolean,
    default: true,
  },
  panelClass: {
    type: String,
    default: '',
  },
  headerClass: {
    type: String,
    default: '',
  },
  bodyClass: {
    type: String,
    default: 'p-6',
  },
  footerClass: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

const panelRef = ref(null)

const transitionName = computed(() =>
  props.placement === 'right' ? 'base-drawer-slide' : 'base-modal-fade',
)

const sizeClass = computed(() => {
  // Drawers ignore the centered-dialog max-width map; width comes from panelClass.
  if (props.placement === 'right') return ''
  const sizes = {
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

function onKeydown(e) {
  if (e.key === 'Escape' && props.open && props.closeOnEsc) {
    emit('close')
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      nextTick(() => {
        // Focus the panel for keyboard users; safe no-op if not focusable.
        panelRef.value?.focus?.()
      })
    }
  },
)

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
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
