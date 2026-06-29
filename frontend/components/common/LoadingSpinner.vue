<template>
  <!--
    Standalone (non-inline): centered spinner in a polite live region. The
    visually-hidden `label` gives screen readers an accessible name.
  -->
  <div v-if="!inline" class="flex items-center justify-center" role="status" aria-live="polite">
    <div
      :class="['animate-spin rounded-full border-b-2', colorClass, sizeClasses]"
      :aria-hidden="decorative ? 'true' : undefined"
    ></div>
    <span v-if="!decorative" class="sr-only">{{ label }}</span>
  </div>
  <!--
    Inline: sits next to text or inside a button. When `label` is empty the
    spinner is decorative (aria-hidden) since adjacent text conveys meaning;
    otherwise it carries role=status + aria-label.
  -->
  <div
    v-else
    :class="['inline-block animate-spin rounded-full border-b-2', colorClass, sizeClasses]"
    :role="decorative ? undefined : 'status'"
    :aria-live="decorative ? undefined : 'polite'"
    :aria-label="decorative ? undefined : label"
    :aria-hidden="decorative ? 'true' : undefined"
  ></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value),
  },
  color: {
    type: String,
    default: 'blue',
    // 'blue' | 'white' | 'gray' | 'current'
  },
  inline: {
    type: Boolean,
    default: false,
  },
  // Accessible label announced to screen readers. Pass an empty string ('')
  // to mark the spinner decorative (aria-hidden) when it sits next to visible
  // text that already conveys the loading state.
  label: {
    type: String,
    default: 'Loading',
  },
})

const decorative = computed(() => props.label === '')

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'small':
      return 'h-4 w-4'
    case 'large':
      return 'h-12 w-12'
    default:
      return 'h-8 w-8'
  }
})

const colorClass = computed(() => {
  switch (props.color) {
    case 'white':
      return 'border-white'
    case 'gray':
      return 'border-slate-400'
    case 'current':
      return 'border-current'
    default:
      return 'border-blue-600'
  }
})
</script>
