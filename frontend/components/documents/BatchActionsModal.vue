<template>
  <BaseModal :open="open" size="lg" @close="$emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
          {{ actionTitle }}
        </h3>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {{ documents.length }} {{ entityLabel }}{{ documents.length !== 1 ? 's' : '' }} selected
        </p>
      </div>
    </template>

    <!-- Reprocess Action -->
    <div v-if="action === 'reprocess'" class="space-y-4">
      <div class="flex items-center">
        <input
          v-model="forceReprocess"
          type="checkbox"
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
        />
        <label class="ml-2 text-sm text-slate-700 dark:text-slate-300">
          Force reprocess (ignore existing results)
        </label>
      </div>
    </div>

    <!-- Export Action -->
    <div v-else-if="action === 'export'" class="space-y-4">
      <p class="text-sm text-slate-600 dark:text-slate-400">Choose export format and options:</p>
      <div>
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
          Export Format
        </label>
        <select
          v-model="exportFormat"
          class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="txt">Plain Text</option>
          <option value="pdf">PDF (with text layer)</option>
        </select>
      </div>
      <div class="space-y-2">
        <label class="flex items-center">
          <input
            v-model="includeMetadata"
            type="checkbox"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
          />
          <span class="ml-2 text-sm text-slate-700 dark:text-slate-300">Include metadata</span>
        </label>
        <label class="flex items-center">
          <input
            v-model="includePreprocessingInfo"
            type="checkbox"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
          />
          <span class="ml-2 text-sm text-slate-700 dark:text-slate-300"
            >Include preprocessing information</span
          >
        </label>
      </div>
    </div>

    <!-- Delete Action -->
    <div v-else-if="action === 'delete'" class="space-y-4">
      <div
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4"
      >
        <div class="flex">
          <AlertTriangle class="h-5 w-5 text-red-400 flex-shrink-0" />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800 dark:text-red-300">
              Warning: This action cannot be undone
            </h3>
            <p class="mt-1 text-sm text-red-700 dark:text-red-400">
              {{ deleteWarningText }}
            </p>
          </div>
        </div>
      </div>
      <div class="flex items-center">
        <input
          v-model="confirmDelete"
          type="checkbox"
          class="h-4 w-4 text-red-600 focus:ring-red-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
        />
        <label class="ml-2 text-sm text-slate-700 dark:text-slate-300">
          I understand that this action is permanent
        </label>
      </div>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">Cancel</BaseButton>
      <BaseButton
        :variant="action === 'delete' ? 'danger' : 'primary'"
        :disabled="!canPerformAction"
        :loading="isProcessing"
        @click="performAction"
      >
        {{ isProcessing ? 'Processing...' : actionButtonText }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed } from 'vue'
import { AlertTriangle } from '@lucide/vue'
import { documentsApi } from '@/services/documentsApi'
import { trialsApi } from '@/services/trialsApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  open: { type: Boolean, required: true },
  action: { type: String, required: true },
  documents: { type: Array, required: true },
  projectId: { type: [String, Number], required: true },
  // 'documents' (default) operates on documents via documentsApi;
  // 'trials' operates on trials via trialsApi (delete only).
  mode: {
    type: String,
    default: 'documents',
    validator: (v) => v === 'documents' || v === 'trials',
  },
})

const emit = defineEmits(['close', 'complete', 'deleted'])
const toast = useToast()

// Form state
const forceReprocess = ref(false)
const exportFormat = ref('json')
const includeMetadata = ref(true)
const includePreprocessingInfo = ref(true)
const confirmDelete = ref(false)
const isProcessing = ref(false)

// Computed
const entityLabel = computed(() => (props.mode === 'trials' ? 'trial' : 'document'))

const deleteWarningText = computed(() =>
  props.mode === 'trials'
    ? 'The selected trials and their results will be permanently deleted.'
    : 'The selected documents and their preprocessing results will be permanently deleted.',
)

const actionTitle = computed(() => {
  const entity = entityLabel.value
  const capEntity = entity.charAt(0).toUpperCase() + entity.slice(1)
  switch (props.action) {
    case 'reprocess':
      return `Reprocess ${capEntity}s`
    case 'export':
      return `Export ${capEntity}s`
    case 'delete':
      return `Delete ${capEntity}s`
    default:
      return 'Batch Action'
  }
})

const actionButtonText = computed(() => {
  const entity = entityLabel.value
  const capEntity = entity.charAt(0).toUpperCase() + entity.slice(1)
  switch (props.action) {
    case 'reprocess':
      return 'Start Reprocessing'
    case 'export':
      return 'Export'
    case 'delete':
      return `Delete ${capEntity}s`
    default:
      return 'Confirm'
  }
})

const canPerformAction = computed(() => {
  if (isProcessing.value) return false
  switch (props.action) {
    case 'reprocess':
      return true
    case 'export':
      return true
    case 'delete':
      return confirmDelete.value
    default:
      return false
  }
})

// Methods
const performAction = async () => {
  if (!canPerformAction.value) return
  isProcessing.value = true
  try {
    switch (props.action) {
      case 'reprocess':
        await reprocessDocuments()
        break
      case 'export':
        await exportDocuments()
        break
      case 'delete':
        await deleteDocuments()
        // Always close modal after delete - specific errors already shown
        emit('complete')
        return
    }
    emit('complete')
  } catch (error) {
    // Don't show generic error for delete - specific errors already shown
    if (props.action !== 'delete') {
      toast.error(`Failed to ${props.action} ${entityLabel.value}s`)
      console.error(error)
    }
  } finally {
    isProcessing.value = false
    // Close modal after action completes (for delete, this happens after all attempts)
    if (props.action === 'delete') {
      emit('close')
    }
  }
}

const reprocessDocuments = async () => {
  const fileIds = props.documents
  const taskData = {
    inline_config: {
      name: `Reprocess ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
      additional_settings: {},
    },
    file_ids: fileIds,
    force_reprocess: forceReprocess.value,
  }
  await preprocessingApi.create(props.projectId, taskData)
  toast.success('Reprocessing task started')
}

const exportDocuments = async () => {
  toast.info('Export functionality would be implemented here')
}

const deleteDocuments = async () => {
  const failedDocs = []
  const successDocs = []
  const deleteFn = props.mode === 'trials' ? trialsApi.delete : documentsApi.delete
  const label = entityLabel.value

  for (const docId of props.documents) {
    try {
      await deleteFn(props.projectId, docId)
      successDocs.push(docId)
    } catch (error) {
      const errorMsg = extractErrorMessage(error, `Failed to delete ${label}`)
      failedDocs.push({ docId, error: errorMsg })

      // Show specific error for each failed item
      if (errorMsg.includes('document sets')) {
        toast.error(
          `${label.charAt(0).toUpperCase() + label.slice(1)} #${docId}: ${errorMsg} Go to Document Groups tab to manage.`,
        )
      } else if (errorMsg.includes('trial')) {
        toast.error(`${label.charAt(0).toUpperCase() + label.slice(1)} #${docId}: ${errorMsg}`)
      } else if (errorMsg.includes('trial result')) {
        toast.error(`${label.charAt(0).toUpperCase() + label.slice(1)} #${docId}: ${errorMsg}`)
      } else if (errorMsg.includes('evaluation')) {
        toast.error(`${label.charAt(0).toUpperCase() + label.slice(1)} #${docId}: ${errorMsg}`)
      } else {
        toast.error(`${label.charAt(0).toUpperCase() + label.slice(1)} #${docId}: ${errorMsg}`)
      }
    }
  }

  const successCount = successDocs.length
  if (successCount > 0) {
    toast.success(`${successCount} ${label}${successCount !== 1 ? 's' : ''} deleted successfully`)
    // Emit successfully deleted IDs so parent can update selection
    emit('deleted', successDocs)
  }

  if (failedDocs.length > 0) {
    console.error(`Failed to delete ${label}s:`, failedDocs)
    // Don't throw - close modal anyway but parent will know what was deleted
  }

  return successDocs
}
</script>
