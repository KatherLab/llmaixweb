<template>
  <div
    :role="type === 'error' ? 'alert' : 'status'"
    :aria-live="type === 'error' ? 'assertive' : 'polite'"
    class="relative flex items-center gap-3 w-80 max-w-[calc(100vw-2rem)] py-2.5 pl-3 pr-2 rounded-modal border border-default bg-surface/90 backdrop-blur-md shadow-lg shadow-slate-900/5 overflow-hidden"
  >
    <!-- Colored accent + progress bar at the bottom edge. -->
    <div class="absolute inset-y-0 left-0 w-1" :class="visual.accentClass" aria-hidden="true" />
    <div
      v-if="(timeout ?? 0) > 0"
      class="absolute bottom-0 left-0 h-0.5 origin-left"
      :class="visual.accentClass"
      :style="{ animation: `toast-shrink ${timeout ?? 0}ms linear forwards` }"
      aria-hidden="true"
    />

    <!-- Icon chip -->
    <div
      class="flex items-center justify-center h-9 w-9 shrink-0 rounded-card"
      :class="visual.chipClass"
    >
      <component :is="visual.icon" class="h-5 w-5" :class="visual.iconClass" />
    </div>

    <p class="flex-1 text-sm font-medium text-content break-words">
      {{ message }}
    </p>

    <button
      type="button"
      class="shrink-0 p-1.5 rounded-card text-content-subtle hover:text-content hover:bg-surface-muted transition-colors"
      aria-label="Dismiss notification"
      @click="emit('dismiss')"
    >
      <X class="h-4 w-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from '@lucide/vue'
import { getToastVisual } from '@/utils/toastIcons'
import type { ToastType } from '@/stores/toast'

interface Props {
  message: string
  type?: ToastType | string
  timeout?: number
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  timeout: 4000,
})

const emit = defineEmits<{ (e: 'dismiss'): void }>()

const visual = computed(() => getToastVisual(props.type))
</script>
