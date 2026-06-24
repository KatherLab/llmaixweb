<template>
  <button
    v-bind="$attrs"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="[
      'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed',
      sizeClass,
      variantClass,
    ]"
  >
    <LoadingSpinner v-if="loading" size="small" :color="loadingIconColor" inline label="" />
    <slot />
  </button>
</template>

<script setup>
import { computed } from 'vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    // 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
  },
  size: {
    type: String,
    default: 'md',
    // 'sm' | 'md' | 'lg'
  },
  type: {
    type: String,
    default: 'button',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-3 py-1 text-sm'
    case 'lg':
      return 'px-5 py-2.5 text-base'
    default:
      return 'px-4 py-2 text-sm'
  }
})

const variantClass = computed(() => {
  switch (props.variant) {
    case 'secondary':
      return 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:ring-blue-500'
    case 'danger':
      return 'text-white bg-red-600 hover:bg-red-700 focus:ring-red-500'
    case 'warning':
      return 'text-white bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500'
    case 'success':
      return 'text-white bg-green-600 hover:bg-green-700 focus:ring-green-500'
    case 'ghost':
      return 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:ring-blue-500'
    default:
      return 'text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
  }
})

// Spinner icon inherits currentColor; on light variants use a darker tone.
const loadingIconColor = computed(() => {
  return props.variant === 'secondary' || props.variant === 'ghost' ? 'gray' : 'white'
})
</script>
