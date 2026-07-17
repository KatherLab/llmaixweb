<template>
  <div class="flex flex-col h-full min-h-0 bg-surface">
    <!-- Document header bar -->
    <div
      class="flex items-center justify-between gap-3 px-5 py-3 border-b border-default bg-surface-muted/60 shrink-0"
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
    </div>

    <!-- Error banner (failed docs — shown above the split, replaces Result tab) -->
    <div v-if="!activeResult.result || additionalContent?.json_error" class="px-5 pt-4 shrink-0">
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

    <!-- Panel layout: toggle chips add/remove panes (Source, Result, Reasoning, Metadata) -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <PanelLayout
        :panels="availablePanels"
        :model-value="activePanels"
        :max-visible="3"
        @update:model-value="activePanels = $event"
      >
        <!-- Source document (original file or extracted text) -->
        <template #pane-source>
          <div class="flex flex-col h-full min-h-0">
            <div
              class="flex items-center justify-between gap-2 px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <h4 class="flex items-center gap-2 text-sm font-semibold text-content-muted">
                <FileText class="h-4 w-4" /> Source Document
              </h4>
              <button
                v-if="hasPreviewableFile"
                class="text-xs text-primary hover:underline"
                @click="toggleOriginalView"
              >
                {{ showOriginal ? 'Show extracted text' : 'Show original file' }}
              </button>
            </div>
            <div class="flex-1 min-h-0 bg-surface-muted">
              <div
                v-if="documentPdfLoading"
                class="flex flex-col items-center justify-center h-full"
              >
                <LoadingSpinner size="medium" inline label="" />
                <span class="mt-2 text-sm text-content-muted">Loading preview…</span>
              </div>
              <DocumentFilePreview
                v-else-if="showOriginal && documentPdfUrl"
                view-mode="pdf"
                :original-pdf-url="documentPdfUrl"
              />
              <div v-else-if="docLoading" class="flex items-center justify-center h-full">
                <LoadingSpinner size="medium" inline label="" />
              </div>
              <pre
                v-else-if="documentContent"
                class="text-xs text-content-muted whitespace-pre-wrap break-words font-mono p-4 overflow-auto h-full"
                >{{ documentContent }}</pre>
              <div
                v-else
                class="flex items-center justify-center h-full p-6 text-sm text-content-subtle italic"
              >
                No original file or extracted text for this document.
              </div>
            </div>
          </div>
        </template>

        <!-- Result JSON -->
        <template #pane-result>
          <div class="flex flex-col h-full min-h-0">
            <div
              class="flex items-center justify-between gap-2 px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <h4 class="flex items-center gap-2 text-sm font-semibold text-content-muted">
                <Braces class="h-4 w-4" /> Result
              </h4>
            </div>
            <div class="relative flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <!-- Copy JSON — floats top-right so it doesn't affect header height -->
              <BaseButton
                v-if="activeResult.result"
                variant="ghost"
                size="sm"
                class="absolute top-2 right-2 shadow-sm"
                :title="copied ? 'Copied!' : 'Copy JSON'"
                @click="copyResult"
              >
                <component :is="copied ? Check : Copy" class="h-4 w-4" />
              </BaseButton>
              <JsonViewer
                v-if="activeResult.result"
                :data="activeResult.result as Record<string, unknown>"
              />
              <div v-else class="text-sm text-content-muted italic">
                No structured output for this document.
              </div>
            </div>
          </div>
        </template>

        <!-- Reasoning -->
        <template #pane-reasoning>
          <div class="flex flex-col h-full min-h-0">
            <h4
              class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <MessageSquare class="h-4 w-4" /> Reasoning
            </h4>
            <div class="flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <div
                v-if="reasoningContent"
                class="markdown-content"
                v-html="renderMarkdown(reasoningContent)"
              ></div>
              <div v-else class="text-sm text-content-muted italic">
                No reasoning content was captured for this document.
              </div>
            </div>
          </div>
        </template>

        <!-- Metadata -->
        <template #pane-metadata>
          <div class="flex flex-col h-full min-h-0">
            <h4
              class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <Info class="h-4 w-4" /> Metadata
            </h4>
            <div class="flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <dl class="space-y-3 text-sm">
                <div v-if="additionalContent?.usage">
                  <dt class="font-semibold text-content mb-1">Token Usage</dt>
                  <ul class="text-xs text-content-muted ml-2 space-y-0.5">
                    <li v-for="(v, k) in additionalContent.usage" :key="k">
                      <span class="font-medium">{{ formatKey(k as string) }}:</span> {{ v }}
                    </li>
                  </ul>
                </div>
                <div v-if="additionalContent?.finish_reason">
                  <dt class="font-semibold text-content">Finish Reason</dt>
                  <dd class="text-xs text-content-muted">
                    {{ additionalContent.finish_reason }}
                  </dd>
                </div>
                <div v-if="additionalContent?.json_error">
                  <dt class="font-semibold text-content">JSON Error</dt>
                  <dd class="text-xs text-red-600 dark:text-red-400">
                    {{ additionalContent.json_error }}
                  </dd>
                </div>
                <div
                  v-if="
                    !additionalContent?.usage &&
                    !additionalContent?.finish_reason &&
                    !additionalContent?.json_error
                  "
                  class="text-sm text-content-muted italic"
                >
                  No metadata for this document.
                </div>
              </dl>
            </div>
          </div>
        </template>
      </PanelLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { Braces, Check, Copy, FileText, Info, MessageSquare } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import PanelLayout, { type PanelOption } from '@/components/common/PanelLayout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import DocumentFilePreview from '@/components/documents/DocumentFilePreview.vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { renderMarkdown } from '@/utils/markdown'
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
}>()

const toast = useToast()

const documentContent = ref('')
const docLoading = ref(false)
const documentPreviewable = ref(false)
const documentFileId = ref<number | null>(null)
const documentPdfUrl = ref('')
const documentPdfLoading = ref(false)
const copied = ref(false)
// Show the original file when available, else fall back to extracted text.
const showOriginal = ref(true)
// Active panels in the PanelLayout (order = left-to-right). 'source' is added
// by default when there's original content; 'result' is always present.
const activePanels = ref<string[]>(['result'])

const activeResult = computed(() => props.result)

// Whether the source pane has anything to show (previewable original file OR
// extracted text). Drives whether the Source chip appears at all.
const hasOriginalContent = computed(
  () => documentPreviewable.value || !!documentContent.value || docLoading.value,
)
const hasPreviewableFile = computed(() => documentPreviewable.value && !!documentPdfUrl.value)

// The chip menu. Source is only offered when there's original content;
// Reasoning / Metadata only when they exist. Result is always available.
const availablePanels = computed<PanelOption[]>(() => {
  const panels: PanelOption[] = []
  if (hasOriginalContent.value) {
    panels.push({ key: 'source', label: 'Source', icon: FileText })
  }
  panels.push({ key: 'result', label: 'Result', icon: Braces })
  if (reasoningContent.value) {
    panels.push({ key: 'reasoning', label: 'Reasoning', icon: MessageSquare })
  }
  if (
    additionalContent.value?.usage ||
    additionalContent.value?.finish_reason ||
    additionalContent.value?.json_error
  ) {
    panels.push({ key: 'metadata', label: 'Metadata', icon: Info })
  }
  return panels
})

function toggleOriginalView(): void {
  showOriginal.value = !showOriginal.value
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

const reasoningContent = computed(() => additionalContent.value?.reasoning_content || '')

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

const formatKey = (key: string): string => key.replace(/_/g, ' ')

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

// Monotonic load counter: rapid prev/next through results fires the loaders
// again before earlier responses land; a stale response must not overwrite
// the newer document's state (or create an object URL nothing revokes).
let loadSeq = 0

async function loadDocumentTextAndMeta(seq: number): Promise<void> {
  const docId = props.result.document_id
  if (!docId) return
  docLoading.value = true
  try {
    const r = await documentsApi.get(props.projectId, docId)
    if (seq !== loadSeq) return // superseded by a newer result selection
    const d = r.data
    documentContent.value = d.text || 'No text content available'
    const previewable = analyzeOriginalFile(d.original_file?.file_type)
    documentPreviewable.value = previewable
    documentFileId.value = previewable
      ? d.preprocessed_file_id && d.preprocessed_file?.file_type === 'application/pdf'
        ? d.preprocessed_file_id
        : d.original_file_id
      : null
    // Default to Source + Result side-by-side when there's original content.
    if (hasOriginalContent.value && !activePanels.value.includes('source')) {
      activePanels.value = ['source', ...activePanels.value]
    }
  } catch (err) {
    if (seq !== loadSeq) return
    documentContent.value = 'Error loading document content'
    console.error(err)
  } finally {
    if (seq === loadSeq) docLoading.value = false
  }
}

async function loadOriginalFilePreview(seq: number): Promise<void> {
  if (documentPdfUrl.value || documentPdfLoading.value) return
  if (!documentPreviewable.value || !documentFileId.value) return
  documentPdfLoading.value = true
  try {
    const fr = await filesApi.getContent(props.projectId, documentFileId.value, {
      preview: true,
    })
    // Bail BEFORE creating the object URL — creating it and then dropping the
    // reference would leak one full-file blob per superseded load.
    if (seq !== loadSeq) return
    const blob = new Blob([fr.data], {
      type: (fr.headers['content-type'] as string) || undefined,
    })
    documentPdfUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    if (seq !== loadSeq) return
    console.error(err)
    toast.error('Failed to load document')
  } finally {
    if (seq === loadSeq) documentPdfLoading.value = false
  }
}

function resetDocState(): void {
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
  documentPdfUrl.value = ''
  documentPdfLoading.value = false
  documentContent.value = ''
  documentPreviewable.value = false
  documentFileId.value = null
  showOriginal.value = true
  // Reset to just Result; loadDocumentTextAndMeta() will prepend Source once it
  // confirms there's original content to show.
  activePanels.value = ['result']
}

// When the active result changes, reset state and prefetch the new doc's text
// + file preview so pane switches feel instant. The preview load must run
// AFTER the text/meta load resolves — it depends on documentPreviewable /
// documentFileId set there.
watch(
  () => props.result.id,
  async () => {
    const seq = ++loadSeq
    resetDocState()
    await loadDocumentTextAndMeta(seq)
    if (seq !== loadSeq) return
    await loadOriginalFilePreview(seq)
  },
  { immediate: true },
)

onUnmounted(() => {
  // Invalidate any in-flight load so it can't create an object URL after
  // this final revoke (which would leak it).
  loadSeq++
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
})
</script>
