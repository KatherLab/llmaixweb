<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Evaluate Trial</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
            <div class="flex">
              <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-yellow-800">Schema-specific field mappings required</h3>
                <p class="mt-1 text-sm text-yellow-700">
                  Each trial requires field mappings for its specific schema. Trials without mappings will be grayed out.
                  <button @click="showMappingModal = true" class="underline hover:no-underline">
                    Configure mappings
                  </button>
                </p>
              </div>
            </div>
          </div>

          <div v-if="isLoading" class="text-center py-8">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading trials...</p>
          </div>

          <div v-else-if="trials.length === 0" class="text-center py-8 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>No trials available for evaluation</p>
          </div>

          <div v-else>
            <div class="mb-4">
              <h4 class="font-medium text-gray-900 mb-2">Select a trial to evaluate</h4>
              <p class="text-sm text-gray-600">Choose from completed trials to compare against your ground truth data.</p>
            </div>

            <div class="space-y-3 max-h-96 overflow-y-auto">
              <div
                v-for="trial in availableTrials"
                :key="trial.id"
                class="border rounded-lg p-4 transition-colors"
                :class="{
                  'border-blue-500 bg-blue-50 cursor-pointer hover:bg-blue-100': trial.hasMappings && selectedTrial?.id === trial.id,
                  'border-gray-300 cursor-pointer hover:bg-gray-50': trial.hasMappings && selectedTrial?.id !== trial.id,
                  'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60': !trial.hasMappings
                }"
                @click="trial.hasMappings ? selectTrial(trial) : null"
              >
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                      <h5 class="font-medium text-gray-900">Trial #{{ trial.id }}</h5>
                      <span class="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {{ trial.status }}
                      </span>
                      <!-- Mapping status indicator -->
                      <span
                        v-if="trial.hasMappings"
                        class="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        Mappings Ready
                      </span>
                      <span
                        v-else
                        class="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                      >
                        No Mappings
                      </span>
                    </div>
                    <div class="text-sm text-gray-600 space-y-1">
                      <div><span class="font-medium">Model:</span> {{ trial.llm_model }}</div>
                      <div><span class="font-medium">Schema:</span> {{ getSchemaName(trial.schema_id) }}</div>
                      <div><span class="font-medium">Documents:</span> {{ trial.document_ids?.length || 0 }}</div>
                      <div><span class="font-medium">Created:</span> {{ formatDate(trial.created_at) }}</div>
                    </div>
                    <div v-if="!trial.hasMappings" class="mt-2 text-xs text-red-600">
                      Configure field mappings for "{{ getSchemaName(trial.schema_id) }}" schema to enable evaluation
                    </div>
                  </div>
                  <div class="flex flex-col items-end gap-2">
                    <div v-if="isAlreadyEvaluated(trial)" class="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                      Already evaluated
                    </div>
                    <div class="text-xs text-gray-500">
                      {{ trial.results?.length || 0 }} results
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="evaluateTrial"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            :disabled="!selectedTrial || isEvaluating || !selectedTrial.hasMappings"
          >
            <span v-if="isEvaluating" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Evaluating...
            </span>
            <span v-else>Evaluate Trial</span>
          </button>
        </div>

        <!-- Field Mapping Modal -->
        <GroundTruthPreviewModal
          v-if="showMappingModal"
          :project-id="projectId"
          :ground-truth="groundTruth"
          @close="showMappingModal = false"
          @configured="onMappingConfigured"
        />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  groundTruth: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close', 'evaluate']);

const toast = useToast();
const isLoading = ref(false);
const isEvaluating = ref(false);
const trials = ref([]);
const schemas = ref([]);
const selectedTrial = ref(null);
const existingEvaluations = ref([]);
const trialMappingStatus = ref({});
const showMappingModal = ref(false);

// Filter trials to only show completed ones with mapping status
const availableTrials = computed(() => {
  return trials.value
    .filter(trial => trial.status === 'completed')
    .map(trial => ({
      ...trial,
      hasMappings: trialMappingStatus.value[trial.id] || false
    }));
});

// Check if trial is already evaluated
const isAlreadyEvaluated = (trial) => {
  return existingEvaluations.value.some(evaluation => evaluation.trial_id === trial.id);
};

// Get schema name by ID
const getSchemaName = (schemaId) => {
  const schema = schemas.value.find(s => s.id === schemaId);
  return schema?.schema_name || `Schema ${schemaId}`;
};

// Check if mappings exist for a specific trial's schema
const checkMappingStatus = async (trial) => {
  try {
    const response = await api.get(
      `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${trial.schema_id}/mapping/status`
    );
    return response.data.has_mappings || false;
  } catch (err) {
    console.error(`Failed to check mapping status for trial ${trial.id}:`, err);
    return false;
  }
};

// Load mapping status for all trials
const loadMappingStatuses = async () => {
  if (!trials.value.length) return;

  const statusPromises = trials.value
    .filter(trial => trial.status === 'completed')
    .map(async (trial) => {
      const hasMapping = await checkMappingStatus(trial);
      trialMappingStatus.value[trial.id] = hasMapping;
    });

  await Promise.all(statusPromises);
};

// Load trials, schemas, and existing evaluations
const fetchData = async () => {
  isLoading.value = true;
  try {
    const [trialsResponse, schemasResponse, evaluationsResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/trial`),
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/evaluation?groundtruth_id=${props.groundTruth.id}`)
    ]);

    trials.value = trialsResponse.data;
    schemas.value = schemasResponse.data;
    existingEvaluations.value = evaluationsResponse.data;

    // Load mapping statuses for all trials
    await loadMappingStatuses();
  } catch (err) {
    toast.error(`Failed to load data: ${err.message}`);
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Select trial
const selectTrial = (trial) => {
  if (trial.hasMappings) {
    selectedTrial.value = trial;
  }
};

// Evaluate selected trial
const evaluateTrial = async () => {
  if (!selectedTrial.value || !selectedTrial.value.hasMappings) return;

  isEvaluating.value = true;
  try {
    const response = await api.post(
      `/project/${props.projectId}/trial/${selectedTrial.value.id}/evaluate?groundtruth_id=${props.groundTruth.id}`
    );

    emit('evaluate', response.data);
    toast.success('Trial evaluation completed successfully');
  } catch (err) {
    toast.error(`Failed to evaluate trial: ${err.message}`);
    console.error(err);
  } finally {
    isEvaluating.value = false;
  }
};

// Handle mapping configuration
const onMappingConfigured = async () => {
  showMappingModal.value = false;
  // Refresh mapping statuses after configuration
  await loadMappingStatuses();
  toast.success('Field mappings configured successfully');
};

onMounted(() => {
  fetchData();
});
</script>
