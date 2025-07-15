<template>
  <div class="flex items-center justify-center">
    <div
      :class="[
        'animate-spin rounded-full border-b-2 border-blue-600',
        sizeClasses
      ]"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  }
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'small':
      return 'h-4 w-4';
    case 'large':
      return 'h-12 w-12';
    default:
      return 'h-8 w-8';
  }
});
</script>
