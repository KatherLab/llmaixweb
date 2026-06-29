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
      <X class="w-3 h-3" aria-hidden="true" />
    </button>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { X } from '@lucide/vue'
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
    // 'blue' | 'green' | 'yellow' | 'red' | 'gray' | 'purple' | 'teal' | 'cyan' | 'orange'
  },
})

defineEmits(['remove'])

const colorClass = computed(() => getPillClass(props.color))
</script>
