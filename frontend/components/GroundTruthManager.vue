<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 bg-black/30 backdrop-blur-[2px] flex items-center justify-center p-4 z-50"
        @click="emitClose"
      >
        <div
          class="bg-white rounded-xl border border-gray-200 shadow-lg w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden"
          @click.stop
        >
          <!-- HEADER -->
          <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h3 class="text-lg font-semibold text-gray-900">Manage Ground Truth Files</h3>
            <button @click="emitClose" class="text-gray-400 hover:text-gray-500">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- BODY: Files List -->
          <div class="flex-1 overflow-y-auto p-6">
            <div v-if="groundTruthFiles.length === 0" class="text-center py-12 text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>No ground truth files uploaded yet</p>
            </div>

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
                      <span class="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {{ gt.format?.toUpperCase() }}
                      </span>
                      <span
                        v-if="gt.field_mappings?.length"
                        class="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
                      >
                        {{ gt.field_mappings.length }} mappings
                      </span>
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
                      @click="previewGroundTruth(gt)"
                      class="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
                      title="Configure mappings"
                    >
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="3.5" stroke="currentColor" stroke-width="2"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M11 5.055V3a1 1 0 012 0v2.055A7.002 7.002 0 0118.945 11H21a1 1 0 010 2h-2.055A7.002 7.002 0 0113 18.945V21a1 1 0 01-2 0v-2.055A7.002 7.002 0 015.055 13H3a1 1 0 010-2h2.055A7.002 7.002 0 0111 5.055z"/>
                      </svg>
                    </button>
                    <!-- Rename (pencil) -->
                    <button
                      @click="editGroundTruth(gt)"
                      class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-md transition-colors"
                      title="Rename"
                    >
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M16.862 5.487a2.25 2.25 0 013.181 3.181l-9.192 9.193a2 2 0 01-.812.504l-4.054 1.351a.25.25 0 01-.316-.316l1.351-4.054a2 2 0 01.504-.812l9.193-9.192z" />
                      </svg>
                    </button>
                    <!-- Delete (trash) -->
                    <button
                      @click="deleteGroundTruth(gt)"
                      class="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
                      title="Delete"
                    >
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
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
          </div>

          <!-- FOOTER -->
          <div class="px-6 py-4 border-t border-gray-200 flex justify-end">
            <button
              @click="emitClose"
              class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            >
              Close
            </button>
          </div>

          <!-- Edit Modal -->
          <transition name="fade">
            <div
              v-if="editingGroundTruth"
              class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-[60]"
              @click="cancelEdit"
            >
              <div
                class="bg-white rounded-lg shadow-lg w-full max-w-md"
                @click.stop
              >
                <div class="px-6 py-4 border-b border-gray-200">
                  <h4 class="text-lg font-medium text-gray-900">Rename Ground Truth</h4>
                </div>
                <div class="p-6">
                  <label for="edit-name" class="block text-sm font-medium text-gray-700 mb-2">Name</label>
                  <input
                    id="edit-name"
                    v-model="editName"
                    type="text"
                    class="block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                    placeholder="Ground truth file name"
                  />
                </div>
                <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                  <button
                    @click="cancelEdit"
                    class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    @click="saveEdit"
                    class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                    :disabled="isSaving"
                  >
                    <span v-if="isSaving">Saving...</span>
                    <span v-else>Save</span>
                  </button>
                </div>
              </div>
            </div>
          </transition>

          <!-- Preview Modal (GroundTruthPreviewModal) -->
          <GroundTruthPreviewModal
            v-if="previewingGroundTruth"
            :project-id="projectId"
            :ground-truth="previewingGroundTruth"
            @close="closePreview"
            @configured="onMappingConfigured"
          />
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  groundTruthFiles: {
    type: Array,
    required: true
  },
  open: {
    type: Boolean,
    required: true
  }
});
const emit = defineEmits(['close', 'updated']);

const toast = useToast();
const editingGroundTruth = ref(null);
const previewingGroundTruth = ref(null);
const editName = ref('');
const isSaving = ref(false);

// Disable background scroll when modal is open
const stop = watch(() => props.open, (v) => {
  document.body.classList.toggle('overflow-hidden', v);
});
onUnmounted(() => {
  document.body.classList.remove('overflow-hidden');
  stop();
});

// Modal close handler
function emitClose() {
  emit('close');
}

// Edit ground truth
function editGroundTruth(gt) {
  editingGroundTruth.value = gt;
  editName.value = gt.name || '';
}
function cancelEdit() {
  editingGroundTruth.value = null;
  editName.value = '';
}
async function saveEdit() {
  if (!editingGroundTruth.value) return;
  isSaving.value = true;
  try {
    const formData = new FormData();
    formData.append('name', editName.value);

    await api.put(
      `/project/${props.projectId}/groundtruth/${editingGroundTruth.value.id}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    toast.success('Ground truth updated successfully');
    emit('updated');
    cancelEdit();
  } catch (err) {
    toast.error(`Failed to update ground truth: ${err.message}`);
    console.error(err);
  } finally {
    isSaving.value = false;
  }
}

// Preview ground truth
function previewGroundTruth(gt) {
  previewingGroundTruth.value = gt;
}
function closePreview() {
  previewingGroundTruth.value = null;
}

// Delete ground truth
async function deleteGroundTruth(gt) {
  if (!confirm(`Are you sure you want to delete "${gt.name || 'this ground truth file'}"?`)) {
    return;
  }
  try {
    await api.delete(`/project/${props.projectId}/groundtruth/${gt.id}`);
    toast.success('Ground truth deleted successfully');
    emit('updated');
  } catch (err) {
    toast.error(`Failed to delete ground truth: ${err.message}`);
    console.error(err);
  }
}

// Handle mapping configuration
function onMappingConfigured() {
  previewingGroundTruth.value = null;
  emit('updated');
  toast.success('Field mappings configured successfully');
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
