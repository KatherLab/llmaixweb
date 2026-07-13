<template>
  <BaseModal
    :open="open"
    title="Export Evaluation Report"
    size="lg"
    body-class="p-6"
    @close="$emit('close')"
  >
    <div class="space-y-6">
      <!-- Export format selection -->
      <div>
        <label :class="labelClass">Export Format</label>
        <div class="grid grid-cols-3 gap-3">
          <div
            class="relative flex cursor-pointer rounded-card border p-4 focus:outline-none"
            :class="exportFormat === 'csv' ? 'border-primary ring-2 ring-ring' : 'border-strong'"
            @click="exportFormat = 'csv'"
          >
            <div class="flex h-5 items-center">
              <input v-model="exportFormat" type="radio" value="csv" :class="radioClass" />
            </div>
            <div class="ml-3">
              <div class="text-sm font-medium text-content">CSV</div>
              <div class="text-sm text-content-subtle">Comma-separated values</div>
            </div>
          </div>
          <div
            class="relative flex cursor-pointer rounded-card border p-4 focus:outline-none"
            :class="exportFormat === 'xlsx' ? 'border-primary ring-2 ring-ring' : 'border-strong'"
            @click="exportFormat = 'xlsx'"
          >
            <div class="flex h-5 items-center">
              <input v-model="exportFormat" type="radio" value="xlsx" :class="radioClass" />
            </div>
            <div class="ml-3">
              <div class="text-sm font-medium text-content">Excel</div>
              <div class="text-sm text-content-subtle">Excel spreadsheet</div>
            </div>
          </div>
          <div
            class="relative flex cursor-pointer rounded-card border p-4 focus:outline-none"
            :class="exportFormat === 'zip' ? 'border-primary ring-2 ring-ring' : 'border-strong'"
            @click="exportFormat = 'zip'"
          >
            <div class="flex h-5 items-center">
              <input v-model="exportFormat" type="radio" value="zip" :class="radioClass" />
            </div>
            <div class="ml-3">
              <div class="text-sm font-medium text-content">ZIP</div>
              <div class="text-sm text-content-subtle">ZIP archive (advanced)</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Evaluation selection -->
      <div>
        <label :class="labelClass">Select Evaluations</label>
        <div class="max-h-64 overflow-y-auto border border-default rounded-card">
          <div class="p-3 border-b border-default bg-surface-muted">
            <label class="flex items-center">
              <input
                type="checkbox"
                :checked="allSelected"
                :class="checkboxClass"
                @change="toggleSelectAll"
              />
              <span class="ml-2 text-sm font-medium text-content-muted">Select All</span>
            </label>
          </div>
          <div class="divide-y divide-default">
            <div
              v-for="evaluation in evaluations"
              :key="evaluation.id"
              class="p-3 hover:bg-surface-muted"
            >
              <label class="flex items-center">
                <input
                  v-model="selectedEvaluations"
                  type="checkbox"
                  :value="evaluation.id"
                  :class="checkboxClass"
                />
                <div class="ml-3 flex-1">
                  <div class="text-sm font-medium text-content">
                    {{
                      trialLabel(
                        {
                          name: evaluation.trial_name,
                          project_trial_number: evaluation.project_trial_number,
                        },
                        evaluation.trial_id,
                      )
                    }}
                  </div>
                  <div class="text-sm text-content-subtle">
                    {{ getEvaluationAccuracyPct(evaluation) }} accuracy •
                    {{ getEvaluationDocumentCount(evaluation) }} documents •
                    {{ formatDate(evaluation.created_at) }}
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
        <div
          v-if="selectedEvaluations.length === 0"
          class="mt-2 text-sm text-red-600 dark:text-red-400"
        >
          Please select at least one evaluation to export.
        </div>
      </div>

      <!-- Export options -->
      <div>
        <label :class="labelClass">Export Options</label>
        <div class="space-y-3">
          <div class="flex items-center">
            <input
              id="include-details"
              v-model="includeDetails"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-details" class="ml-2 text-sm text-content-muted">
              Include detailed document-level metrics
            </label>
          </div>
          <div class="flex items-center">
            <input
              id="include-field-details"
              v-model="includeFieldDetails"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-field-details" class="ml-2 text-sm text-content-muted">
              Include field-by-field comparison data
            </label>
          </div>
          <div class="flex items-center">
            <input
              id="include-errors"
              v-model="includeErrors"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-errors" class="ml-2 text-sm text-content-muted">
              Include error analysis and examples
            </label>
          </div>
          <div v-if="exportFormat === 'zip'" class="flex items-center">
            <input
              id="include-document-content"
              v-model="includeDocumentContent"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-document-content" class="ml-2 text-sm text-content-muted">
              Include document content (in docs/)
            </label>
          </div>
          <div v-if="exportFormat === 'zip'" class="flex items-center">
            <input
              id="include-gt-content"
              v-model="includeGroundTruthContent"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-gt-content" class="ml-2 text-sm text-content-muted">
              Include ground truth content (in docs/)
            </label>
          </div>
        </div>
      </div>

      <!-- Preview of export content -->
      <div v-if="selectedEvaluations.length > 0" class="bg-surface-muted rounded-card p-4">
        <h4 class="text-sm font-medium text-content-muted mb-2">Export Preview</h4>
        <div class="text-sm text-content-muted space-y-1">
          <div>• {{ selectedEvaluations.length }} evaluation(s) selected</div>
          <div>• {{ totalDocuments }} total documents</div>
          <div v-if="includeDetails">• Document-level metrics included</div>
          <div v-if="includeFieldDetails">• Field comparison data included</div>
          <div v-if="includeErrors">• Error analysis included</div>
          <div v-if="exportFormat === 'zip' && includeDocumentContent">
            • Document content files included
          </div>
          <div v-if="exportFormat === 'zip' && includeGroundTruthContent">
            • Ground truth files included
          </div>
          <div v-if="includesLargeContent" class="text-xs text-amber-600 dark:text-amber-400 mt-2">
            Includes original document/ground-truth files — the archive may be large.
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')"> Cancel </BaseButton>
      <BaseButton
        :loading="isExporting"
        :disabled="isExporting || selectedEvaluations.length === 0"
        @click="exportReport"
      >
        <span v-if="!isExporting" class="flex items-center gap-1.5">
          <Upload class="w-4 h-4" />
          Export Report
        </span>
        <span v-else>Exporting...</span>
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Upload } from '@lucide/vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { formatDate } from '@/utils/formatters'
import { getEvaluationAccuracyPct, getEvaluationDocumentCount } from '@/utils/evaluationHelpers'
import { trialLabel } from '@/utils/trialLabel'
import { checkboxClass, radioClass, labelClass } from '@/utils/formStyles'
import { useToast } from '@/composables/useToast'
import { useFileDownload } from '@/composables/useFileDownload'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import type { Evaluation } from '@/types'

type ExportFormat = 'csv' | 'xlsx' | 'zip'

interface Props {
  open: boolean
  projectId: string | number
  evaluations: Evaluation[]
}

const props = defineProps<Props>()

const emit = defineEmits<{ close: [] }>()
const toast = useToast()
const { downloadFromApi } = useFileDownload()
const isExporting = ref(false)

const exportFormat = ref<ExportFormat>('csv')
const selectedEvaluations = ref<number[]>([])
const includeDetails = ref(true)
const includeFieldDetails = ref(false)
const includeErrors = ref(false)
const includeDocumentContent = ref(false)
const includeGroundTruthContent = ref(false)

// Reset export selections when the modal closes so a reopen starts fresh
// (component stays mounted to enable the close transition).
watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      exportFormat.value = 'csv'
      selectedEvaluations.value = []
      includeDetails.value = true
      includeFieldDetails.value = false
      includeErrors.value = false
      includeDocumentContent.value = false
      includeGroundTruthContent.value = false
    }
  },
)

const allSelected = computed(() => {
  return (
    props.evaluations.length > 0 && selectedEvaluations.value.length === props.evaluations.length
  )
})

const totalDocuments = computed(() => {
  return selectedEvaluations.value.reduce((total, evalId) => {
    const evaluation = props.evaluations.find((e) => e.id === evalId)
    return total + getEvaluationDocumentCount(evaluation)
  }, 0)
})

// Note: we intentionally do NOT show a fake "estimated file size". The real
// size depends on document/PDF content the frontend cannot measure, so any
// estimate would be misleading — especially for ZIP exports with document
// content, which could be orders of magnitude larger than a guess.
const includesLargeContent = computed(
  () =>
    exportFormat.value === 'zip' &&
    (includeDocumentContent.value || includeGroundTruthContent.value),
)

const toggleSelectAll = (): void => {
  if (allSelected.value) {
    selectedEvaluations.value = []
  } else {
    selectedEvaluations.value = props.evaluations.map((e) => e.id)
  }
}

const exportReport = async (): Promise<void> => {
  if (selectedEvaluations.value.length === 0) {
    toast.warning('Please select at least one evaluation to export')
    return
  }
  isExporting.value = true
  try {
    const params = new URLSearchParams({
      format: exportFormat.value,
      include_details: includeDetails.value.toString(),
      include_field_details: includeFieldDetails.value.toString(),
      include_errors: includeErrors.value.toString(),
    })
    selectedEvaluations.value.forEach((id) => {
      params.append('evaluation_ids', id.toString())
    })
    if (exportFormat.value === 'zip' || includeDocumentContent.value)
      params.append('include_document_content', includeDocumentContent.value ? 'true' : 'false')
    if (exportFormat.value === 'zip' || includeGroundTruthContent.value)
      params.append(
        'include_ground_truth_content',
        includeGroundTruthContent.value ? 'true' : 'false',
      )

    const timestamp = new Date().toISOString().split('T')[0]
    const extension = exportFormat.value === 'zip' ? 'zip' : exportFormat.value
    const filename = `evaluation_report_${timestamp}.${extension}`

    await downloadFromApi(
      () => evaluationsApi.download(props.projectId, params as unknown as Record<string, unknown>),
      filename,
    )

    toast.success('Report exported')
    emit('close')
  } catch (err: unknown) {
    toast.error(`Failed to export report: ${(err as Error)?.message}`)
    console.error(err)
  } finally {
    isExporting.value = false
  }
}
</script>
