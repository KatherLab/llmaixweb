<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md"
        @click="emit('cancel')"
      >
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200" @click.stop>
          <div class="flex justify-between items-center mb-2">
            <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
            <button @click="emit('cancel')" class="text-gray-400 hover:text-gray-600 transition-colors" aria-label="Close">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p class="text-gray-600 mb-6">{{ message }}</p>
          <div class="flex justify-end gap-3">
            <button
              @click="emit('cancel')"
              class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
            >
              {{ cancelText }}
            </button>
            <button
              @click="emit('confirm')"
              :class="['px-4 py-2 rounded-lg', confirmButtonClass]"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue';
import { useScrollLock } from '@/composables/useScrollLock';

const props = defineProps({
  open: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Confirm Action'
  },
  message: {
    type: String,
    default: 'Are you sure you want to perform this action?'
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  confirmVariant: {
    type: String,
    default: 'danger' // 'danger', 'warning', 'primary'
  }
});

const emit = defineEmits(['confirm', 'cancel']);

useScrollLock({ watch: () => props.open });

const confirmButtonClass = computed(() => {
  const variants = {
    'danger': 'bg-red-600 hover:bg-red-700 text-white',
    'warning': 'bg-yellow-600 hover:bg-yellow-700 text-white',
    'primary': 'bg-blue-600 hover:bg-blue-700 text-white'
  };
  return variants[props.confirmVariant] || variants.primary;
});
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