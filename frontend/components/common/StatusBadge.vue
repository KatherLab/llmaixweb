<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold',
      badgeClass,
      $attrs.class,
    ]"
  >
    <slot>{{ label || status }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getStatusBadgeClass, getPillClass } from '@/utils/statusStyles'

defineOptions({ inheritAttrs: false })

interface Props {
  status?: string
  label?: string
  // When set, uses the generic color pill map (dark-mode aware) instead of the
  // status map. Use for semantic non-status pills (counts, "active", match/
  // mismatch, …). Values: blue|green|yellow|red|purple|teal|cyan|orange|gray
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  status: '',
  label: '',
  color: '',
})

const badgeClass = computed(() =>
  props.color ? getPillClass(props.color) : getStatusBadgeClass(props.status),
)
</script>
