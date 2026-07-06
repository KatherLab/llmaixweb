<template>
  <button
    v-bind="$attrs"
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    :class="[baseClass, sizeClass, variantClass]"
  >
    <LoadingSpinner v-if="loading" size="small" :color="loadingIconColor" inline label="" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineOptions({ inheritAttrs: false })

interface Props {
  // 'primary' | 'secondary' | 'danger' | 'warning' | 'success' | 'ghost' | 'link' | 'icon'
  variant?: 'primary' | 'secondary' | 'danger' | 'warning' | 'success' | 'ghost' | 'link' | 'icon'
  // 'sm' | 'md' | 'lg'
  size?: 'sm' | 'md' | 'lg'
  // Used by variant="link" and variant="icon": sets the text/hover color tone.
  // 'blue' | 'red' | 'green' | 'purple' | 'gray'
  tone?: 'blue' | 'red' | 'green' | 'purple' | 'gray'
  type?: 'button' | 'submit' | 'reset'
  loading?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  tone: 'blue',
  type: 'button',
  loading: false,
  disabled: false,
})

const baseClass =
  'inline-flex items-center justify-center gap-2 font-medium rounded-card transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed'

const sizeClass = computed(() => {
  // Link + icon buttons are inline actions — no horizontal padding, inherit
  // surrounding size. Icon buttons get square padding for an icon-only hit area.
  if (props.variant === 'link') return ''
  if (props.variant === 'icon') return 'p-1.5'
  switch (props.size) {
    case 'sm':
      return 'px-3 py-1 text-sm'
    case 'lg':
      return 'px-5 py-2.5 text-base'
    default:
      return 'px-4 py-2 text-sm'
  }
})

const linkToneClass = computed(() => {
  switch (props.tone) {
    case 'red':
      return 'text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300'
    case 'green':
      return 'text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300'
    case 'gray':
      return 'text-content-muted hover:text-content'
    default:
      return 'text-primary hover:bg-primary-hover'
  }
})

// Icon buttons: muted gray default, colored text + tinted bg on hover.
const iconToneClass = computed(() => {
  switch (props.tone) {
    case 'red':
      return 'hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
    case 'green':
      return 'hover:text-green-600 dark:hover:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
    case 'purple':
      return 'hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20'
    case 'gray':
      return 'hover:text-content hover:bg-surface-muted'
    default:
      return 'hover:text-primary hover:bg-primary-soft'
  }
})

const variantClass = computed(() => {
  switch (props.variant) {
    case 'secondary':
      return 'text-content bg-surface border border-strong hover:bg-surface-muted focus:ring-ring'
    case 'danger':
      return 'text-white bg-red-600 hover:bg-red-700 focus:ring-red-500'
    case 'warning':
      return 'text-white bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500'
    case 'success':
      return 'text-white bg-green-600 hover:bg-green-700 focus:ring-green-500'
    case 'ghost':
      return 'text-content-muted hover:text-content hover:bg-surface-muted focus:ring-ring'
    case 'link':
      return linkToneClass.value
    case 'icon':
      return ['text-content-subtle transition-colors', iconToneClass.value].join(' ')
    default:
      return 'text-white bg-primary hover:bg-primary-hover focus:ring-ring'
  }
})

// Spinner icon inherits currentColor; on light variants use a darker tone.
const loadingIconColor = computed(() => {
  return props.variant === 'secondary' || props.variant === 'ghost' ? 'gray' : 'white'
})
</script>
