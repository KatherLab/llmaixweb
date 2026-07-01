<template>
  <BaseModal :open="open" title="Manage Ground Truth Files" size="xl" @close="emitClose">
    <template #header>
      <div>
        <h3 class="text-lg font-medium text-slate-900 dark:text-white">
          Manage Ground Truth Files
        </h3>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Ground truth files contain the correct extracted values you compare trial results against.
          Configure field mappings to link each ground-truth column to a schema field.
        </p>
      </div>
    </template>

    <!-- BODY: Files List -->
    <EmptyState
      v-if="groundTruthFiles.length === 0"
      title="No ground truth files uploaded yet"
      description="Upload a file with the correct values (CSV, XLSX, or JSON) to start evaluating trial accuracy."
    />

    <div v-else class="space-y-4">
      <div
        v-for="(gt, index) in groundTruthFiles"
        :key="gt.id"
        class="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h4 class="font-medium text-slate-900 dark:text-white">
                {{ gt.name || `Ground Truth #${index + 1}` }}
              </h4>
              <StatusBadge color="blue" class="px-2 py-1 font-medium">{{
                gt.format?.toUpperCase()
              }}</StatusBadge>
              <StatusBadge
                v-if="gt.field_mappings?.length"
                color="green"
                class="px-2 py-1 font-medium"
                >{{ gt.field_mappings.length }} mappings</StatusBadge
              >
            </div>
            <div class="text-xs text-slate-600 dark:text-slate-400 flex flex-wrap gap-4">
              <span>Created: {{ formatDate(gt.created_at) }}</span>
              <span v-if="gt.updated_at !== gt.created_at">
                Updated: {{ formatDate(gt.updated_at) }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <!-- Configure mappings -->
            <button
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20 rounded-md transition-colors"
              title="Configure field mappings"
              @click="previewGroundTruth(gt)"
            >
              <Settings class="w-4 h-4" />
              Configure mappings
            </button>
            <!-- Rename (pencil) -->
            <button
              class="p-2 text-slate-600 hover:text-slate-800 dark:hover:text-white hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-700 rounded-md transition-colors"
              title="Rename"
              @click="editGroundTruth(gt)"
            >
              <Pencil class="w-5 h-5" />
            </button>
            <!-- Delete (trash) -->
            <button
              class="p-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
              title="Delete"
              @click="deleteGroundTruth(gt)"
            >
              <Trash2 class="w-5 h-5" />
            </button>
          </div>
        </div>
        <!-- Field mappings preview -->
        <div
          v-if="gt.field_mappings?.length"
          class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700"
        >
          <h5 class="text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Configured Field Mappings
          </h5>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div
              v-for="mapping in gt.field_mappings.slice(0, 6)"
              :key="mapping.id"
              class="bg-slate-50 dark:bg-slate-700/50 px-2 py-1 rounded flex justify-between"
            >
              <span class="font-mono text-blue-800 dark:text-blue-300">{{
                mapping.schema_field
              }}</span>
              <span class="text-slate-500 dark:text-slate-400"
                >→ {{ mapping.ground_truth_field }}</span
              >
            </div>
            <div
              v-if="gt.field_mappings.length > 6"
              class="bg-slate-50 dark:bg-slate-700/50 px-2 py-1 rounded text-center text-slate-500 dark:text-slate-400"
            >
              +{{ gt.field_mappings.length - 6 }} more...
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton @click="emitClose">Close</BaseButton>
    </template>
  </BaseModal>

  <!-- Edit Modal -->
  <BaseModal :open="!!editingGroundTruth" title="Rename Ground Truth" size="sm" @close="cancelEdit">
    <label for="edit-name" :class="labelClass">Name</label>
    <input
      id="edit-name"
      v-model="editName"
      type="text"
      :class="inputClass"
      maxlength="100"
      placeholder="Ground truth file name"
    />
    <template #footer>
      <BaseButton variant="secondary" @click="cancelEdit">Cancel</BaseButton>
      <BaseButton :disabled="isSaving" :loading="isSaving" @click="saveEdit">
        <span v-if="isSaving">Saving...</span>
        <span v-else>Save</span>
      </BaseButton>
    </template>
  </BaseModal>

  <!-- Preview Modal (GroundTruthPreviewModal) -->
  <GroundTruthPreviewModal
    :open="showPreview"
    :project-id="projectId"
    :ground-truth="previewingGroundTruth"
    @close="closePreview"
    @configured="onMappingConfigured"
  />

  <!-- Delete ground truth confirmation -->
  <ConfirmationDialog
    :open="showDeleteConfirm"
    title="Delete ground truth?"
    :message="`Are you sure you want to delete “${pendingDelete?.name || 'this ground truth file'}”? This action cannot be undone.`"
    confirm-text="Delete"
    cancel-text="Cancel"
    confirm-variant="danger"
    @confirm="confirmDelete"
    @cancel="showDeleteConfirm = false"
  />
</template>

<script setup>
import { ref } from 'vue'
import { Pencil, Settings, Trash2 } from '@lucide/vue'
import { groundtruthApi } from '@/services/groundtruthApi'
import { formatDate } from '@/utils/formatters'
import { inputClass, labelClass } from '@/utils/formStyles'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
  groundTruthFiles: {
    type: Array,
    required: true,
  },
  open: {
    type: Boolean,
    required: true,
  },
})
const emit = defineEmits(['close', 'updated'])

const toast = useToast()
const editingGroundTruth = ref(null)
const previewingGroundTruth = ref(null)
const showPreview = ref(false)
const editName = ref('')
const isSaving = ref(false)

// Modal close handler
function emitClose() {
  emit('close')
}

// Edit ground truth
function editGroundTruth(gt) {
  editingGroundTruth.value = gt
  editName.value = gt.name || ''
}
function cancelEdit() {
  editingGroundTruth.value = null
  editName.value = ''
}
async function saveEdit() {
  if (!editingGroundTruth.value) return
  isSaving.value = true
  try {
    const formData = new FormData()
    formData.append('name', editName.value)

    await groundtruthApi.update(props.projectId, editingGroundTruth.value.id, formData)
    toast.success('Ground truth updated successfully')
    emit('updated')
    cancelEdit()
  } catch (err) {
    toast.error(`Failed to update ground truth: ${err.message}`)
    console.error(err)
  } finally {
    isSaving.value = false
  }
}

// Preview ground truth
function previewGroundTruth(gt) {
  previewingGroundTruth.value = gt
  showPreview.value = true
}
function closePreview() {
  showPreview.value = false
}

// Delete ground truth (confirmed via ConfirmationDialog)
const showDeleteConfirm = ref(false)
const pendingDelete = ref(null)
function deleteGroundTruth(gt) {
  pendingDelete.value = gt
  showDeleteConfirm.value = true
}
async function confirmDelete() {
  const gt = pendingDelete.value
  showDeleteConfirm.value = false
  pendingDelete.value = null
  if (!gt) return
  try {
    await groundtruthApi.delete(props.projectId, gt.id)
    toast.success('Ground truth deleted successfully')
    emit('updated')
  } catch (err) {
    toast.error(`Failed to delete ground truth: ${err.message}`)
    console.error(err)
  }
}

// Handle mapping configuration
function onMappingConfigured() {
  showPreview.value = false
  emit('updated')
  toast.success('Field mappings configured successfully')
}
</script>
