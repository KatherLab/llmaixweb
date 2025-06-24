<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  actionText: {
    type: String,
    default: 'Get Started'
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['action']);
</script>

<template>
  <div class="text-center p-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
    <slot name="icon">
      <!-- Default icon if no custom icon is provided -->
      <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
      </svg>
    </slot>

    <h3 class="mt-4 text-lg font-medium text-gray-900">{{ title }}</h3>
    <p class="mt-1 text-sm text-gray-500">{{ description }}</p>

    <div class="mt-6">
      <button
        @click="emit('action')"
        :disabled="disabled"
        class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
      >
        {{ actionText }}
      </button>
    </div>
  </div>
</template>
