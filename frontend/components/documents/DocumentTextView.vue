<template>
  <div class="p-6">
    <div
      v-if="textLoading"
      class="flex items-center justify-center py-12 text-slate-400 dark:text-slate-500"
    >
      <span class="mr-2"><LoadingSpinner size="small" color="current" inline label="" /></span>
      <span>Loading text…</span>
    </div>
    <div
      v-else
      class="markdown-content max-w-none bg-slate-50 dark:bg-slate-800 p-4 rounded-lg"
      v-html="safeMarkdown"
    />
  </div>
</template>

<script setup>
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineProps({
  textLoading: { type: Boolean, default: false },
  safeMarkdown: { type: String, default: '' },
})
</script>
