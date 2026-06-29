<script setup>
import { AlertTriangle, X } from '@lucide/vue'
/**
 * Shared error banner: icon + message + optional retry/dismiss actions.
 *
 * Props:
 *  - message      : the error text (also used as fallback if a default slot is given)
 *  - dismissable  : show a dismiss (×) button
 *  - retryText    : show a retry button with this label (empty = hidden)
 *  - retryLoading : disables the retry button and shows "Retrying..."
 *
 * Slots:
 *  - default : rich message content (overrides the `message` prop text)
 */
defineProps({
  message: {
    type: String,
    default: '',
  },
  dismissable: {
    type: Boolean,
    default: false,
  },
  retryText: {
    type: String,
    default: '',
  },
  retryLoading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['dismiss', 'retry'])
</script>

<template>
  <div
    role="alert"
    class="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 dark:border-red-400 p-4 mb-6"
  >
    <div class="flex items-start">
      <div class="flex-shrink-0">
        <AlertTriangle class="h-5 w-5 text-red-400 dark:text-red-300" aria-hidden="true" />
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm text-red-700 dark:text-red-200">
          <slot>{{ message }}</slot>
        </p>
      </div>
      <div v-if="dismissable || retryText" class="ml-auto pl-3 flex items-center gap-3">
        <button
          v-if="retryText"
          type="button"
          class="text-sm font-medium text-red-700 hover:text-red-800 dark:text-red-300 dark:hover:text-red-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 rounded"
          :disabled="retryLoading"
          @click="emit('retry')"
        >
          {{ retryLoading ? 'Retrying...' : retryText }}
        </button>
        <button
          v-if="dismissable"
          type="button"
          class="inline-flex text-red-400 hover:text-red-500 dark:text-red-300 dark:hover:text-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 rounded"
          aria-label="Dismiss error"
          @click="emit('dismiss')"
        >
          <X class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>
</template>
