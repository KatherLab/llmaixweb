<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="emit('cancel')"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6" @click.stop>
        <h3 class="text-lg font-semibold mb-2">{{ title }}</h3>
        <p class="text-gray-600 mb-6">{{ message }}</p>
        <div class="flex justify-end gap-3">
          <button
            @click="emit('cancel')"
            class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            {{ cancelText }}
          </button>
          <button
            @click="emit('confirm')"
            :class="['px-4 py-2 rounded-md', confirmButtonClass]"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue';

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

const confirmButtonClass = computed(() => {
  const variants = {
    'danger': 'bg-red-600 hover:bg-red-700 text-white',
    'warning': 'bg-yellow-600 hover:bg-yellow-700 text-white',
    'primary': 'bg-blue-600 hover:bg-blue-700 text-white'
  };
  return variants[props.confirmVariant] || variants.primary;
});
</script>