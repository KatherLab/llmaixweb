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
import { getStatusBadgeClass } from '@/utils/statusStyles'

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
})

const badgeClass = computed(() => getStatusBadgeClass(props.status))
</script>
