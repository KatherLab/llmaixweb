<script setup>
/**
 * Shared inline callout: leading icon + tinted box (title + body).
 *
 * Replaces the ~10 hand-rolled `bg-blue-50 border-blue-200 … dark:bg-blue-900/20`
 * info/warning boxes scattered across modals (DuplicatePreviewModal,
 * PromptFormModal, MetricsExportModal, DownloadModal, …). The tint comes from
 * the shared `getBannerClass` banner vocabulary so it matches the existing
 * StatusBanner/ModelTestCard colors exactly, dark mode included.
 *
 * Props:
 *  - variant : 'info' | 'warning' | 'danger' | 'success' | 'gray' (default 'info')
 *  - icon    : optional lucide component (rendered via <component :is>). If
 *              omitted, a sensible default is picked per variant.
 *  - title   : optional bold heading line
 *
 * Slots:
 *  - default : body content
 *  - icon    : override the leading icon entirely
 */
import { computed } from 'vue'
import { Info, AlertTriangle, CircleAlert, CircleCheckBig } from '@lucide/vue'
import { getBannerClass } from '@/utils/statusStyles'

const props = defineProps({
  variant: {
    type: String,
    default: 'info',
    validator: (v) => ['info', 'warning', 'danger', 'success', 'gray'].includes(v),
  },
  icon: { type: [Object, Function], default: undefined },
  title: { type: String, default: '' },
})

const COLOR_KEY = {
  info: 'blue',
  warning: 'amber',
  danger: 'red',
  success: 'green',
  gray: 'gray',
}

const DEFAULT_ICON = {
  info: Info,
  warning: AlertTriangle,
  danger: CircleAlert,
  success: CircleCheckBig,
  gray: Info,
}

const boxClass = computed(() => getBannerClass(COLOR_KEY[props.variant]))
const iconComp = computed(() => props.icon || DEFAULT_ICON[props.variant])
</script>

<template>
  <div :class="['flex items-start gap-2.5 rounded-lg p-3', boxClass]">
    <component
      :is="$slots.icon ? undefined : iconComp"
      v-if="!$slots.icon"
      class="w-5 h-5 flex-shrink-0 mt-0.5"
    />
    <slot v-else name="icon" />
    <div class="flex-1 text-sm">
      <p v-if="title" class="font-medium mb-0.5">{{ title }}</p>
      <slot />
    </div>
  </div>
</template>
