<template>
  <ErrorBanner v-if="failures && Object.keys(failures).length" class="rounded-modal p-5 mb-6">
    <div class="flex items-center gap-2 mb-2">
      <span class="font-semibold text-red-700 dark:text-red-300"
        >{{ failureCount }} document error{{ failureCount === 1 ? '' : 's' }}</span
      >
    </div>
    <details class="mt-1" open>
      <summary class="text-sm text-red-700 dark:text-red-300 cursor-pointer">
        View error details
      </summary>
      <ul class="list-disc list-inside mt-2 text-sm text-red-800 dark:text-red-200">
        <li v-for="(err, docId) in failures" :key="docId">
          <button
            v-if="isDocumentEntry(docId)"
            type="button"
            class="font-semibold underline decoration-dotted underline-offset-2 hover:decoration-solid"
            title="Show this document in the viewer"
            @click="$emit('select', Number(docId))"
          >
            {{ displayName(docId) }}
          </button>
          <span v-else class="font-semibold">{{ displayName(docId) }}</span
          >: {{ err }}
        </li>
      </ul>
    </details>
  </ErrorBanner>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

interface Props {
  /** trial.meta.failures — document id (as string) → error message. May also
   *  contain non-document keys like "_dispatch" for trial-level errors. */
  failures?: Record<string, string>
  /** document id (as string) → resolved document name, provided by the parent
   *  from the results it already has loaded. */
  documentNames?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  failures: () => ({}),
  documentNames: () => ({}),
})

defineEmits<{
  /** Clicked a document entry — the parent selects the matching result. */
  select: [documentId: number]
}>()

const failureCount = computed(() => Object.keys(props.failures).length)

// Keys like "_dispatch" hold trial-level errors, not per-document ones.
const isDocumentEntry = (docId: string | number): boolean => /^\d+$/.test(String(docId))

const displayName = (docId: string | number): string => {
  const key = String(docId)
  if (!isDocumentEntry(key)) return 'Trial'
  return props.documentNames[key] || `Doc ${key}`
}
</script>
