<template>
  <div class="bg-white shadow border border-slate-100 rounded-xl transition-shadow hover:shadow-lg">
    <!-- Row header -->
    <div
      class="cursor-pointer flex items-center justify-between px-6 py-4 border-b hover:bg-slate-50/70 transition-colors rounded-t-xl select-none"
      @click="$emit('toggle-expansion')"
    >
      <div class="flex flex-col gap-0.5">
        <div class="flex items-center flex-wrap gap-2">
          <StatusBadge color="blue" class="w-7 h-7 justify-center text-base font-bold">{{
            index + 1
          }}</StatusBadge>
          <span class="font-medium text-slate-800">{{
            label?.name || 'Loading document name...'
          }}</span>

          <!-- Status pills -->
          <span
            v-if="res.result"
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
              getPillClass('green'),
            ]"
            >OK</span
          >
          <span
            v-else
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
              getPillClass('red'),
            ]"
            >Error</span
          >

          <span
            v-if="
              res.additional_content?.finish_reason &&
              res.additional_content.finish_reason !== 'stop'
            "
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
              getPillClass('yellow'),
            ]"
          >
            {{ res.additional_content.finish_reason }}
          </span>
          <span
            v-if="res.additional_content?.truncation_analysis?.likely_truncated"
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
              getPillClass('orange'),
            ]"
          >
            Truncated
          </span>
        </div>
        <span
          v-if="label?.original && label?.original !== label?.name"
          class="text-xs text-slate-400 italic ml-10 truncate max-w-xs"
          >(Original: {{ label.original }})</span
        >
      </div>
      <ChevronDown
        class="w-5 h-5 text-slate-400 transition-transform duration-200"
        :class="{ 'rotate-180': expanded }"
      />
    </div>

    <!-- Row body -->
    <div v-if="expanded" class="p-6 bg-gradient-to-b from-white to-blue-50/20">
      <!-- Inline error panel -->
      <ErrorBanner
        v-if="!res.result || res.additional_content?.json_error"
        class="mb-4 rounded-lg text-sm"
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
      </ErrorBanner>

      <div
        class="flex gap-6"
        :class="viewMode === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
      >
        <div
          class="bg-slate-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100"
        >
          <h4 class="text-sm font-semibold mb-3 text-slate-700 flex items-center gap-1.5">
            <FileText class="h-4 w-4" />
            Document Content
          </h4>
          <div
            v-if="isMarkdown(documentContent)"
            class="markdown-content"
            v-html="renderMarkdown(documentContent)"
          ></div>
          <pre v-else class="text-xs text-slate-800 whitespace-pre-wrap">{{ documentContent }}</pre>
        </div>

        <div
          class="bg-slate-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100"
        >
          <h4 class="text-sm font-semibold mb-3 text-slate-700 flex items-center gap-1.5">
            <FileJson class="h-4 w-4" />
            Extracted Information
          </h4>
          <template v-if="res.result">
            <JsonViewer :data="res.result" />
          </template>
          <template v-else>
            <div class="text-xs text-slate-500 italic">No structured output for this document.</div>
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
          <AlignLeft class="h-4 w-4" />
          {{ viewMode === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
        </BaseButton>
        <button
          v-if="documentMeta?.previewable"
          class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
          @click="$emit('toggle-document-panel')"
        >
          <EyeOff v-if="showDocumentPanel" class="h-4 w-4" />
          <Eye v-else class="h-4 w-4" />
          {{ showDocumentPanel ? 'Hide Original Document' : 'View Original Document' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { AlignLeft, ChevronDown, Eye, EyeOff, FileJson, FileText } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { getPillClass } from '@/utils/statusStyles'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
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
