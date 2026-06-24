<template>
  <div class="bg-white shadow border border-gray-100 rounded-xl transition-shadow hover:shadow-lg">
    <!-- Row header -->
    <div
      class="cursor-pointer flex items-center justify-between px-6 py-4 border-b hover:bg-gray-50/70 transition-colors rounded-t-xl select-none"
      @click="$emit('toggle-expansion')"
    >
      <div class="flex flex-col gap-0.5">
        <div class="flex items-center flex-wrap gap-2">
          <StatusBadge color="blue" class="w-7 h-7 justify-center text-base font-bold">{{
            index + 1
          }}</StatusBadge>
          <span class="font-medium text-gray-800">{{
            label?.name || 'Loading document name...'
          }}</span>

          <!-- Status pills -->
          <span
            v-if="res.result"
            class="text-[10px] uppercase tracking-wide bg-green-100 text-green-700 px-2 py-0.5 rounded"
            >OK</span
          >
          <span
            v-else
            class="text-[10px] uppercase tracking-wide bg-red-100 text-red-700 px-2 py-0.5 rounded"
            >Error</span
          >

          <span
            v-if="
              res.additional_content?.finish_reason &&
              res.additional_content.finish_reason !== 'stop'
            "
            class="text-[10px] uppercase tracking-wide bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded"
          >
            {{ res.additional_content.finish_reason }}
          </span>
          <span
            v-if="res.additional_content?.truncation_analysis?.likely_truncated"
            class="text-[10px] uppercase tracking-wide bg-orange-100 text-orange-800 px-2 py-0.5 rounded"
          >
            Truncated
          </span>
        </div>
        <span
          v-if="label?.original && label?.original !== label?.name"
          class="text-xs text-gray-400 italic ml-10 truncate max-w-xs"
          >(Original: {{ label.original }})</span
        >
      </div>
      <svg
        class="w-5 h-5 text-gray-400 transition-transform duration-200"
        :class="{ 'rotate-180': expanded }"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
          clip-rule="evenodd"
        />
      </svg>
    </div>

    <!-- Row body -->
    <div v-if="expanded" class="p-6 bg-gradient-to-b from-white to-blue-50/20">
      <!-- Inline error panel -->
      <div
        v-if="!res.result || res.additional_content?.json_error"
        class="mb-4 bg-red-50 border border-red-200 text-red-800 text-sm rounded-lg p-4"
      >
        <div class="font-semibold mb-1">This document has no structured result.</div>
        <div v-if="res.additional_content?.user_guidance?.user_message" class="mb-1">
          {{ res.additional_content.user_guidance.user_message }}
        </div>
        <div v-else-if="res.additional_content?.json_error" class="mb-1">
          Parser error: {{ res.additional_content.json_error }}
        </div>
        <details v-if="res.additional_content?.tuning_advice" class="mt-2">
          <summary class="cursor-pointer">Tuning advice</summary>
          <ul class="list-disc list-inside mt-1">
            <li v-for="(rec, i) in res.additional_content.tuning_advice.recommendations" :key="i">
              <span class="font-medium">{{ rec.action }}</span>
              <span v-if="rec.suggested_value">
                → <code>{{ rec.suggested_value }}</code></span
              >
              <span v-if="rec.rationale"> — {{ rec.rationale }}</span>
            </li>
          </ul>
        </details>
      </div>

      <div
        class="flex gap-6"
        :class="viewMode === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
      >
        <div
          class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100"
        >
          <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Document Content
          </h4>
          <div
            v-if="isMarkdown(documentContent)"
            class="markdown-content"
            v-html="renderMarkdown(documentContent)"
          ></div>
          <pre v-else class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContent }}</pre>
        </div>

        <div
          class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100"
        >
          <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
            Extracted Information
          </h4>
          <template v-if="res.result">
            <JsonViewer :data="res.result" />
          </template>
          <template v-else>
            <div class="text-xs text-gray-500 italic">No structured output for this document.</div>
          </template>
        </div>

        <ResultDocumentPreview
          v-if="showDocumentPanel"
          :pdf-url="documentPdfUrl"
          :pdf-loading="documentPdfLoading"
        />
      </div>

      <!-- Reasoning & Metadata -->
      <ResultReasoningPanel
        :reasoning-content="reasoningContent"
        :additional-content="additionalContent"
        :show="showReasoningPanel"
        @toggle="$emit('toggle-reasoning')"
      />

      <!-- Row actions -->
      <div class="mt-6 flex flex-wrap gap-3 justify-end">
        <BaseButton
          variant="secondary"
          size="sm"
          class="shadow-sm"
          @click="$emit('toggle-view-mode')"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 6h16M4 12h16m-7 6h7"
            />
          </svg>
          {{ viewMode === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
        </BaseButton>
        <button
          v-if="documentMeta?.previewable"
          class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
          @click="$emit('toggle-document-panel')"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              v-if="showDocumentPanel"
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268-2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
            />
            <path v-else d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268-2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
          {{ showDocumentPanel ? 'Hide Original Document' : 'View Original Document' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import JsonViewer from '@/components/common/JsonViewer.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ResultDocumentPreview from './ResultDocumentPreview.vue'
import ResultReasoningPanel from './ResultReasoningPanel.vue'
import { renderMarkdown, isMarkdown } from '@/utils/markdown.js'

defineProps({
  res: {
    type: Object,
    required: true,
  },
  index: {
    type: Number,
    required: true,
  },
  label: {
    type: Object,
    default: null,
  },
  expanded: {
    type: Boolean,
    default: false,
  },
  documentContent: {
    type: String,
    default: '',
  },
  viewMode: {
    type: String,
    default: 'horizontal',
  },
  documentPdfUrl: {
    type: String,
    default: '',
  },
  documentPdfLoading: {
    type: Boolean,
    default: false,
  },
  showDocumentPanel: {
    type: Boolean,
    default: false,
  },
  documentMeta: {
    type: Object,
    default: null,
  },
  showReasoningPanel: {
    type: Boolean,
    default: false,
  },
  reasoningContent: {
    type: String,
    default: '',
  },
  additionalContent: {
    type: Object,
    default: null,
  },
})

defineEmits(['toggle-expansion', 'toggle-view-mode', 'toggle-document-panel', 'toggle-reasoning'])
</script>

<style>
/* Global (non-scoped) so it applies to v-html markdown content rendered here
 * and in the child ResultReasoningPanel. */
.markdown-content {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #333;
}
.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
}
.markdown-content h1 {
  font-size: 1.5em;
}
.markdown-content h2 {
  font-size: 1.25em;
}
.markdown-content h3 {
  font-size: 1.125em;
}
.markdown-content p {
  margin-bottom: 1em;
}
.markdown-content ul,
.markdown-content ol {
  margin-bottom: 1em;
  padding-left: 1.5em;
}
.markdown-content li {
  margin-bottom: 0.25em;
}
.markdown-content code {
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 85%;
  font-family: SFMono-Regular, Consolas, Menlo, monospace;
}
.markdown-content pre {
  background-color: #f6f8fa;
  border-radius: 3px;
  padding: 1em;
  overflow: auto;
  margin-bottom: 1em;
}
.markdown-content pre code {
  background-color: transparent;
  padding: 0;
}
.markdown-content a {
  color: #0366d6;
  text-decoration: none;
}
.markdown-content a:hover {
  text-decoration: underline;
}
</style>
