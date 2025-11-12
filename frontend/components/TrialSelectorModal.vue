<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="handleClose"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Evaluate Trial</h3>
          <button @click="handleClose" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Error Display -->
        <div v-if="error" class="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-red-400 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div class="flex-1">
              <h4 class="text-sm font-medium text-red-800">Evaluation Error</h4>
              <p class="mt-1 text-sm text-red-700">{{ error }}</p>
              <div class="mt-3 flex gap-2">
                <button
                  v-if="lastFailedOperation"
                  @click="retryLastOperation"
                  class="text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200 transition-colors"
                  :disabled="isRetrying"
                >
                  <span v-if="isRetrying" class="flex items-center">
                    <svg class="animate-spin -ml-1 mr-1 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Retrying...
                  </span>
                  <span v-else>Retry</span>
                </button>
                <button
                  @click="clearError"
                  class="text-sm text-red-600 hover:text-red-800"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <!-- Prerequisites Warning -->
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

          <!-- Loading State -->
          <div v-if="loadingStates.trials" class="text-center py-8">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading trials and checking mappings...</p>
          </div>

          <!-- No Trials State -->
          <div v-else-if="trials.items.length === 0" class="text-center py-8 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p>No completed trials available for evaluation</p>
            <p class="text-sm text-gray-400 mt-1">Run some trials first to evaluate them against ground truth</p>
          </div>

          <!-- Trials List -->
          <div v-else>
            <div class="mb-4">
              <h4 class="font-medium text-gray-900 mb-2">Select a trial to evaluate</h4>
              <p class="text-sm text-gray-600">Choose from completed trials to compare against your ground truth data.</p>
              <div class="mt-3 flex gap-4 text-sm">
                <span class="text-gray-600">
                  Total trials: <span class="font-medium">{{ trials.total }}</span>
                </span>
                <span class="text-green-600">
                  Ready for evaluation: <span class="font-medium">{{ availableTrials.filter(t => t.hasMappings).length }}</span>
                </span>
                <span class="text-red-600">
                  Missing mappings: <span class="font-medium">{{ availableTrials.filter(t => !t.hasMappings).length }}</span>
                </span>
              </div>
            </div>

            <!-- Mapping Status Loading -->
            <div v-if="loadingStates.mappings" class="text-center py-4">
              <div class="inline-block animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <p class="mt-2 text-sm text-gray-500">Checking field mappings...</p>
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
                @click="trial.hasMappings ? selectTrial(trial) : showMappingRequiredTooltip(trial)"
              >
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                      <h5 class="font-medium text-gray-900">Trial #{{ trial.id }}</h5>
                      <span class="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {{ trial.status }}
                      </span>
                      <span
                        v-if="trial.hasMappings"
                        class="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        ✓ Mappings Ready
                      </span>
                      <span
                        v-else-if="trial.mappingStatus === 'loading'"
                        class="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600"
                      >
                        Checking...
                      </span>
                      <span
                        v-else
                        class="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                      >
                        ⚠ No Mappings
                      </span>
                    </div>
                    <div class="text-sm text-gray-600 grid grid-cols-2 gap-y-1 gap-x-4">
                      <div><span class="font-medium">Model:</span> {{ trial.llm_model }}</div>
                      <div><span class="font-medium">Schema:</span> {{ getSchemaName(trial.schema_id) }}</div>
                      <div><span class="font-medium">Documents:</span> {{ trial.documents_count }}</div>
                      <div><span class="font-medium">Results:</span> {{ trial.results_count }}</div>
                      <div><span class="font-medium">Created:</span> {{ formatDate(trial.created_at) }}</div>
                      <div><span class="font-medium">Last result:</span> {{ trial.last_result_at ? formatDate(trial.last_result_at) : '—' }}</div>
                      <div v-if="trial.has_failures !== null && trial.has_failures !== undefined" class="col-span-2">
                        <span
                          v-if="trial.has_failures"
                          class="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"
                        >
                          Errors: {{ trial.error_count || 0 }}
                        </span>
                        <span
                          v-else
                          class="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                        >
                          No Errors
                        </span>
                      </div>
                    </div>
                    <div v-if="!trial.hasMappings && trial.mappingStatus !== 'loading'" class="mt-2 text-xs text-red-600">
                      Configure field mappings for "{{ getSchemaName(trial.schema_id) }}" schema to enable evaluation
                    </div>
                  </div>
                  <div class="flex flex-col items-end gap-2">
                    <div v-if="isAlreadyEvaluated(trial)" class="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                      Already evaluated
                    </div>
                    <div class="text-xs text-gray-500">
                      {{ trial.results_count }} results
                    </div>
                  </div>
                </div>
              </div>

              <!-- Load more for pagination -->
              <div class="pt-2 flex justify-center" v-if="trials.items.length < trials.total">
                <button
                  class="px-4 py-2 border rounded-md text-sm"
                  :disabled="loadingStates.trials"
                  @click="loadMore"
                >
                  {{ loadingStates.trials ? 'Loading...' : 'Load more' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            type="button"
            @click="handleClose"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="evaluateTrialWithValidation"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            :disabled="!canEvaluate"
          >
            <span v-if="isEvaluating" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Evaluating...
            </span>
            <span v-else>{{ selectedTrial ? `Evaluate Trial #${selectedTrial.id}` : 'Select Trial First' }}</span>
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
import { ref, onMounted, computed, onBeforeUnmount } from 'vue';
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

// Loading states
const loadingStates = ref({
  trials: false,
  mappings: false,
  evaluation: false
});

// Paginated trials data (summaries)
const trials = ref({
  items: [],
  total: 0,
  limit: 20,
  offset: 0
});

const schemas = ref([]);
const selectedTrial = ref(null);
const existingEvaluations = ref([]);
const trialMappingStatus = ref({});
const showMappingModal = ref(false);

// Error handling
const error = ref(null);
const lastFailedOperation = ref(null);
const isRetrying = ref(false);

// Computed properties
const isEvaluating = computed(() => loadingStates.value.evaluation);

const canEvaluate = computed(() => {
  return !!selectedTrial.value &&
         !!selectedTrial.value.hasMappings &&
         (selectedTrial.value.results_count || 0) > 0 &&
         !isEvaluating.value &&
         !loadingStates.value.trials &&
         !error.value;
});

// Only completed trials are shown in this selector
const availableTrials = computed(() => {
  return trials.value.items
    .filter(trial => trial.status === 'completed')
    .map(trial => ({
      ...trial,
      hasMappings: trialMappingStatus.value[trial.id] || false,
      mappingStatus: trialMappingStatus.value[trial.id] === undefined ? 'loading' : 'loaded'
    }));
});

// Utility functions
const isAlreadyEvaluated = (trial) => {
  return existingEvaluations.value.some(evaluation => evaluation.trial_id === trial.id);
};

const getSchemaName = (schemaId) => {
  const schema = schemas.value.find(s => s.id === schemaId);
  return schema?.schema_name || `Schema ${schemaId}`;
};

// Error handling functions
const clearError = () => {
  error.value = null;
  lastFailedOperation.value = null;
};

const handleApiError = (err, operation) => {
  console.error(`${operation} failed:`, err);

  let errorMessage;

  if (!err.response) {
    errorMessage = `Network error during ${operation}. Please check your connection and try again.`;
  } else if (err.response.status === 400) {
    errorMessage = `${operation} failed: ${err.response.data?.detail || err.message}`;
  } else if (err.response.status === 403) {
    errorMessage = `Permission denied: You don't have access to ${operation.toLowerCase()}.`;
  } else if (err.response.status === 404) {
    errorMessage = `Resource not found during ${operation}. Please refresh and try again.`;
  } else if (err.response.status === 500) {
    errorMessage = `Server error during ${operation}. Please try again later or contact support.`;
  } else {
    errorMessage = `${operation} failed: ${err.response?.data?.detail || err.message}`;
  }

  error.value = errorMessage;
  toast.error(errorMessage);
};

const retryLastOperation = async () => {
  if (!lastFailedOperation.value) return;

  isRetrying.value = true;
  error.value = null;

  try {
    await lastFailedOperation.value();
    toast.success('Operation completed successfully');
    lastFailedOperation.value = null;
  } catch (err) {
    handleApiError(err, 'Retry');
  } finally {
    isRetrying.value = false;
  }
};

// Data fetching functions
const fetchTrials = async ({ append = false } = {}) => {
  lastFailedOperation.value = () => fetchTrials({ append });
  loadingStates.value.trials = true;

  try {
    const { limit, offset } = trials.value;
    // Filter to completed to avoid extra client-side filtering volume
    const { data } = await api.get(`/project/${props.projectId}/trial`, {
      params: { limit, offset, status: 'completed' }
    });

    if (append) {
      trials.value.items.push(...(data.items || []));
    } else {
      trials.value.items = data.items || [];
    }
    trials.value.total = data.total || trials.value.items.length;

    // Once a page is loaded, check mapping statuses for those trials
    await loadMappingStatusesFor(trials.value.items);

    lastFailedOperation.value = null;
  } catch (err) {
    handleApiError(err, 'Loading trial data');
  } finally {
    loadingStates.value.trials = false;
  }
};

const loadMore = async () => {
  if (trials.value.items.length >= trials.value.total) return;
  trials.value.offset = trials.value.items.length;
  await fetchTrials({ append: true });
};

// Fetch schemas and existing evaluations for this ground truth
const fetchSchemasAndEvaluations = async () => {
  const [schemasResponse, evaluationsResponse] = await Promise.all([
    api.get(`/project/${props.projectId}/schema`),
    api.get(`/project/${props.projectId}/evaluation?groundtruth_id=${props.groundTruth.id}`)
  ]);
  schemas.value = schemasResponse.data;
  existingEvaluations.value = evaluationsResponse.data;
};

const fetchData = async () => {
  lastFailedOperation.value = fetchData;
  error.value = null;

  try {
    // Reset paging for fresh open
    trials.value.limit = 20;
    trials.value.offset = 0;

    await Promise.all([
      fetchSchemasAndEvaluations(),
      fetchTrials()
    ]);

    lastFailedOperation.value = null;
  } catch (err) {
    handleApiError(err, 'Loading trial data');
  }
};

// Mapping checks
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

const loadMappingStatusesFor = async (trialList) => {
  const completed = trialList.filter(t => t.status === 'completed');
  if (!completed.length) return;

  loadingStates.value.mappings = true;
  try {
    const checks = completed.map(async (trial) => {
      const hasMapping = await checkMappingStatus(trial);
      trialMappingStatus.value[trial.id] = hasMapping;
    });
    await Promise.all(checks);
  } catch (err) {
    console.error('Error loading mapping statuses:', err);
  } finally {
    loadingStates.value.mappings = false;
  }
};

// Trial selection
const selectTrial = (trial) => {
  if (trial.hasMappings) {
    selectedTrial.value = trial;
    error.value = null;
  }
};

const showMappingRequiredTooltip = (trial) => {
  toast.warning(`Configure field mappings for "${getSchemaName(trial.schema_id)}" schema first`);
};

// Validation (uses summary fields)
const validateEvaluationPrerequisites = () => {
  const errors = [];

  if (!selectedTrial.value) {
    errors.push('Please select a trial to evaluate');
  }

  if (selectedTrial.value && !selectedTrial.value.hasMappings) {
    errors.push(`Trial #${selectedTrial.value.id} requires field mappings for schema "${getSchemaName(selectedTrial.value.schema_id)}"`);
  }

  if (!props.groundTruth) {
    errors.push('Ground truth file is required');
  }

  if (selectedTrial.value && (selectedTrial.value.results_count || 0) === 0) {
    errors.push('Selected trial has no results to evaluate');
  }

  return errors;
};

// Evaluate
const evaluateTrialWithValidation = async () => {
  const validationErrors = validateEvaluationPrerequisites();
  if (validationErrors.length > 0) {
    error.value = `Cannot evaluate trial: ${validationErrors.join(', ')}`;
    toast.error(error.value);
    return;
  }

  lastFailedOperation.value = evaluateTrialWithValidation;
  loadingStates.value.evaluation = true;
  error.value = null;

  try {
    // Re-check mapping before posting
    const mappingStatus = await checkMappingStatus(selectedTrial.value);
    if (!mappingStatus) {
      throw new Error(`Field mappings for schema "${getSchemaName(selectedTrial.value.schema_id)}" are not configured or have been removed`);
    }

    const response = await api.post(
      `/project/${props.projectId}/trial/${selectedTrial.value.id}/evaluate?groundtruth_id=${props.groundTruth.id}`
    );

    emit('evaluate', response.data);
    toast.success(`Trial #${selectedTrial.value.id} evaluation completed successfully`);
    lastFailedOperation.value = null;
  } catch (err) {
    if (err.response?.status === 400) {
      const detail = err.response.data?.detail || err.message;
      if (detail.includes('No field mapping found')) {
        error.value = `Field mappings missing: ${detail}`;
        toast.error('Field mappings are required but not found. Please configure them first.');
      } else if (detail.includes('No results found')) {
        error.value = 'Trial has no results to evaluate. Please run the trial first.';
        toast.error(error.value);
      } else if (detail.includes('Document not found') || detail.includes('No ground truth found')) {
        error.value = 'Data consistency issue detected. Some documents or ground truth entries are missing.';
        toast.error(error.value);
      } else {
        error.value = `Evaluation failed: ${detail}`;
        toast.error(error.value);
      }
    } else {
      handleApiError(err, 'Trial evaluation');
    }
  } finally {
    loadingStates.value.evaluation = false;
  }
};

// Mapping configured
const onMappingConfigured = async () => {
  showMappingModal.value = false;
  try {
    await loadMappingStatusesFor(trials.value.items);
    toast.success('Field mappings configured successfully');
  } catch (err) {
    handleApiError(err, 'Refreshing mapping status');
  }
};

/** BODY SCROLL LOCK LOGIC **/
const lockBodyScroll = () => {
  if (typeof window !== 'undefined') {
    document.body.classList.add('no-scroll');
  }
};
const unlockBodyScroll = () => {
  if (typeof window !== 'undefined') {
    document.body.classList.remove('no-scroll');
  }
};

const handleClose = () => {
  unlockBodyScroll();
  emit('close');
};

onMounted(() => {
  lockBodyScroll();
  fetchData();
});
onBeforeUnmount(() => {
  unlockBodyScroll();
});
</script>

<style>
.no-scroll {
  overflow: hidden !important;
}
</style>
