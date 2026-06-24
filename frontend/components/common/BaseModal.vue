<template>
  <Teleport to="body">
    <transition name="base-modal-fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-black/30 backdrop-blur-md"
        @click="onBackdropClick"
      >
        <div
          ref="panelRef"
          :class="[
            'relative bg-white rounded-2xl shadow-2xl w-full flex flex-col max-h-[90vh] border border-gray-200 overflow-hidden',
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

const sizeClass = computed(() => {
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
</style>
