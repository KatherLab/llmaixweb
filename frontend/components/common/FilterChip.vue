<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
      colorClass,
      $attrs.class,
    ]"
  >
    {{ label }}<slot />
    <button
      type="button"
      class="hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
      :aria-label="'Remove ' + label"
      @click="$emit('remove')"
    >
      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
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
import { getPillClass } from '@/utils/statusStyles'

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

const colorClass = computed(() => getPillClass(props.color))
</script>
