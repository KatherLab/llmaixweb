<template>
  <div class="flex flex-col h-full min-h-0 bg-surface">
    <!-- Document header bar -->
    <div
      class="flex items-center justify-between gap-3 px-5 py-3 border-b border-default bg-surface-muted/60"
    >
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <h3 class="text-sm font-semibold text-content truncate">
            {{ documentLabel }}
          </h3>
          <span
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded shrink-0',
              statusPillClass(activeResult.status as string),
            ]"
          >
            {{ statusLabel(activeResult.status as string) }}
          </span>
          <span
            v-if="additionalContent?.finish_reason && additionalContent.finish_reason !== 'stop'"
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded shrink-0',
              getPillClass('yellow'),
            ]"
          >
            {{ additionalContent.finish_reason }}
          </span>
        </div>
        <div class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-content-subtle mt-1">
          <span v-if="tokenUsage !== '—'">
            <span class="font-medium text-content-muted">Tokens:</span> {{ tokenUsage }}
          </span>
          <span>
            <span class="font-medium text-content-muted">Created:</span>
            {{ formatDateSmart(activeResult.created_at) }}
          </span>
          <span v-if="activeResult.original_file_name" class="truncate max-w-[24rem]">
            <span class="font-medium text-content-muted">File:</span>
            {{ activeResult.original_file_name }}
          </span>
        </div>
      </div>

      <!-- Inline prev/next (mirrors the pinned footer control) -->
      <div class="flex items-center gap-1 shrink-0">
        <BaseButton
          variant="secondary"
          size="sm"
          :disabled="!hasPrev"
          :title="hasPrev ? 'Previous document (←)' : 'First result'"
          @click="$emit('prev')"
        >
          <ChevronLeft class="h-4 w-4" />
        </BaseButton>
        <span class="text-xs font-medium text-content-muted tabular-nums px-1">
          {{ index + 1 }} / {{ total }}
        </span>
        <BaseButton
          variant="secondary"
          size="sm"
          :disabled="!hasNext"
          :title="hasNext ? 'Next document (→)' : 'Last result'"
          @click="$emit('next')"
        >
          <ChevronRight class="h-4 w-4" />
        </BaseButton>
      </div>
    </div>

    <!-- Error banner (replaces the JSON tab content for failed docs) -->
    <div v-if="!activeResult.result || additionalContent?.json_error" class="px-5 pt-4">
      <ErrorBanner class="rounded-card text-sm">
        <div class="font-semibold mb-1">This document has no structured result.</div>
        <div v-if="additionalContent?.user_guidance?.user_message" class="mb-1">
          {{ additionalContent.user_guidance.user_message }}
        </div>
        <div v-else-if="additionalContent?.json_error" class="mb-1">
          Parser error: {{ additionalContent.json_error }}
        </div>
        <details v-if="additionalContent?.tuning_advice" class="mt-2">
          <summary class="cursor-pointer text-content-muted">Tuning advice</summary>
          <ul class="list-disc list-inside mt-1 text-content-muted">
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
    </div>

    <!-- Tabs -->
    <div class="flex items-center gap-1 px-5 border-b border-default bg-surface shrink-0">
      <button
        type="button"
        :class="[
          'px-3 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === 'json'
            ? 'border-primary text-content'
            : 'border-transparent text-content-muted hover:text-content',
        ]"
        @click="activeTab = 'json'"
      >
        <FileJson class="h-4 w-4 inline -mt-0.5 mr-1" />
        Extracted JSON
      </button>
      <button
        type="button"
        :class="[
          'px-3 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === 'text'
            ? 'border-primary text-content'
            : 'border-transparent text-content-muted hover:text-content',
        ]"
        @click="activeTab = 'text'"
      >
        <FileText class="h-4 w-4 inline -mt-0.5 mr-1" />
        Document Text
      </button>
      <button
        v-if="documentPreviewable"
        type="button"
        :class="[
          'px-3 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
          activeTab === 'file'
            ? 'border-primary text-content'
            : 'border-transparent text-content-muted hover:text-content',
        ]"
        @click="activeTab = 'file'"
      >
        <Eye class="h-4 w-4 inline -mt-0.5 mr-1" />
        Original File
      </button>

      <div class="ml-auto flex items-center gap-2 py-1.5">
        <BaseButton
          v-if="activeResult.result && activeTab === 'json'"
          variant="ghost"
          size="sm"
          class="-mr-1"
          :title="copied ? 'Copied!' : 'Copy JSON'"
          @click="copyResult"
        >
          <component :is="copied ? Check : Copy" class="h-4 w-4" />
        </BaseButton>
      </div>
    </div>

    <!-- Tab content (scrollable) -->
    <div class="flex-1 min-h-0 overflow-y-auto bg-surface">
      <transition name="doc-fade" mode="out-in">
        <div :key="activeResult.id" class="p-5">
          <!-- Extracted JSON -->
          <div v-if="activeTab === 'json'">
            <template v-if="activeResult.result">
              <JsonViewer :data="activeResult.result as Record<string, unknown>" />
            </template>
            <div v-else class="text-sm text-content-muted italic">
              No structured output for this document.
            </div>
          </div>

          <!-- Document text -->
          <div v-else-if="activeTab === 'text'">
            <div v-if="docLoading" class="flex flex-col items-center justify-center py-12">
              <LoadingSpinner size="medium" inline label="" />
              <span class="mt-2 text-sm text-content-muted">Loading document text…</span>
            </div>
            <template v-else-if="documentContent">
              <div
                v-if="isMarkdown(documentContent)"
                class="markdown-content"
                v-html="renderMarkdown(documentContent)"
              ></div>
              <pre v-else class="text-xs text-content whitespace-pre-wrap break-words font-mono">{{
                documentContent
              }}</pre>
            </template>
            <div v-else class="text-sm text-content-muted italic">No text content available.</div>
          </div>

          <!-- Original file preview -->
          <div v-else-if="activeTab === 'file'">
            <iframe
              v-if="documentPdfUrl"
              :src="documentPdfUrl"
              frameborder="0"
              class="rounded-card w-full h-[70vh] border border-default"
              :title="`Preview of ${documentLabel}`"
            ></iframe>
            <div
              v-else-if="documentPdfLoading"
              class="flex flex-col items-center justify-center py-12"
            >
              <LoadingSpinner size="medium" inline label="" />
              <span class="mt-2 text-sm text-content-muted">Loading preview…</span>
            </div>
            <div v-else class="text-sm text-content-muted italic">Failed to load preview.</div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { Check, ChevronLeft, ChevronRight, Copy, Eye, FileJson, FileText } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { renderMarkdown, isMarkdown } from '@/utils/markdown'
import { getPillClass } from '@/utils/statusStyles'
import { formatDateSmart } from '@/utils/formatters'
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

interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}

const props = defineProps<{
  result: TrialResultItem
  projectId: string | number
  index: number
  total: number
  hasPrev: boolean
  hasNext: boolean
}>()

defineEmits<{
  prev: []
  next: []
}>()

const toast = useToast()

const documentContent = ref('')
const docLoading = ref(false)
const documentPreviewable = ref(false)
const documentFileId = ref<number | null>(null)
const documentPdfUrl = ref('')
const documentPdfLoading = ref(false)
const copied = ref(false)
const activeTab = ref<'json' | 'text' | 'file'>('json')

const activeResult = computed(() => props.result)

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

const documentLabel = computed(
  () =>
    props.result.document_name ||
    props.result.original_file_name ||
    `Document #${props.result.document_id}`,
)

const tokenUsage = computed(() => {
  const usage = additionalContent.value?.usage as TokenUsage | undefined
  return usage?.total_tokens ?? '—'
})

const STATUS_LABELS: Record<string, string> = {
  success: 'OK',
  failed: 'Error',
  incomplete: 'Incomplete',
  invalid_json: 'Invalid JSON',
  schema_invalid: 'Schema invalid',
  refused: 'Refused',
  provider_error: 'Provider error',
}

const statusLabel = (status: string): string => STATUS_LABELS[status] || (status ? status : '—')

const statusPillClass = (status: string): string => {
  if (status === 'success') return getPillClass('green')
  if (status === 'incomplete') return getPillClass('yellow')
  if (status === 'refused') return getPillClass('orange')
  return getPillClass('red')
}

const analyzeOriginalFile = (fileType: string | undefined | null): boolean => {
  if (!fileType) return false
  return fileType === 'application/pdf' || fileType.startsWith('image/')
}

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

async function loadOriginalFilePreview(): Promise<void> {
  if (documentPdfUrl.value || documentPdfLoading.value) return
  if (!documentPreviewable.value || !documentFileId.value) return
  documentPdfLoading.value = true
  try {
    const fr = await filesApi.getContent(props.projectId, documentFileId.value, {
      preview: true,
    })
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

function resetDocState(): void {
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
  documentPdfUrl.value = ''
  documentPdfLoading.value = false
  documentContent.value = ''
  documentPreviewable.value = false
  documentFileId.value = null
  activeTab.value = 'json'
}

// When the active result changes, reset state and prefetch the new doc's text
// (and file preview when previewable) so tab switches feel instant.
watch(
  () => props.result.id,
  () => {
    resetDocState()
    loadDocumentTextAndMeta()
  },
  { immediate: true },
)

// Lazily load the original-file preview only when its tab is opened.
watch(activeTab, (tab) => {
  if (tab === 'file') loadOriginalFilePreview()
})

onUnmounted(() => {
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
})
</script>

<style scoped>
.doc-fade-enter-active,
.doc-fade-leave-active {
  transition: opacity 0.15s ease;
}
.doc-fade-enter-from,
.doc-fade-leave-to {
  opacity: 0;
}
</style>
