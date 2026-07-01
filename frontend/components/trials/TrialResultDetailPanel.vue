<template>
  <div class="p-5 bg-gradient-to-b from-white to-blue-50/20 dark:from-slate-900 dark:to-slate-900">
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
        <summary class="cursor-pointer text-slate-700 dark:text-slate-300">Tuning advice</summary>
        <ul class="list-disc list-inside mt-1 text-slate-700 dark:text-slate-300">
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
        class="bg-slate-50 dark:bg-slate-800/40 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100 dark:border-slate-700"
      >
        <h4
          class="text-sm font-semibold mb-3 text-slate-700 dark:text-slate-200 flex items-center gap-1.5"
        >
          <FileText class="h-4 w-4" />
          Document Content
        </h4>
        <div v-if="docLoading" class="text-xs text-slate-400 dark:text-slate-500">
          Loading document text…
        </div>
        <template v-else-if="documentContent">
          <div
            v-if="isMarkdown(documentContent)"
            class="markdown-content"
            v-html="renderMarkdown(documentContent)"
          ></div>
          <pre v-else class="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{{
            documentContent
          }}</pre>
        </template>
        <div v-else class="text-xs text-slate-500 dark:text-slate-400 italic">
          No text content available.
        </div>
      </div>

      <!-- Extracted Information -->
      <div
        class="bg-slate-50 dark:bg-slate-800/40 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-slate-100 dark:border-slate-700"
      >
        <div class="flex items-center justify-between mb-3">
          <h4
            class="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5"
          >
            <FileJson class="h-4 w-4" />
            Extracted Information
          </h4>
          <BaseButton
            v-if="result.result"
            variant="ghost"
            size="sm"
            class="-mr-2"
            :title="copied ? 'Copied!' : 'Copy JSON'"
            @click="copyResult"
          >
            <component :is="copied ? Check : Copy" class="h-4 w-4" />
          </BaseButton>
        </div>
        <template v-if="result.result">
          <JsonViewer :data="result.result" />
        </template>
        <template v-else>
          <div class="text-xs text-slate-500 dark:text-slate-400 italic">
            No structured output for this document.
          </div>
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
      <BaseButton
        v-if="documentPreviewable"
        variant="secondary"
        size="sm"
        class="shadow-sm"
        @click="toggleDocumentPanel"
      >
        <EyeOff v-if="showDocumentPanel" class="h-4 w-4" />
        <Eye v-else class="h-4 w-4" />
        {{ showDocumentPanel ? 'Hide Original Document' : 'View Original Document' }}
      </BaseButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type PropType } from 'vue'
import { AlignLeft, Check, Copy, Eye, EyeOff, FileJson, FileText } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import ResultDocumentPreview from './ResultDocumentPreview.vue'
import ResultReasoningPanel from './ResultReasoningPanel.vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { renderMarkdown, isMarkdown } from '@/utils/markdown'
import type { TrialResultItem } from '@/types'

interface AdditionalContent {
  reasoning_content?: string
  usage?: Record<string, unknown>
  finish_reason?: string
  json_error?: string
  user_guidance?: { user_message?: string }
  tuning_advice?: {
    recommendations: Array<{
      action: string
      suggested_value?: string
      rationale?: string
    }>
  }
  [key: string]: unknown
}

const props = defineProps({
  result: { type: Object as PropType<TrialResultItem>, required: true },
  projectId: { type: [String, Number] as PropType<string | number>, required: true },
})

const toast = useToast()

const documentContent = ref('')
const docLoading = ref(false)
const viewMode = ref<'horizontal' | 'vertical'>('horizontal')
const showDocumentPanel = ref(false)
const documentPdfUrl = ref('')
const documentPdfLoading = ref(false)
const showReasoningPanel = ref(false)
const documentPreviewable = ref(false)
const documentFileId = ref<number | null>(null)
const copied = ref(false)

async function copyResult(): Promise<void> {
  if (!props.result.result) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(props.result.result, null, 2))
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    toast.error('Failed to copy')
  }
}

const additionalContent = computed<AdditionalContent | null>(() => {
  const ac = props.result.additional_content
  if (!ac) return null
  if (typeof ac === 'string') {
    try {
      return JSON.parse(ac) as AdditionalContent
    } catch {
      return null
    }
  }
  return ac as AdditionalContent
})

const reasoningContent = computed(() => additionalContent.value?.reasoning_content || null)

const analyzeOriginalFile = (fileType: string | undefined | null): boolean => {
  if (!fileType) return false
  return fileType === 'application/pdf' || fileType.startsWith('image/')
}

async function loadDocumentTextAndMeta(): Promise<void> {
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

function toggleViewMode(): void {
  viewMode.value = viewMode.value === 'vertical' ? 'horizontal' : 'vertical'
}

async function toggleDocumentPanel(): Promise<void> {
  showDocumentPanel.value = !showDocumentPanel.value
  if (!showDocumentPanel.value) return
  if (documentPdfUrl.value || documentPdfLoading.value) return
  if (!documentPreviewable.value || !documentFileId.value) return
  documentPdfLoading.value = true
  try {
    const fr = await filesApi.getContent(props.projectId, documentFileId.value, { preview: true })
    const blob = new Blob([fr.data], {
      type: (fr.headers['content-type'] as string) || undefined,
    })
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
