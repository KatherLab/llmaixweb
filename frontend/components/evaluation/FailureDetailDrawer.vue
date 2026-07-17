<template>
  <SlideOver
    :open="open"
    aria-label="Failure details"
    max-width="max-w-[95rem]"
    @close="$emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between gap-4 flex-1 min-w-0 pr-8">
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-content truncate">
            {{ documentName || `Document #${documentId}` }}
          </h3>
          <p class="text-xs text-content-subtle mt-0.5">
            <span :class="statusClass">{{ statusLabel }}</span>
            <span v-if="docEval">
              · {{ docEval.correct_fields }}/{{ docEval.total_fields }} fields correct</span
            >
            <span v-if="docEval"> · {{ formatMetricPercent(docEval.accuracy) }} accuracy</span>
          </p>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <BaseButton
            variant="ghost"
            size="sm"
            :title="leftRailOpen ? 'Hide document list' : 'Show document list'"
            @click="leftRailOpen = !leftRailOpen"
          >
            <PanelLeft class="h-4 w-4" />
          </BaseButton>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="!hasPrev"
            :title="hasPrev ? 'Previous document (←)' : 'First document'"
            @click="$emit('prev')"
          >
            <ChevronLeft class="h-4 w-4" />
          </BaseButton>
          <span class="text-xs font-medium text-content-muted tabular-nums px-1 whitespace-nowrap">
            {{ docPosition }}
          </span>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="!hasNext"
            :title="hasNext ? 'Next document (→)' : 'Last document'"
            @click="$emit('next')"
          >
            <ChevronRight class="h-4 w-4" />
          </BaseButton>
        </div>
      </div>
    </template>

    <!-- Error banner for documents that couldn't be scored -->
    <div v-if="docEval?.error" class="px-6 pt-4 shrink-0">
      <ErrorBanner :message="docEval.error" />
    </div>

    <div v-if="docEval" class="flex h-full min-h-0">
      <!-- Left rail: document list (overview of all docs in this eval) -->
      <aside
        :class="[
          'flex flex-col border-r border-default bg-surface-muted/40 shrink-0',
          leftRailOpen ? 'w-64' : 'w-0 -ml-px overflow-hidden',
        ]"
      >
        <div v-show="leftRailOpen" class="flex flex-col h-full min-w-0">
          <div class="p-3 border-b border-default shrink-0">
            <SearchInput v-model="railSearch" placeholder="Search documents…" />
          </div>
          <div class="flex-1 min-h-0 overflow-y-auto p-2 space-y-0.5">
            <button
              v-for="(d, i) in railDocs"
              :key="d.document_id"
              type="button"
              :class="[
                'w-full text-left px-3 py-2 rounded-card border-l-2 transition-colors',
                i === currentDocIndex
                  ? 'bg-primary-soft border-primary'
                  : 'border-transparent hover:bg-surface',
              ]"
              @click="$emit('select-doc', d.document_id)"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span
                  :class="['h-1.5 w-1.5 rounded-full shrink-0', accuracyDotClass(d.accuracy)]"
                />
                <span class="text-sm text-content truncate flex-1">{{
                  d.document_name || `Document #${d.document_id}`
                }}</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 pl-3.5">
                <span class="text-[10px] uppercase tracking-wide text-content-subtle">
                  {{ docStatusLabel(d) }}
                </span>
                <span class="text-[10px] font-medium" :class="accuracyColor(d.accuracy)">
                  {{ formatMetricPercent(d.accuracy) }}
                </span>
              </div>
            </button>
            <div
              v-if="!railDocs.length"
              class="flex flex-col items-center justify-center py-8 px-3 text-center"
            >
              <p class="text-xs text-content-subtle">No documents match your search.</p>
              <button
                type="button"
                class="mt-2 text-xs font-medium text-primary hover:underline"
                @click="railSearch = ''"
              >
                Clear search
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- Right: panels (source / GT vs prediction / output / reasoning) -->
      <div class="flex-1 min-w-0 flex flex-col">
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
                  {{ viewMode === 'text' ? 'Show original file' : 'Show extracted text' }}
                </button>
              </div>
              <div class="flex-1 min-h-0 bg-surface-muted">
                <div v-if="loadingDocument" class="flex items-center justify-center h-full p-6">
                  <LoadingSpinner size="medium" />
                </div>
                <DocumentFilePreview
                  v-else-if="viewMode === 'pdf' && originalPdfUrl"
                  view-mode="pdf"
                  :original-pdf-url="originalPdfUrl"
                />
                <DocumentFilePreview
                  v-else-if="viewMode === 'image' && originalImageUrl"
                  view-mode="image"
                  :original-image-url="originalImageUrl"
                />
                <div v-else class="p-4 h-full overflow-auto">
                  <pre v-if="documentText" class="text-xs text-content-muted whitespace-pre-wrap">{{
                    documentText
                  }}</pre>
                  <p v-else class="text-xs text-content-subtle italic">
                    No preview available for this file type. Showing extracted text instead — but
                    none was extracted during preprocessing.
                  </p>
                </div>
              </div>
            </div>
          </template>

          <!-- GT vs Prediction -->
          <template #pane-comparison>
            <div class="flex flex-col h-full min-h-0">
              <h4
                class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
              >
                <GitCompare class="h-4 w-4" /> Expected vs Predicted
              </h4>
              <div class="flex-1 min-h-0 overflow-auto bg-surface">
                <table class="w-full text-xs">
                  <thead class="sticky top-0 bg-surface-muted">
                    <tr>
                      <th class="p-2 text-left font-medium text-content-muted">Field</th>
                      <th class="p-2 text-left font-medium text-content-muted">Expected</th>
                      <th class="p-2 text-left font-medium text-content-muted">Got</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(detail, fieldName) in fieldDetails"
                      :key="fieldName"
                      :class="
                        detail.is_correct
                          ? 'bg-green-50 dark:bg-green-900/20'
                          : 'bg-red-50 dark:bg-red-900/20'
                      "
                    >
                      <td class="p-2 align-top">
                        <div class="font-medium text-content-muted">
                          {{ prettifyField(fieldName) }}
                        </div>
                        <div v-if="!detail.is_correct" class="mt-1 space-y-0.5">
                          <Tooltip :text="getErrorSuggestion(detail.error_type)">
                            <span
                              class="text-[10px] font-semibold uppercase tracking-wide text-red-600 dark:text-red-400 cursor-help"
                              >{{ prettifyErrorType(detail.error_type) }}</span
                            >
                          </Tooltip>
                          <p class="text-[10px] leading-snug text-content-subtle">
                            {{ getErrorTypeDescription(detail.error_type) }}
                          </p>
                        </div>
                      </td>
                      <td class="p-2 align-top text-content-muted break-words">
                        {{ formatValue(detail.ground_truth_value) }}
                      </td>
                      <td class="p-2 align-top">
                        <div class="flex items-start gap-1">
                          <component
                            :is="detail.is_correct ? Check : X"
                            :class="
                              detail.is_correct
                                ? 'text-green-600 dark:text-green-400'
                                : 'text-red-600 dark:text-red-400'
                            "
                            class="h-3.5 w-3.5 mt-0.5 shrink-0"
                          />
                          <span class="text-content-muted break-words">{{
                            formatValue(detail.predicted_value)
                          }}</span>
                        </div>
                      </td>
                    </tr>
                    <tr v-if="!Object.keys(fieldDetails).length">
                      <td colspan="3" class="p-4 text-center text-content-subtle italic">
                        No field-level comparison available.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>

          <!-- Model output -->
          <template #pane-output>
            <div class="flex flex-col h-full min-h-0">
              <h4
                class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
              >
                <Braces class="h-4 w-4" /> Output
              </h4>
              <div class="flex-1 min-h-0 overflow-auto bg-surface p-4">
                <div
                  v-if="loadingResult"
                  class="flex items-center justify-center h-full min-h-[200px]"
                >
                  <LoadingSpinner size="medium" />
                </div>
                <JsonViewer v-else-if="trialResult?.result" :data="trialResult.result" />
                <p v-else class="text-xs text-content-subtle italic">
                  No structured result was produced for this document.
                </p>
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
              <div class="flex-1 min-h-0 overflow-auto bg-surface p-4">
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
        </PanelLayout>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <p class="text-xs text-content-subtle">
          Tip: use <kbd class="px-1 py-0.5 bg-surface-sunken rounded">←</kbd> /
          <kbd class="px-1 py-0.5 bg-surface-sunken rounded">→</kbd> to move between documents.
        </p>
        <BaseButton variant="secondary" @click="$emit('close')">Close</BaseButton>
      </div>
    </template>
  </SlideOver>
</template>

<script setup lang="ts">
import { ref, computed, watch, type PropType } from 'vue'
import {
  Braces,
  Check,
  ChevronLeft,
  ChevronRight,
  FileText,
  GitCompare,
  MessageSquare,
  PanelLeft,
  X,
} from '@lucide/vue'
import SlideOver from '@/components/common/SlideOver.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import PanelLayout, { type PanelOption } from '@/components/common/PanelLayout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import DocumentFilePreview from '@/components/documents/DocumentFilePreview.vue'
import { renderMarkdown } from '@/utils/markdown'
import {
  formatMetricPercent,
  getErrorTypeDescription,
  getErrorSuggestion,
} from '@/utils/metricsDefinitions'
import {
  prettifyField,
  accuracyColor,
  prettifyErrorType,
  documentStatusLabel,
  ACCURACY_THRESHOLDS,
} from '@/utils/evaluationHelpers'
import type { DocumentEvaluationDetail, TrialResultItem } from '@/types'

/** Original file attached to a document (subset used here). */
interface OriginalFile {
  id?: number
  file_type?: string
  [key: string]: unknown
}

const props = defineProps({
  open: { type: Boolean, required: true },
  documentId: { type: [String, Number] as PropType<string | number | null>, default: null },
  documentName: { type: String, default: '' },
  docEval: { type: Object as PropType<DocumentEvaluationDetail | null>, default: null },
  trialResult: { type: Object as PropType<TrialResultItem | null>, default: null },
  loadingDocument: { type: Boolean, default: false },
  loadingResult: { type: Boolean, default: false },
  documentText: { type: String, default: '' },
  originalFile: { type: Object as PropType<OriginalFile | null>, default: null },
  originalFileUrl: { type: String, default: '' },
  originalFileType: { type: String, default: '' },
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
  /** "x / y" position indicator for the header (1-based). */
  docPosition: { type: String, default: '' },
  /** Filtered doc list (reflects page-level search/status/field/confusion
   * filters) — drives the left rail overview. */
  documents: { type: Array as PropType<DocumentEvaluationDetail[]>, default: () => [] },
  /** Index of the open doc within `documents` (-1 if not found). */
  currentDocIndex: { type: Number, default: -1 },
})

defineEmits<{
  close: []
  prev: []
  next: []
  /** Rail click — host loads the clicked document. */
  'select-doc': [documentId: number]
}>()

// Active panels in the PanelLayout (order = left-to-right). Default to the
// GT-vs-prediction comparison — that's the eval use case. Source is prepended
// when original content arrives.
const activePanels = ref<string[]>(['comparison'])
const showOriginal = ref(true) // show original file when available, else text

// ---- Left rail (document overview) ----
const leftRailOpen = ref(true)
const railSearch = ref('')
// Further filter the page-level filtered list by the rail's local search.
const railDocs = computed<DocumentEvaluationDetail[]>(() => {
  const q = railSearch.value.trim().toLowerCase()
  if (!q) return props.documents
  return props.documents.filter((d) =>
    (d.document_name || `Document #${d.document_id}`).toLowerCase().includes(q),
  )
})

const accuracyDotClass = (acc: number): string => {
  if (acc >= ACCURACY_THRESHOLDS.HIGH) return 'bg-green-500'
  if (acc < ACCURACY_THRESHOLDS.LOW) return 'bg-red-500'
  return 'bg-yellow-500'
}

const docStatusLabel = (d: DocumentEvaluationDetail): string => documentStatusLabel(d)

const fieldDetails = computed(() => props.docEval?.field_details || {})

const reasoningContent = computed(
  () => (props.trialResult?.additional_content?.reasoning_content as string | undefined) || '',
)

const hasPreviewableFile = computed(
  () => props.originalFileType === 'pdf' || props.originalFileType === 'image',
)

// Whether the source pane has anything to show (previewable original file OR
// extracted text). Drives whether the Source chip appears at all.
const hasOriginalContent = computed(
  () => hasPreviewableFile.value || !!props.documentText || props.loadingDocument,
)

// The chip menu. Source only when there's original content; Reasoning only
// when it exists. Comparison + Output are always available.
const availablePanels = computed<PanelOption[]>(() => {
  const panels: PanelOption[] = []
  if (hasOriginalContent.value) {
    panels.push({ key: 'source', label: 'Source', icon: FileText })
  }
  panels.push({ key: 'comparison', label: 'Comparison', icon: GitCompare })
  panels.push({ key: 'output', label: 'Output', icon: Braces })
  if (reasoningContent.value) {
    panels.push({ key: 'reasoning', label: 'Reasoning', icon: MessageSquare })
  }
  return panels
})

const viewMode = computed(() => {
  if (!showOriginal.value) return 'text'
  if (props.originalFileType === 'pdf' && props.originalFileUrl) return 'pdf'
  if (props.originalFileType === 'image' && props.originalFileUrl) return 'image'
  return 'text'
})

const statusLabel = computed(() => {
  if (props.docEval?.has_error || props.docEval?.error) return 'Evaluation error'
  if (props.docEval && props.docEval.accuracy >= ACCURACY_THRESHOLDS.HIGH) return 'High accuracy'
  if (props.docEval && props.docEval.accuracy < ACCURACY_THRESHOLDS.LOW) return 'Low accuracy'
  return 'Partial'
})

const statusClass = computed(() => {
  if (props.docEval?.has_error || props.docEval?.error)
    return 'text-red-600 dark:text-red-400 font-medium'
  // accuracyColor returns the same green/red/yellow tiers; append weight here.
  return `${accuracyColor(props.docEval?.accuracy)} font-medium`
})

// Template aliases for the pre-built object URL, named by preview kind.
// (Keeps the template's originalPdfUrl / originalImageUrl references valid.)
const originalPdfUrl = computed(() => props.originalFileUrl)
const originalImageUrl = computed(() => props.originalFileUrl)

const toggleOriginalView = (): void => {
  showOriginal.value = !showOriginal.value
}

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// Reset panels + original-view toggle when switching documents. Source is
// prepended once hasOriginalContent flips true (watched below).
watch(
  () => props.documentId,
  () => {
    activePanels.value = ['comparison']
    showOriginal.value = true
  },
)

// When original content becomes available, show Source + Comparison by default.
watch(hasOriginalContent, (has) => {
  if (has && !activePanels.value.includes('source')) {
    activePanels.value = ['source', ...activePanels.value]
  }
})
</script>
