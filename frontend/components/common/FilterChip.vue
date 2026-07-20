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
      class="hover:text-red-600 dark:hover:text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
      :aria-label="$t('common.filter_chip.remove', { label })"
      @click="$emit('remove')"
    >
      <X class="w-3 h-3" aria-hidden="true" />
    </button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from '@lucide/vue'
import { getPillClass } from '@/utils/statusStyles'

defineOptions({ inheritAttrs: false })

interface Props {
  label?: string
  // 'blue' | 'green' | 'yellow' | 'red' | 'gray' | 'purple' | 'teal' | 'cyan' | 'orange'
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  color: 'blue',
})

defineEmits<{ (e: 'remove'): void }>()

const colorClass = computed(() => getPillClass(props.color))
</script>
