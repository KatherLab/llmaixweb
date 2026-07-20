<template>
  <BaseModal
    :open="open"
    :title="$t('evaluation.export.title')"
    size="lg"
    body-class="p-6"
    @close="$emit('close')"
  >
    <div class="space-y-6">
      <!-- Export format selection -->
      <div>
        <label :class="labelClass">{{ $t('evaluation.export.format_label') }}</label>
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
              <div class="text-sm text-content-subtle">
                {{ $t('evaluation.export.csv_desc') }}
              </div>
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
              <div class="text-sm text-content-subtle">
                {{ $t('evaluation.export.xlsx_desc') }}
              </div>
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
              <div class="text-sm text-content-subtle">
                {{ $t('evaluation.export.zip_desc') }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Evaluation selection -->
      <div>
        <label :class="labelClass">{{ $t('evaluation.export.select_label') }}</label>
        <p v-if="groundTruthName" class="text-xs text-content-subtle mb-2">
          {{ $t('evaluation.export.showing_for_gt', { name: groundTruthName }) }}
        </p>
        <div class="max-h-64 overflow-y-auto border border-default rounded-card">
          <div class="p-3 border-b border-default bg-surface-muted">
            <label class="flex items-center">
              <input
                type="checkbox"
                :checked="allSelected"
                :class="checkboxClass"
                @change="toggleSelectAll"
              />
              <span class="ml-2 text-sm font-medium text-content-muted">{{
                $t('evaluation.export.select_all')
              }}</span>
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
                    {{
                      $t('evaluation.export.accuracy_label', {
                        value: getEvaluationAccuracyPct(evaluation),
                      })
                    }}
                    •
                    {{
                      $t(
                        'evaluation.export.documents_label',
                        { count: getEvaluationDocumentCount(evaluation) },
                        getEvaluationDocumentCount(evaluation),
                      )
                    }}
                    •
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
          {{ $t('evaluation.export.select_one') }}
        </div>
      </div>

      <!-- Export options -->
      <div>
        <label :class="labelClass">{{ $t('evaluation.export.options_label') }}</label>
        <div class="space-y-3">
          <div class="flex items-center">
            <input
              id="include-details"
              v-model="includeDetails"
              type="checkbox"
              :class="checkboxClass"
            />
            <label for="include-details" class="ml-2 text-sm text-content-muted">
              {{ $t('evaluation.export.opt_details') }}
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
              {{ $t('evaluation.export.opt_field_details') }}
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
              {{ $t('evaluation.export.opt_errors') }}
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
              {{ $t('evaluation.export.opt_document_content') }}
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
              {{ $t('evaluation.export.opt_gt_content') }}
            </label>
          </div>
        </div>
      </div>

      <!-- Preview of export content -->
      <div v-if="selectedEvaluations.length > 0" class="bg-surface-muted rounded-card p-4">
        <h4 class="text-sm font-medium text-content-muted mb-2">
          {{ $t('evaluation.export.preview_title') }}
        </h4>
        <div class="text-sm text-content-muted space-y-1">
          <div>
            •
            {{
              $t(
                'evaluation.export.preview_evaluations',
                { count: selectedEvaluations.length },
                selectedEvaluations.length,
              )
            }}
          </div>
          <div>
            • {{ $t('evaluation.export.preview_total_documents', { count: totalDocuments }) }}
          </div>
          <div v-if="includeDetails">• {{ $t('evaluation.export.preview_details') }}</div>
          <div v-if="includeFieldDetails">
            • {{ $t('evaluation.export.preview_field_details') }}
          </div>
          <div v-if="includeErrors">• {{ $t('evaluation.export.preview_errors') }}</div>
          <div v-if="exportFormat === 'zip' && includeDocumentContent">
            • {{ $t('evaluation.export.preview_document_content') }}
          </div>
          <div v-if="exportFormat === 'zip' && includeGroundTruthContent">
            • {{ $t('evaluation.export.preview_gt_content') }}
          </div>
          <div v-if="includesLargeContent" class="text-xs text-amber-600 dark:text-amber-400 mt-2">
            {{ $t('evaluation.export.large_warning') }}
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">
        {{ $t('evaluation.export.cancel') }}
      </BaseButton>
      <BaseButton
        :loading="isExporting"
        :disabled="isExporting || selectedEvaluations.length === 0"
        @click="exportReport"
      >
        <span v-if="!isExporting" class="flex items-center gap-1.5">
          <Upload class="w-4 h-4" />
          {{ $t('evaluation.export.export_button') }}
        </span>
        <span v-else>{{ $t('evaluation.export.exporting') }}</span>
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
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
  /** Evaluation ids to pre-check when the modal opens (e.g. the evaluation
   * whose analysis page the export was launched from). */
  preselectedIds?: number[]
  /** Name of the ground truth the listed evaluations are scoped to. */
  groundTruthName?: string
}

const props = withDefaults(defineProps<Props>(), {
  preselectedIds: () => [],
  groundTruthName: '',
})

const emit = defineEmits<{ close: [] }>()
const { t } = useI18n({ useScope: 'global' })
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

// On open, apply the caller's preselection (only ids that are actually in the
// listed evaluations). On close, reset export selections so a reopen starts
// fresh (component stays mounted to enable the close transition).
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      selectedEvaluations.value = props.preselectedIds.filter((id) =>
        props.evaluations.some((e) => e.id === id),
      )
    } else {
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
    toast.warning(t('evaluation.export.select_one_toast'))
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

    toast.success(t('evaluation.export.export_success'))
    emit('close')
  } catch (err: unknown) {
    toast.error(t('evaluation.export.export_failed', { error: (err as Error)?.message }))
    console.error(err)
  } finally {
    isExporting.value = false
  }
}
</script>
