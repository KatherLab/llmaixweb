<template>
  <div
    v-if="reasoningContent || additionalContent?.usage || additionalContent?.finish_reason"
    class="mt-6"
  >
    <button
      class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
      @click="$emit('toggle')"
    >
      <svg
        :class="show ? 'rotate-90' : ''"
        class="h-4 w-4 transition-transform duration-200"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
      <span>{{ show ? 'Hide' : 'Show' }} LLM Reasoning & Metadata</span>
    </button>
    <div v-if="show" class="bg-blue-50/60 border border-blue-100 rounded-lg mt-3 p-5">
      <div v-if="reasoningContent" class="mb-4">
        <h5 class="font-semibold text-blue-800 mb-2">Reasoning</h5>
        <div class="markdown-content" v-html="renderMarkdown(reasoningContent)"></div>
      </div>
      <div v-if="additionalContent?.usage" class="mb-2">
        <h5 class="font-semibold text-blue-800 mb-1">Token Usage</h5>
        <ul class="text-xs text-blue-900 ml-2">
          <li v-for="(v, k) in additionalContent.usage" :key="k">
            <span class="font-medium">{{ k.replace(/_/g, ' ') }}:</span> {{ v }}
          </li>
        </ul>
      </div>
      <div v-if="additionalContent?.finish_reason">
        <h5 class="font-semibold text-blue-800 mb-1">Finish Reason</h5>
        <span class="text-xs text-blue-900">{{ additionalContent.finish_reason }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { renderMarkdown } from '@/utils/markdown.js'

defineProps({
  reasoningContent: {
    type: String,
    default: '',
  },
  additionalContent: {
    type: Object,
    default: null,
  },
  show: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['toggle'])
</script>
