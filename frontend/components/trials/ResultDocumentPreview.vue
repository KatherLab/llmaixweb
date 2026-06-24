<template>
  <div class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100">
    <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
        />
      </svg>
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
      <span class="mt-2 text-gray-500 block">Loading preview…</span>
    </div>
    <span v-else class="text-gray-500">Failed to load preview</span>
  </div>
</template>

<script setup>
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
