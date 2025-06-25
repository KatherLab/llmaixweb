<script setup>
import { computed } from 'vue';

const props = defineProps({
  size: {
    type: String,
    default: 'medium', // small, medium, large
  },
  message: {
    type: String,
    default: 'Loading...',
  },
});

const sizeClass = computed(() => {
  const sizes = {
    'small': 'h-4 w-4',
    'medium': 'h-8 w-8',
    'large': 'h-12 w-12',
  };
  return sizes[props.size] || sizes.medium;
});
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12">
    <svg
      :class="['animate-spin', sizeClass]"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      ></circle>
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
    <span v-if="props.message" class="mt-2 text-sm text-gray-500">{{
      props.message
    }}</span>
  </div>
</template>