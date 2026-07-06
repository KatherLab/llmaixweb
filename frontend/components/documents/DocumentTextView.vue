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
      class="markdown-content max-w-none bg-slate-50 dark:bg-slate-800 p-4 rounded-card"
      v-html="safeMarkdown"
    />
  </div>
</template>

<script setup lang="ts">
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

interface Props {
  textLoading?: boolean
  safeMarkdown?: string
}

withDefaults(defineProps<Props>(), {
  textLoading: false,
  safeMarkdown: '',
})
</script>
