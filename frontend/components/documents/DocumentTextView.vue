<template>
  <div class="p-6">
    <div v-if="textLoading" class="flex items-center justify-center py-12 text-content-subtle">
      <span class="mr-2"><LoadingSpinner size="small" color="current" inline label="" /></span>
      <span>Loading text…</span>
    </div>
    <div
      v-else
      class="markdown-content max-w-none bg-surface-muted p-4 rounded-card"
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
