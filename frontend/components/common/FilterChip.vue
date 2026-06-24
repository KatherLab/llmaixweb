<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
      colorClass,
      $attrs.class,
    ]"
  >
    {{ label }}<slot />
    <button type="button" class="hover:text-red-600" @click="$emit('remove')">
      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </span>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  color: {
    type: String,
    default: 'blue',
    // 'blue' | 'green' | 'yellow' | 'red' | 'gray' | 'purple' | 'indigo' | 'teal' | 'cyan' | 'orange'
  },
})

defineEmits(['remove'])

const colorClass = computed(() => {
  const colors = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
    teal: 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300',
    cyan: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
    gray: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300',
  }
  return colors[props.color] || colors.blue
})
</script>
