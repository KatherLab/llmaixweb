<template>
  <BaseModal :open="open" placement="right" panel-class="w-full max-w-6xl" @close="$emit('close')">
    <template #header>
      <div class="flex items-center justify-between gap-4 pr-8">
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-slate-900 dark:text-white truncate">
            {{ documentName || `Document #${documentId}` }}
          </h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            <span :class="statusClass">{{ statusLabel }}</span>
            <span v-if="docEval">
              · {{ docEval.correct_fields }}/{{ docEval.total_fields }} fields correct</span
            >
            <span v-if="docEval"> · {{ formatMetricPercent(docEval.accuracy) }} accuracy</span>
          </p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <BaseButton variant="secondary" size="sm" :disabled="!hasPrev" @click="$emit('prev')">
            <ChevronLeft class="h-4 w-4" />
            Prev
          </BaseButton>
          <BaseButton variant="secondary" size="sm" :disabled="!hasNext" @click="$emit('next')">
            Next
            <ChevronRight class="h-4 w-4" />
          </BaseButton>
        </div>
      </div>
    </template>

    <!-- Error banner for documents that couldn't be scored -->
    <div v-if="docEval?.error" class="px-6 pt-4">
      <ErrorBanner :message="docEval.error" />
    </div>

    <div v-if="docEval" class="px-6 pb-6 space-y-6">
      <!-- 3-column comparison: Original | Model output + reasoning | GT vs prediction -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- Column 1: Original document -->
        <section class="flex flex-col min-h-0">
          <h4
            class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2"
          >
            <FileText class="h-4 w-4" /> Original Document
          </h4>
          <div
            class="flex-1 min-h-[300px] border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-slate-50 dark:bg-slate-800"
          >
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
              <pre
                v-if="documentText"
                class="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap"
                >{{ documentText }}</pre>
              <p v-else class="text-xs text-slate-500 dark:text-slate-400 italic">
                No preview available for this file type. Showing extracted text instead — but none
                was extracted during preprocessing.
              </p>
            </div>
          </div>
          <button
            v-if="hasPreviewableFile"
            class="mt-1 text-xs text-blue-600 dark:text-blue-400 hover:underline text-left"
            @click="toggleOriginalView"
          >
            {{ viewMode === 'text' ? 'Show original file' : 'Show extracted text' }}
          </button>
        </section>

        <!-- Column 2: Model output + reasoning -->
        <section class="flex flex-col min-h-0">
          <h4
            class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2"
          >
            <Bot class="h-4 w-4" /> Model Output
          </h4>
          <div
            class="flex-1 min-h-[300px] border border-slate-200 dark:border-slate-700 rounded-lg overflow-auto bg-slate-50 dark:bg-slate-800 p-3"
          >
            <div v-if="loadingResult" class="flex items-center justify-center h-full">
              <LoadingSpinner size="medium" />
            </div>
            <JsonViewer v-else-if="trialResult?.result" :data="trialResult.result" />
            <p v-else class="text-xs text-slate-500 dark:text-slate-400 italic">
              No structured result was produced for this document.
            </p>
          </div>
          <ResultReasoningPanel
            v-if="trialResult"
            :reasoning-content="reasoningContent"
            :additional-content="trialResult.additional_content"
            :show="showReasoning"
            @toggle="showReasoning = !showReasoning"
          />
        </section>

        <!-- Column 3: Ground truth vs prediction -->
        <section class="flex flex-col min-h-0">
          <h4
            class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2"
          >
            <ScaleIcon class="h-4 w-4" /> Ground Truth vs Prediction
          </h4>
          <div
            class="flex-1 min-h-[300px] border border-slate-200 dark:border-slate-700 rounded-lg overflow-auto bg-white dark:bg-slate-800"
          >
            <table class="w-full text-xs">
              <thead class="sticky top-0 bg-slate-50 dark:bg-slate-700">
                <tr>
                  <th class="p-2 text-left font-medium text-slate-600 dark:text-slate-300">
                    Field
                  </th>
                  <th class="p-2 text-left font-medium text-slate-600 dark:text-slate-300">
                    Expected
                  </th>
                  <th class="p-2 text-left font-medium text-slate-600 dark:text-slate-300">Got</th>
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
                    <div class="font-medium text-slate-800 dark:text-slate-200">
                      {{ prettifyField(fieldName) }}
                    </div>
                    <Tooltip v-if="!detail.is_correct" :text="errorTooltip(detail.error_type)">
                      <span
                        class="text-[10px] text-red-600 dark:text-red-400 underline cursor-help"
                        >{{ prettifyErrorType(detail.error_type) }}</span
                      >
                    </Tooltip>
                  </td>
                  <td class="p-2 align-top text-slate-700 dark:text-slate-300 break-words">
                    {{ formatValue(detail.ground_truth_value) }}
                  </td>
                  <td class="p-2 align-top">
                    <div class="flex items-start gap-1">
                      <component
                        :is="detail.is_correct ? Check : X"
                        :class="detail.is_correct ? 'text-green-600' : 'text-red-600'"
                        class="h-3.5 w-3.5 mt-0.5 shrink-0"
                      />
                      <span class="text-slate-700 dark:text-slate-300 break-words">{{
                        formatValue(detail.predicted_value)
                      }}</span>
                    </div>
                  </td>
                </tr>
                <tr v-if="!Object.keys(fieldDetails).length">
                  <td colspan="3" class="p-4 text-center text-slate-500 dark:text-slate-400 italic">
                    No field-level comparison available.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <p class="text-xs text-slate-500 dark:text-slate-400">
          Tip: use <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded">J</kbd> /
          <kbd class="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded">K</kbd> to move between
          documents.
        </p>
        <BaseButton variant="secondary" @click="$emit('close')">Close</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Bot, Check, ChevronLeft, ChevronRight, FileText, Scale, X } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import DocumentFilePreview from '@/components/documents/DocumentFilePreview.vue'
import ResultReasoningPanel from '@/components/trials/ResultReasoningPanel.vue'
import {
  formatMetricPercent,
  getErrorTypeDescription,
  getErrorSuggestion,
} from '@/utils/metricsDefinitions'
import {
  prettifyField,
  accuracyColor,
  prettifyErrorType,
  ACCURACY_THRESHOLDS,
} from '@/utils/evaluationHelpers'

// `Scale` is exported as `Scale` by lucide; alias for template clarity.
const ScaleIcon = Scale

const props = defineProps({
  open: { type: Boolean, required: true },
  documentId: { type: [String, Number], default: null },
  documentName: { type: String, default: '' },
  docEval: { type: Object, default: null }, // DocumentEvaluationDetail
  trialResult: { type: Object, default: null }, // TrialResultItem (result + additional_content)
  loadingDocument: { type: Boolean, default: false },
  loadingResult: { type: Boolean, default: false },
  documentText: { type: String, default: '' },
  originalFile: { type: Object, default: null }, // Document.original_file
  originalFileUrl: { type: String, default: '' }, // pre-built object URL for PDF/image
  originalFileType: { type: String, default: '' }, // 'pdf' | 'image' | 'other'
  hasPrev: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
})

defineEmits(['close', 'prev', 'next'])

const showReasoning = ref(false)
const showOriginal = ref(true) // show original file when available, else text

const fieldDetails = computed(() => props.docEval?.field_details || {})

const reasoningContent = computed(
  () => props.trialResult?.additional_content?.reasoning_content || '',
)

const hasPreviewableFile = computed(
  () => props.originalFileType === 'pdf' || props.originalFileType === 'image',
)

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

const toggleOriginalView = () => {
  showOriginal.value = !showOriginal.value
}

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const errorTooltip = (errorType) => {
  return `${getErrorTypeDescription(errorType)} — ${getErrorSuggestion(errorType)}`
}

// Reset reasoning toggle when switching documents.
watch(
  () => props.documentId,
  () => {
    showReasoning.value = false
    showOriginal.value = true
  },
)
</script>
