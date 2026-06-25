<template>
  <BaseModal
    :open="open"
    title="Manage Ground Truth Files"
    size="xl"
    panel-class="rounded-xl shadow-lg"
    @close="emitClose"
  >
    <!-- BODY: Files List -->
    <EmptyState v-if="groundTruthFiles.length === 0" title="No ground truth files uploaded yet" />

    <div v-else class="space-y-4">
      <div
        v-for="(gt, index) in groundTruthFiles"
        :key="gt.id"
        class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h4 class="font-medium text-gray-900">
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
            <div class="text-xs text-gray-600 flex flex-wrap gap-4">
              <span>Created: {{ formatDate(gt.created_at) }}</span>
              <span v-if="gt.updated_at !== gt.created_at">
                Updated: {{ formatDate(gt.updated_at) }}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <!-- Configure mappings (wrench icon) -->
            <button
              class="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
              title="Configure mappings"
              @click="previewGroundTruth(gt)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3.5" stroke="currentColor" stroke-width="2" />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M11 5.055V3a1 1 0 012 0v2.055A7.002 7.002 0 0118.945 11H21a1 1 0 010 2h-2.055A7.002 7.002 0 0113 18.945V21a1 1 0 01-2 0v-2.055A7.002 7.002 0 015.055 13H3a1 1 0 010-2h2.055A7.002 7.002 0 0111 5.055z"
                />
              </svg>
            </button>
            <!-- Rename (pencil) -->
            <button
              class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-md transition-colors"
              title="Rename"
              @click="editGroundTruth(gt)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16.862 5.487a2.25 2.25 0 013.181 3.181l-9.192 9.193a2 2 0 01-.812.504l-4.054 1.351a.25.25 0 01-.316-.316l1.351-4.054a2 2 0 01.504-.812l9.193-9.192z"
                />
              </svg>
            </button>
            <!-- Delete (trash) -->
            <button
              class="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
              title="Delete"
              @click="deleteGroundTruth(gt)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>
        <!-- Field mappings preview -->
        <div v-if="gt.field_mappings?.length" class="mt-3 pt-3 border-t border-gray-100">
          <h5 class="text-xs font-medium text-gray-700 mb-1">Configured Field Mappings</h5>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div
              v-for="mapping in gt.field_mappings.slice(0, 6)"
              :key="mapping.id"
              class="bg-gray-50 px-2 py-1 rounded flex justify-between"
            >
              <span class="font-mono text-blue-800">{{ mapping.schema_field }}</span>
              <span class="text-gray-500">→ {{ mapping.ground_truth_field }}</span>
            </div>
            <div
              v-if="gt.field_mappings.length > 6"
              class="bg-gray-50 px-2 py-1 rounded text-center text-gray-500"
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
    <label for="edit-name" class="block text-sm font-medium text-gray-700 mb-2">Name</label>
    <input
      id="edit-name"
      v-model="editName"
      type="text"
      class="block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
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
    v-if="previewingGroundTruth"
    :project-id="projectId"
    :ground-truth="previewingGroundTruth"
    @close="closePreview"
    @configured="onMappingConfigured"
  />
</template>

<script setup>
import { ref } from 'vue'
import { groundtruthApi } from '@/services/groundtruthApi'
import { formatDate } from '@/utils/formatters'
import { useToast } from 'vue-toastification'
import BaseModal from '@/components/common/BaseModal.vue'
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
}
function closePreview() {
  previewingGroundTruth.value = null
}

// Delete ground truth
async function deleteGroundTruth(gt) {
  if (!confirm(`Are you sure you want to delete "${gt.name || 'this ground truth file'}"?`)) {
    return
  }
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
  previewingGroundTruth.value = null
  emit('updated')
  toast.success('Field mappings configured successfully')
}
</script>
