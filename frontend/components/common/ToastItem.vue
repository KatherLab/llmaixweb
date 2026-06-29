<template>
  <div
    :role="type === 'error' ? 'alert' : 'status'"
    :aria-live="type === 'error' ? 'assertive' : 'polite'"
    class="relative flex items-center gap-3 w-80 max-w-[calc(100vw-2rem)] py-2.5 pl-3 pr-2 rounded-xl border border-slate-200/80 bg-white/80 backdrop-blur-md shadow-lg shadow-slate-900/5 dark:border-slate-700/80 dark:bg-slate-800/80 overflow-hidden"
  >
    <!-- Colored accent + progress bar at the bottom edge. -->
    <div class="absolute inset-y-0 left-0 w-1" :class="visual.accentClass" aria-hidden="true" />
    <div
      v-if="timeout > 0"
      class="absolute bottom-0 left-0 h-0.5 origin-left"
      :class="visual.accentClass"
      :style="{ animation: `toast-shrink ${timeout}ms linear forwards` }"
      aria-hidden="true"
    />

    <!-- Icon chip -->
    <div
      class="flex items-center justify-center h-9 w-9 shrink-0 rounded-lg"
      :class="visual.chipClass"
    >
      <component :is="visual.icon" class="h-5 w-5" :class="visual.iconClass" />
    </div>

    <p class="flex-1 text-sm font-medium text-slate-700 dark:text-slate-100 break-words">
      {{ message }}
    </p>

    <button
      type="button"
      class="shrink-0 p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 dark:hover:text-slate-200 dark:hover:bg-slate-700/60 transition-colors"
      aria-label="Dismiss notification"
      @click="emit('dismiss')"
    >
      <X class="h-4 w-4" />
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { X } from '@lucide/vue'
import { getToastVisual } from '@/utils/toastIcons'

const props = defineProps({
  message: {
    type: String,
    required: true,
  },
  type: {
    type: String,
    default: 'info',
  },
  timeout: {
    type: Number,
    default: 4000,
  },
})

const emit = defineEmits(['dismiss'])

const visual = computed(() => getToastVisual(props.type))
</script>
