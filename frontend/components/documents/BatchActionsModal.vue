<template>
  <BaseModal :open="open" size="lg" @close="$emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-content">
          {{ actionTitle }}
        </h3>
        <p class="mt-1 text-sm text-content-muted">
          {{ documents.length }} {{ entityLabel }}{{ documents.length !== 1 ? 's' : '' }} selected
        </p>
      </div>
    </template>

    <!-- Reprocess Action -->
    <div v-if="action === 'reprocess'" class="space-y-4">
      <div class="flex items-center">
        <input v-model="forceReprocess" type="checkbox" :class="checkboxClass" />
        <label class="ml-2 text-sm text-content-muted">
          Force reprocess (ignore existing results)
        </label>
      </div>
    </div>

    <!-- Export Action -->
    <div v-else-if="action === 'export'" class="space-y-4">
      <p class="text-sm text-content-muted">Choose export format and options:</p>
      <div>
        <label :class="labelClass"> Export Format </label>
        <select v-model="exportFormat" :class="selectClass">
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="txt">Plain Text</option>
          <option value="pdf">PDF (with text layer)</option>
        </select>
      </div>
      <div class="space-y-2">
        <label class="flex items-center">
          <input v-model="includeMetadata" type="checkbox" :class="checkboxClass" />
          <span class="ml-2 text-sm text-content-muted">Include metadata</span>
        </label>
        <label class="flex items-center">
          <input v-model="includePreprocessingInfo" type="checkbox" :class="checkboxClass" />
          <span class="ml-2 text-sm text-content-muted">Include preprocessing information</span>
        </label>
      </div>
    </div>

    <!-- Delete Action -->
    <div v-else-if="action === 'delete'" class="space-y-4">
      <Callout variant="danger" title="Warning: This action cannot be undone">
        <p class="mt-1">{{ deleteWarningText }}</p>
      </Callout>
      <div class="flex items-center">
        <input
          v-model="confirmDelete"
          type="checkbox"
          :class="[checkboxClass, 'text-red-600 focus:ring-red-500']"
        />
        <label class="ml-2 text-sm text-content-muted">
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

<script setup lang="ts">
import { ref, computed } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { checkboxClass, selectClass, labelClass } from '@/utils/formStyles'
import { documentsApi } from '@/services/documentsApi'
import { trialsApi } from '@/services/trialsApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import type { PreprocessingTaskCreate } from '@/types'

interface Props {
  open: boolean
  action: string
  documents: number[]
  projectId: string | number
  // 'documents' (default) operates on documents via documentsApi;
  // 'trials' operates on trials via trialsApi (delete only).
  mode?: 'documents' | 'trials'
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'documents',
})

const emit = defineEmits<{
  close: []
  complete: []
  deleted: [ids: number[]]
}>()
const toast = useToast()

// Form state
const forceReprocess = ref<boolean>(false)
const exportFormat = ref<string>('json')
const includeMetadata = ref<boolean>(true)
const includePreprocessingInfo = ref<boolean>(true)
const confirmDelete = ref<boolean>(false)
const isProcessing = ref<boolean>(false)

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
const performAction = async (): Promise<void> => {
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

const reprocessDocuments = async (): Promise<void> => {
  // `props.documents` are *document* IDs, but a preprocessing task needs the
  // underlying *file* IDs. Resolve each selected document to its
  // original_file_id (deduped — row-by-row CSVs share one file).
  const fileIds = new Set<number>()
  for (const docId of props.documents) {
    try {
      const { data } = await documentsApi.get(props.projectId, docId)
      if (data?.original_file_id) fileIds.add(data.original_file_id)
    } catch (error) {
      console.error(`Failed to resolve document #${docId} to a file:`, error)
    }
  }
  if (fileIds.size === 0) {
    toast.error('Could not resolve the selected documents to any files.')
    return
  }
  const taskData: PreprocessingTaskCreate = {
    inline_config: {
      name: `Reprocess ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
      additional_settings: {},
    },
    file_ids: Array.from(fileIds),
    force_reprocess: forceReprocess.value,
  }
  await preprocessingApi.create(props.projectId, taskData)
  toast.success(
    `Reprocessing task started for ${fileIds.size} file${fileIds.size !== 1 ? 's' : ''}`,
  )
}

const exportDocuments = async (): Promise<void> => {
  toast.info('Export functionality would be implemented here')
}

interface FailedDoc {
  docId: number
  error: string
}

const deleteDocuments = async (): Promise<number[]> => {
  const failedDocs: FailedDoc[] = []
  const successDocs: number[] = []
  const deleteFn = props.mode === 'trials' ? trialsApi.delete : documentsApi.delete
  const label = entityLabel.value

  for (const docId of props.documents) {
    try {
      await deleteFn(props.projectId, docId)
      successDocs.push(docId)
    } catch (error) {
      failedDocs.push({
        docId,
        error: extractErrorMessage(error, `Failed to delete ${label}`),
      })
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
    // One summary toast instead of one per failed item. Surface the first
    // error verbatim, note how many more, and add the document-set hint if any
    // failure was caused by a set membership.
    const first = failedDocs[0]
    const more = failedDocs.length > 1 ? ` (+${failedDocs.length - 1} more)` : ''
    const hint = failedDocs.some((f) => f.error.includes('document sets'))
      ? ' Go to the Document Groups tab to manage.'
      : ''
    toast.error(
      `Failed to delete ${failedDocs.length} ${label}${failedDocs.length !== 1 ? 's' : ''}: ` +
        `#${first.docId} — ${first.error}${more}.${hint}`,
    )
    // Don't throw - close modal anyway but parent will know what was deleted
  }

  return successDocs
}
</script>
