<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="modelValue || open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click="handleBackdropClick"
      >
        <div
          class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col border border-gray-200"
          @click.stop
        >
          <!-- Header with close button -->
          <div v-if="title" class="flex items-center justify-between px-6 py-4 border-b bg-gray-50 rounded-t-2xl">
            <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
            <button
              type="button"
              class="text-gray-400 hover:text-gray-600 transition-colors"
              @click="close"
              aria-label="Close"
            >
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto p-6">
            <button
              v-if="!title"
              type="button"
              class="absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition-colors"
              @click="close"
              aria-label="Close"
            >
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <slot></slot>
          </div>

          <!-- Actions footer -->
          <div v-if="$slots.actions" class="px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
            <slot name="actions"></slot>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { watch } from 'vue';
import { useScrollLock } from '@/composables/useScrollLock';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  open: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:modelValue', 'close']);

const isOpen = () => props.modelValue || props.open;

useScrollLock({ watch: () => isOpen() });

const close = () => {
  emit('update:modelValue', false);
  emit('close');
};

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    close();
  }
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
