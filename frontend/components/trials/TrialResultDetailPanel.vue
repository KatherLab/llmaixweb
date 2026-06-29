<template>
  <div class="p-5 bg-gradient-to-b from-white to-blue-50/20">
    <!-- Inline error panel -->
    <ErrorBanner
      v-if="!result.result || additionalContent?.json_error"
      class="mb-4 rounded-lg text-sm"
    >
      <div class="font-semibold mb-1">This document has no structured result.</div>
      <div v-if="additionalContent?.user_guidance?.user_message" class="mb-1">
        {{ additionalContent.user_guidance.user_message }}
      </div>
      <div v-else-if="additionalContent?.json_error" class="mb-1">
        Parser error: {{ additionalContent.json_error }}
      </div>
      <details v-if="additionalContent?.tuning_advice" class="mt-2">
        <summary class="cursor-pointer">Tuning advice</summary>
        <ul class="list-disc list-inside mt-1">
          <li v-for="(rec, i) in additionalContent.tuning_advice.recommendations" :key="i">
            <span class="font-medium">{{ rec.action }}</span>
            <span v-if="rec.suggested_value">
              → <code>{{ rec.suggested_value }}</code></span
            >
            <span v-if="rec.rationale"> — {{ rec.rationale }}</span>
          </li>
        </ul>
      </details>
    </ErrorBanner>

    <div class="flex gap-6" :class="viewMode === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'">
      <!-- Document Content -->
      <div
        class="bg-slate-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100"
      >
        <h4 class="text-sm font-semibold mb-3 text-slate-700 flex items-center gap-1.5">
          <FileText class="h-4 w-4" />
          Document Content
        </h4>
        <div v-if="docLoading" class="text-xs text-slate-400">Loading document text…</div>
        <template v-else-if="documentContent">
          <div
            v-if="isMarkdown(documentContent)"
            class="markdown-content"
            v-html="renderMarkdown(documentContent)"
          ></div>
          <pre v-else class="text-xs text-slate-800 whitespace-pre-wrap">{{ documentContent }}</pre>
        </template>
        <div v-else class="text-xs text-slate-500 italic">No text content available.</div>
      </div>

      <!-- Extracted Information -->
      <div
        class="bg-slate-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100"
      >
        <h4 class="text-sm font-semibold mb-3 text-slate-700 flex items-center gap-1.5">
          <FileJson class="h-4 w-4" />
          Extracted Information
        </h4>
        <template v-if="result.result">
          <JsonViewer :data="result.result" />
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
      @toggle="showReasoningPanel = !showReasoningPanel"
    />

    <!-- Row actions -->
    <div class="mt-6 flex flex-wrap gap-3 justify-end">
      <BaseButton variant="secondary" size="sm" class="shadow-sm" @click="toggleViewMode">
        <AlignLeft class="h-4 w-4" />
        {{ viewMode === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
      </BaseButton>
      <button
        v-if="documentPreviewable"
        class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
        @click="toggleDocumentPanel"
      >
        <EyeOff v-if="showDocumentPanel" class="h-4 w-4" />
        <Eye v-else class="h-4 w-4" />
        {{ showDocumentPanel ? 'Hide Original Document' : 'View Original Document' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { AlignLeft, Eye, EyeOff, FileJson, FileText } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import ResultDocumentPreview from './ResultDocumentPreview.vue'
import ResultReasoningPanel from './ResultReasoningPanel.vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from 'vue-toastification'
import { renderMarkdown, isMarkdown } from '@/utils/markdown.js'

const props = defineProps({
  result: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
})

const toast = useToast()

const documentContent = ref('')
const docLoading = ref(false)
const viewMode = ref('horizontal')
const showDocumentPanel = ref(false)
const documentPdfUrl = ref('')
const documentPdfLoading = ref(false)
const showReasoningPanel = ref(false)
const documentPreviewable = ref(false)
const documentFileId = ref(null)

const additionalContent = computed(() => {
  const ac = props.result.additional_content
  if (!ac) return null
  if (typeof ac === 'string') {
    try {
      return JSON.parse(ac)
    } catch {
      return null
    }
  }
  return ac
})

const reasoningContent = computed(() => additionalContent.value?.reasoning_content || null)

const analyzeOriginalFile = (fileType) => {
  if (!fileType) return false
  return fileType === 'application/pdf' || fileType.startsWith('image/')
}

async function loadDocumentTextAndMeta() {
  const docId = props.result.document_id
  if (!docId) return
  docLoading.value = true
  try {
    const r = await documentsApi.get(props.projectId, docId)
    const d = r.data
    documentContent.value = d.text || 'No text content available'
    const previewable = analyzeOriginalFile(d.original_file?.file_type)
    documentPreviewable.value = previewable
    documentFileId.value = previewable
      ? d.preprocessed_file_id && d.preprocessed_file?.file_type === 'application/pdf'
        ? d.preprocessed_file_id
        : d.original_file_id
      : null
  } catch (err) {
    documentContent.value = 'Error loading document content'
    console.error(err)
  } finally {
    docLoading.value = false
  }
}

function toggleViewMode() {
  viewMode.value = viewMode.value === 'vertical' ? 'horizontal' : 'vertical'
}

async function toggleDocumentPanel() {
  showDocumentPanel.value = !showDocumentPanel.value
  if (!showDocumentPanel.value) return
  if (documentPdfUrl.value || documentPdfLoading.value) return
  if (!documentPreviewable.value || !documentFileId.value) return
  documentPdfLoading.value = true
  try {
    const fr = await filesApi.getContent(props.projectId, documentFileId.value, { preview: true })
    const blob = new Blob([fr.data], { type: fr.headers['content-type'] })
    documentPdfUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    console.error(err)
    toast.error('Failed to load document')
  } finally {
    documentPdfLoading.value = false
  }
}

onMounted(() => {
  loadDocumentTextAndMeta()
})

onUnmounted(() => {
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
})
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
