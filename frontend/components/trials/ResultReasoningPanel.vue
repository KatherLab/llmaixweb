<template>
  <div
    v-if="reasoningContent || additionalContent?.usage || additionalContent?.finish_reason"
    class="mt-6"
  >
    <BaseButton variant="secondary" size="sm" class="shadow-sm" @click="$emit('toggle')">
      <ChevronRight
        :class="show ? 'rotate-90' : ''"
        class="h-4 w-4 transition-transform duration-200"
      />
      <span>{{ show ? 'Hide' : 'Show' }} LLM Reasoning & Metadata</span>
      <span
        v-if="!show"
        class="ml-1 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
      >
        {{ hiddenCount }}
      </span>
    </BaseButton>
    <div
      v-if="show"
      class="bg-blue-50/60 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-card mt-3 p-5"
    >
      <div v-if="reasoningContent" class="mb-4">
        <h5 class="font-semibold text-blue-800 dark:text-blue-300 mb-2">Reasoning</h5>
        <div class="markdown-content" v-html="renderMarkdown(reasoningContent)"></div>
      </div>
      <div v-if="additionalContent?.usage" class="mb-2">
        <h5 class="font-semibold text-blue-800 dark:text-blue-300 mb-1">Token Usage</h5>
        <ul class="text-xs text-blue-900 dark:text-blue-200 ml-2">
          <li v-for="(v, k) in additionalContent.usage" :key="k">
            <span class="font-medium">{{ k.replace(/_/g, ' ') }}:</span> {{ v }}
          </li>
        </ul>
      </div>
      <div v-if="additionalContent?.finish_reason">
        <h5 class="font-semibold text-blue-800 dark:text-blue-300 mb-1">Finish Reason</h5>
        <span class="text-xs text-blue-900 dark:text-blue-200">{{
          additionalContent.finish_reason
        }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { ChevronRight } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { renderMarkdown } from '@/utils/markdown'

interface AdditionalContent {
  reasoning_content?: string
  usage?: Record<string, unknown>
  finish_reason?: string
  [key: string]: unknown
}

const props = defineProps({
  reasoningContent: {
    type: [String, null] as PropType<string | null>,
    default: '',
  },
  additionalContent: {
    type: Object as PropType<AdditionalContent | null>,
    default: null,
  },
  show: {
    type: Boolean,
    default: false,
  },
})

defineEmits<{ toggle: [] }>()

// Count of hidden metadata sections, surfaced as a badge on the collapsed
// toggle so users know there's content worth expanding.
const hiddenCount = computed(() => {
  let n = 0
  if (props.reasoningContent) n++
  if (props.additionalContent?.usage) n++
  if (props.additionalContent?.finish_reason) n++
  return n
})
</script>
