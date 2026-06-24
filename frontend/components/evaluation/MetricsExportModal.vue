<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="$emit('close')"
      >
        <div
          class="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-2xl max-h-[90vh] flex flex-col"
          @click.stop
        >
          <div
            class="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50 rounded-t-2xl"
          >
            <h3 class="text-lg font-semibold text-gray-900">Export Evaluation Report</h3>
            <button
              class="text-gray-400 hover:text-gray-600 transition-colors"
              @click="$emit('close')"
            >
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Fixed height container with scroll -->
          <div class="flex-1 overflow-y-auto p-6 min-h-[600px]">
            <div class="space-y-6">
              <!-- Export format selection -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Export Format</label>
                <div class="grid grid-cols-3 gap-3">
                  <div
                    class="relative flex cursor-pointer rounded-lg border p-4 focus:outline-none"
                    :class="
                      exportFormat === 'csv'
                        ? 'border-blue-600 ring-2 ring-blue-600'
                        : 'border-gray-300'
                    "
                    @click="exportFormat = 'csv'"
                  >
                    <div class="flex h-5 items-center">
                      <input
                        v-model="exportFormat"
                        type="radio"
                        value="csv"
                        class="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                    </div>
                    <div class="ml-3">
                      <div class="text-sm font-medium text-gray-900">CSV</div>
                      <div class="text-sm text-gray-500">Comma-separated values</div>
                    </div>
                  </div>
                  <div
                    class="relative flex cursor-pointer rounded-lg border p-4 focus:outline-none"
                    :class="
                      exportFormat === 'xlsx'
                        ? 'border-blue-600 ring-2 ring-blue-600'
                        : 'border-gray-300'
                    "
                    @click="exportFormat = 'xlsx'"
                  >
                    <div class="flex h-5 items-center">
                      <input
                        v-model="exportFormat"
                        type="radio"
                        value="xlsx"
                        class="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                    </div>
                    <div class="ml-3">
                      <div class="text-sm font-medium text-gray-900">Excel</div>
                      <div class="text-sm text-gray-500">Excel spreadsheet</div>
                    </div>
                  </div>
                  <div
                    class="relative flex cursor-pointer rounded-lg border p-4 focus:outline-none"
                    :class="
                      exportFormat === 'zip'
                        ? 'border-blue-600 ring-2 ring-blue-600'
                        : 'border-gray-300'
                    "
                    @click="exportFormat = 'zip'"
                  >
                    <div class="flex h-5 items-center">
                      <input
                        v-model="exportFormat"
                        type="radio"
                        value="zip"
                        class="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                    </div>
                    <div class="ml-3">
                      <div class="text-sm font-medium text-gray-900">ZIP</div>
                      <div class="text-sm text-gray-500">ZIP archive (advanced)</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Evaluation selection -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2"
                  >Select Evaluations</label
                >
                <div class="max-h-64 overflow-y-auto border border-gray-200 rounded-md">
                  <div class="p-3 border-b border-gray-200 bg-gray-50">
                    <label class="flex items-center">
                      <input
                        type="checkbox"
                        :checked="allSelected"
                        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        @change="toggleSelectAll"
                      />
                      <span class="ml-2 text-sm font-medium text-gray-700">Select All</span>
                    </label>
                  </div>
                  <div class="divide-y divide-gray-200">
                    <div
                      v-for="evaluation in evaluations"
                      :key="evaluation.id"
                      class="p-3 hover:bg-gray-50"
                    >
                      <label class="flex items-center">
                        <input
                          v-model="selectedEvaluations"
                          type="checkbox"
                          :value="evaluation.id"
                          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <div class="ml-3 flex-1">
                          <div class="text-sm font-medium text-gray-900">
                            Trial #{{ evaluation.trial_id }}
                          </div>
                          <div class="text-sm text-gray-500">
                            {{ (evaluation.metrics.accuracy * 100).toFixed(1) }}% accuracy •
                            {{ evaluation.document_metrics?.length || 0 }} documents •
                            {{ formatDate(evaluation.created_at) }}
                          </div>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
                <div v-if="selectedEvaluations.length === 0" class="mt-2 text-sm text-red-600">
                  Please select at least one evaluation to export.
                </div>
              </div>

              <!-- Export options -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-3">Export Options</label>
                <div class="space-y-3">
                  <div class="flex items-center">
                    <input
                      id="include-details"
                      v-model="includeDetails"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label for="include-details" class="ml-2 text-sm text-gray-700">
                      Include detailed document-level metrics
                    </label>
                  </div>
                  <div class="flex items-center">
                    <input
                      id="include-field-details"
                      v-model="includeFieldDetails"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label for="include-field-details" class="ml-2 text-sm text-gray-700">
                      Include field-by-field comparison data
                    </label>
                  </div>
                  <div class="flex items-center">
                    <input
                      id="include-errors"
                      v-model="includeErrors"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label for="include-errors" class="ml-2 text-sm text-gray-700">
                      Include error analysis and examples
                    </label>
                  </div>
                  <div v-if="exportFormat === 'zip'" class="flex items-center">
                    <input
                      id="include-document-content"
                      v-model="includeDocumentContent"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label for="include-document-content" class="ml-2 text-sm text-gray-700">
                      Include document content (in docs/)
                    </label>
                  </div>
                  <div v-if="exportFormat === 'zip'" class="flex items-center">
                    <input
                      id="include-gt-content"
                      v-model="includeGroundTruthContent"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label for="include-gt-content" class="ml-2 text-sm text-gray-700">
                      Include ground truth content (in docs/)
                    </label>
                  </div>
                </div>
              </div>

              <!-- Preview of export content -->
              <div v-if="selectedEvaluations.length > 0" class="bg-gray-50 rounded-lg p-4">
                <h4 class="text-sm font-medium text-gray-700 mb-2">Export Preview</h4>
                <div class="text-sm text-gray-600 space-y-1">
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
                  <div class="text-xs text-gray-500 mt-2">
                    Estimated file size: {{ estimatedFileSize }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3 bg-gray-50 rounded-b-2xl"
          >
            <button
              type="button"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              :disabled="isExporting || selectedEvaluations.length === 0"
              @click="exportReport"
            >
              <span v-if="isExporting" class="flex items-center">
                <svg
                  class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Exporting...
              </span>
              <span v-else class="flex items-center">
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Export Report
              </span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'
import { evaluationsApi } from '@/services/evaluationsApi'
import { formatDate } from '@/utils/formatters'
import { useToast } from 'vue-toastification'
import { useScrollLock } from '@/composables/useScrollLock'
import { useFileDownload } from '@/composables/useFileDownload'

useScrollLock({ autoLock: true })

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
  evaluations: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['close'])
const toast = useToast()
const { downloadFromApi } = useFileDownload()
const isExporting = ref(false)

const exportFormat = ref('csv')
const selectedEvaluations = ref([])
const includeDetails = ref(true)
const includeFieldDetails = ref(false)
const includeErrors = ref(false)
const includeDocumentContent = ref(false)
const includeGroundTruthContent = ref(false)

const allSelected = computed(() => {
  return (
    props.evaluations.length > 0 && selectedEvaluations.value.length === props.evaluations.length
  )
})

const totalDocuments = computed(() => {
  return selectedEvaluations.value.reduce((total, evalId) => {
    const evaluation = props.evaluations.find((e) => e.id === evalId)
    return total + (evaluation?.document_metrics?.length || 0)
  }, 0)
})

const estimatedFileSize = computed(() => {
  let baseSize = selectedEvaluations.value.length * 2
  if (includeDetails.value) baseSize += totalDocuments.value * 1
  if (includeFieldDetails.value) baseSize += totalDocuments.value * 5
  if (includeErrors.value) baseSize += totalDocuments.value * 2
  if (exportFormat.value === 'zip') {
    if (includeDocumentContent.value) baseSize += totalDocuments.value * 30
    if (includeGroundTruthContent.value) baseSize += totalDocuments.value * 15
  }
  if (baseSize < 1) return '< 1 KB'
  if (baseSize < 1024) return `${Math.round(baseSize)} KB`
  return `${Math.round((baseSize / 1024) * 10) / 10} MB`
})

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedEvaluations.value = []
  } else {
    selectedEvaluations.value = props.evaluations.map((e) => e.id)
  }
}

const exportReport = async () => {
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

    await downloadFromApi(() => evaluationsApi.download(props.projectId, params), filename)

    toast.success('Report exported successfully')
    emit('close')
  } catch (err) {
    toast.error(`Failed to export report: ${err.message}`)
    console.error(err)
  } finally {
    isExporting.value = false
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
