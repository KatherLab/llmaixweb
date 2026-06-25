<template>
  <ErrorBanner v-if="failures && Object.keys(failures).length" class="rounded-xl p-5 mb-6">
    <div class="flex items-center gap-2 mb-2">
      <span class="font-semibold text-red-700 dark:text-red-300"
        >{{ failureCount }} document error{{ failureCount === 1 ? '' : 's' }}</span
      >
    </div>
    <details class="mt-1">
      <summary class="text-sm text-red-700 dark:text-red-300 cursor-pointer">
        View error details
      </summary>
      <ul class="list-disc list-inside mt-2 text-sm text-red-800 dark:text-red-200">
        <li v-for="(err, docId) in failures" :key="docId">
          <span class="font-semibold">Doc {{ docId }}:</span> {{ err }}
        </li>
      </ul>
    </details>
  </ErrorBanner>
</template>

<script setup>
import { computed } from 'vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

const props = defineProps({
  failures: {
    type: Object,
    default: () => ({}),
  },
})

const failureCount = computed(() => Object.keys(props.failures).length)
</script>
