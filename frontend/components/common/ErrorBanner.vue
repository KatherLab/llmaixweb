<script setup>
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
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 text-red-400 dark:text-red-300"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
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
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
