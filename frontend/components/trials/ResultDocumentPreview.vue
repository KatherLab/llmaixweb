<template>
  <div
    class="bg-slate-50 dark:bg-slate-800/40 p-5 rounded-modal overflow-auto flex-1 max-h-[480px] border border-slate-100 dark:border-slate-700"
  >
    <h4
      class="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200 flex items-center gap-1.5"
    >
      <FileText class="h-4 w-4" />
      Original Document
    </h4>
    <iframe
      v-if="pdfUrl"
      :src="pdfUrl"
      frameborder="0"
      class="rounded-card w-full h-[400px]"
    ></iframe>
    <div v-else-if="pdfLoading" class="text-center py-10">
      <LoadingSpinner size="medium" />
      <span class="mt-2 text-slate-500 dark:text-slate-400 block">Loading preview…</span>
    </div>
    <span v-else class="text-slate-500 dark:text-slate-400">Failed to load preview</span>
  </div>
</template>

<script setup lang="ts">
import { FileText } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineProps<{
  pdfUrl?: string
  pdfLoading?: boolean
}>()
</script>
