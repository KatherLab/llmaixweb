<template>
  <span
    :class="[
      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold',
      badgeClass,
      $attrs.class,
    ]"
  >
    <slot>{{ label || status }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { getStatusBadgeClass, getPillClass } from '@/utils/statusStyles'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  status: {
    type: String,
    default: '',
  },
  label: {
    type: String,
    default: '',
  },
  // When set, uses the generic color pill map (dark-mode aware) instead of the
  // status map. Use for semantic non-status pills (counts, "active", match/
  // mismatch, …). Values: blue|green|yellow|red|purple|indigo|teal|cyan|orange|gray
  color: {
    type: String,
    default: '',
  },
})

const badgeClass = computed(() =>
  props.color ? getPillClass(props.color) : getStatusBadgeClass(props.status),
)
</script>
