<template>
  <div
    class="bg-slate-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100"
  >
    <h4 class="text-sm font-semibold mb-3 text-slate-700 flex items-center gap-1.5">
      <Download class="h-4 w-4" />
      Original Document
    </h4>
    <iframe
      v-if="pdfUrl"
      :src="pdfUrl"
      frameborder="0"
      width="100%"
      height="400px"
      class="rounded-md"
    ></iframe>
    <div v-else-if="pdfLoading" class="text-center py-10">
      <LoadingSpinner size="medium" />
      <span class="mt-2 text-slate-500 block">Loading preview…</span>
    </div>
    <span v-else class="text-slate-500">Failed to load preview</span>
  </div>
</template>

<script setup>
import { Download } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineProps({
  pdfUrl: {
    type: String,
    default: '',
  },
  pdfLoading: {
    type: Boolean,
    default: false,
  },
})
</script>
