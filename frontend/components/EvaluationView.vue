<template>
  <div class="evaluation-view p-4">
    <!-- Enhanced Error Banner -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="flex items-start">
        <span class="w-5 h-5 text-red-400 mt-0.5 mr-3">⚠️</span>
        <div class="flex-1">
          <h3 class="text-sm font-medium text-red-800">Evaluation System Error</h3>
          <div v-if="typeof error === 'string'" class="mt-1 text-sm text-red-700">
            {{ error }}
          </div>
          <div v-else class="mt-1">
            <p class="text-sm text-red-700">{{ error.message }}</p>
            <div v-if="error.errors && error.errors.length" class="mt-2">
              <p class="text-xs font-medium text-red-800">Details:</p>
              <ul class="mt-1 text-xs text-red-700 list-disc list-inside">
                <li v-for="err in error.errors" :key="err">{{ err }}</li>
              </ul>
            </div>
            <div v-if="error.suggestions && error.suggestions.length" class="mt-2">
              <p class="text-xs font-medium text-red-800">Suggestions:</p>
              <ul class="mt-1 text-xs text-red-700 list-disc list-inside">
                <li v-for="suggestion in error.suggestions" :key="suggestion">{{ suggestion }}</li>
              </ul>
            </div>
          </div>
          <div class="mt-3 flex gap-2">
            <button
              v-if="lastFailedOperation"
              @click="retryLastOperation"
              class="text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200 transition-colors"
              :disabled="isRetrying"
            >
              <span v-if="isRetrying" class="flex items-center">
                <span class="animate-spin -ml-1 mr-1 h-3 w-3">⟳</span>
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

    <div class="header flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Evaluation</h1>
        <p class="text-gray-600">Compare trial results against ground truth data</p>
      </div>
      <div class="flex gap-2">
        <button
          @click="showUploadModal = true"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="loadingStates.groundTruthFiles"
        >
          Upload Ground Truth
        </button>
        <button
          v-if="evaluations.length > 0"
          @click="showExportModal = true"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-green-600 text-white hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed"
          :disabled="loadingStates.evaluations"
        >
          <span class="flex items-center">
            <span class="mr-1">⬇</span>
            Export Results
          </span>
        </button>
      </div>
    </div>

    <!-- Loading States -->
    <div v-if="loadingStates.groundTruthFiles" class="text-center py-8">
      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <p class="mt-2 text-gray-500">Loading ground truth files...</p>
    </div>

    <!-- No ground truth files yet -->
    <EmptyState
      v-else-if="groundTruthFiles.length === 0"
      title="No ground truth files yet"
      description="Upload ground truth data to evaluate your trial results"
      actionText="Upload Ground Truth"
      @action="showUploadModal = true"
    >
      <template #icon>
        <span class="text-6xl text-gray-400">📋</span>
      </template>
    </EmptyState>

    <!-- Main evaluation interface -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-4 gap-6">
      <!-- Ground truth files panel -->
      <div class="bg-white shadow-sm rounded-lg p-4">
        <div class="flex justify-between items-center mb-3">
          <h2 class="font-medium">Ground Truth Files</h2>
          <button
            @click="showGroundTruthManager = true"
            class="text-blue-600 hover:text-blue-800 text-sm"
          >
            Manage
          </button>
        </div>
        <div class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="(gt, index) in groundTruthFiles"
            :key="gt.id"
            class="border rounded-lg p-3 hover:bg-gray-50 cursor-pointer transition-colors"
            :class="{ 'border-blue-500 bg-blue-50': selectedGroundTruth?.id === gt.id }"
            @click="selectGroundTruthWithValidation(gt)"
          >
            <div class="font-medium text-sm">{{ gt.name || `Ground Truth #${index + 1}` }}</div>
            <div class="text-xs text-gray-500">{{ gt.format?.toUpperCase() }} • {{ formatDate(gt.created_at) }}</div>
            <div v-if="gt.field_mappings?.length" class="text-xs text-green-600 mt-1">
              {{ gt.field_mappings.length }} field mappings configured
            </div>
            <div v-else class="text-xs text-yellow-600 mt-1">
              No field mappings configured
            </div>
          </div>
        </div>
      </div>

      <!-- Trial selection and evaluation panel -->
      <div class="bg-white shadow-sm rounded-lg p-4 xl:col-span-3">
        <div v-if="!selectedGroundTruth" class="text-center py-12 text-gray-500">
          <span class="text-6xl text-gray-400 mb-3 block">📋</span>
          <p>Select a ground truth file to start evaluation</p>
        </div>
        <div v-else>
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-medium">Evaluation Dashboard</h2>
            <div class="flex gap-2">
              <button
                @click="showTrialSelectorWithValidation"
                class="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm hover:bg-blue-100 transition-colors disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                :disabled="!canStartEvaluation"
              >
                Evaluate Trial
              </button>
              <button
                v-if="selectedGroundTruth && !selectedGroundTruth.field_mappings?.length"
                @click="previewGroundTruth"
                class="px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-md text-sm hover:bg-yellow-100 transition-colors"
              >
                Preview & Configure
              </button>
            </div>
          </div>

          <!-- Prerequisites Warning -->
          <div v-if="!canStartEvaluation" class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <div class="flex">
              <span class="h-5 w-5 text-yellow-400">⚠️</span>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-yellow-800">Setup Required</h3>
                <p class="mt-1 text-sm text-yellow-700">
                  {{ evaluationPrerequisiteMessage }}
                </p>
              </div>
            </div>
          </div>

          <!-- Loading evaluations -->
          <div v-if="loadingStates.evaluations" class="text-center py-8">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading evaluations...</p>
          </div>

          <!-- Evaluation results table -->
          <div v-else-if="evaluations.length === 0" class="text-center py-8 text-gray-500">
            <span class="text-4xl text-gray-400 mb-2 block">📊</span>
            <p>No evaluations yet. Select a trial to evaluate.</p>
          </div>
          <div v-else class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trial</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Overall Accuracy</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Documents</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="evaluation in evaluations" :key="evaluation.id" class="hover:bg-gray-50">
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="font-medium truncate" :title="getTrialName(evaluation.trial_id)">
                      {{ getTrialName(evaluation.trial_id) }}
                    </div>
                    <div class="text-xs text-gray-500">
                      ID: {{ evaluation.trial_id }} • {{ formatDate(evaluation.created_at) }}
                    </div>
                  </td>

                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    {{ getTrialModel(evaluation.trial_id) }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex items-center">
                      <div class="mr-2">{{ getAccuracyPercentage(evaluation) }}%</div>
                      <div class="w-16 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" :style="{width: `${getAccuracyPercentage(evaluation)}%`}"></div>
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    {{ getDocumentCount(evaluation) }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <span v-if="hasEvaluationErrors(evaluation)" class="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                      Has Errors ({{ getErrorCount(evaluation) }})
                    </span>
                    <span v-else class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                      Complete
                    </span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex gap-2">
                      <button
                        @click="viewEvaluationAnalysis(evaluation)"
                        class="text-blue-600 hover:text-blue-800 text-sm underline"
                      >
                        Analysis
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- (Optional) Trials pagination controls just for caching models -->
          <div class="flex items-center justify-end gap-2 mt-4" v-if="trials.total > trials.limit">
            <button
              class="px-3 py-1 border rounded text-sm"
              :disabled="trials.offset === 0 || loadingStates.trials"
              @click="pageBack"
            >
              Prev
            </button>
            <span class="text-sm text-gray-600">
              {{ Math.min(trials.offset + 1, trials.total) }}–{{ Math.min(trials.offset + trials.items.length, trials.total) }} of {{ trials.total }}
            </span>
            <button
              class="px-3 py-1 border rounded text-sm"
              :disabled="trials.offset + trials.limit >= trials.total || loadingStates.trials"
              @click="pageForward"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <GroundTruthUploadModal
      v-if="showUploadModal"
      :project-id="projectId"
      @close="showUploadModal = false"
      @uploaded="onGroundTruthUploaded"
    />
    <GroundTruthManager
      :open="showGroundTruthManager"
      :project-id="projectId"
      :ground-truth-files="groundTruthFiles"
      @close="showGroundTruthManager = false"
      @updated="fetchGroundTruthFilesWithRetry"
    />
    <TrialSelectorModal
      v-if="showTrialSelector"
      :project-id="projectId"
      :ground-truth="selectedGroundTruth"
      @close="showTrialSelector = false"
      @evaluate="onTrialEvaluate"
    />

    <EvaluationAnalysisModal
      v-if="showEvaluationAnalysis"
      :project-id="projectId"
      :evaluation="selectedEvaluation"
      @close="showEvaluationAnalysis = false"
    />

    <GroundTruthPreviewModal
      v-if="showGroundTruthPreview"
      :project-id="projectId"
      :ground-truth="selectedGroundTruth"
      @close="showGroundTruthPreview = false"
      @configured="onMappingConfigured"
    />
    <MetricsExportModal
      v-if="showExportModal"
      :project-id="projectId"
      :evaluations="evaluations"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';
import EmptyState from '@/components/EmptyState.vue';
import GroundTruthUploadModal from './GroundTruthUploadModal.vue';
import GroundTruthManager from './GroundTruthManager.vue';
import TrialSelectorModal from './TrialSelectorModal.vue';
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue';
import MetricsExportModal from './MetricsExportModal.vue';
import EvaluationAnalysisModal from './evaluation/EvaluationAnalysisModal.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const toast = useToast();

// Loading states
const loadingStates = ref({
  groundTruthFiles: false,
  evaluations: false,
  trials: false
});

// Error handling
const error = ref(null);
const lastFailedOperation = ref(null);
const isRetrying = ref(false);

// Data
const groundTruthFiles = ref([]);
const selectedGroundTruth = ref(null);
const evaluations = ref([]);

// Trials pagination + cache for model lookup
const trials = ref({
  items: [],
  total: 0,
  limit: 20,
  offset: 0
});
const trialCache = ref({}); // { [id]: TrialSummary | Trial (full) }
const pendingTrialFetches = new Set();

// Modal states
const showUploadModal = ref(false);
const showGroundTruthManager = ref(false);
const showTrialSelector = ref(false);
const showGroundTruthPreview = ref(false);
const showExportModal = ref(false);
const showEvaluationAnalysis = ref(false);

// Selected items
const selectedEvaluation = ref(null);

// Computed properties
const canStartEvaluation = computed(() => {
  return selectedGroundTruth.value &&
         selectedGroundTruth.value.field_mappings?.length > 0 &&
         !loadingStates.value.groundTruthFiles &&
         !loadingStates.value.evaluations &&
         !error.value;
});

const evaluationPrerequisiteMessage = computed(() => {
  if (!selectedGroundTruth.value) {
    return 'Please select a ground truth file first.';
  }
  if (!selectedGroundTruth.value.field_mappings?.length) {
    return 'Configure field mappings for the selected ground truth file to enable evaluation.';
  }
  if (error.value) {
    return 'Resolve the current error before starting evaluation.';
  }
  return '';
});

// Utility functions
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
const fetchGroundTruthFiles = async () => {
  lastFailedOperation.value = fetchGroundTruthFiles;
  loadingStates.value.groundTruthFiles = true;
  error.value = null;

  try {
    const response = await api.get(`/project/${props.projectId}/groundtruth`);
    groundTruthFiles.value = response.data;

    if (groundTruthFiles.value.length > 0 && !selectedGroundTruth.value) {
      await selectGroundTruth(groundTruthFiles.value[0]);
    }

    lastFailedOperation.value = null;
  } catch (err) {
    handleApiError(err, 'Loading ground truth files');
  } finally {
    loadingStates.value.groundTruthFiles = false;
  }
};

const fetchGroundTruthFilesWithRetry = async () => {
  lastFailedOperation.value = fetchGroundTruthFiles;
  await fetchGroundTruthFiles();
};

// Paginated trial summaries
const fetchTrials = async (opts = {}) => {
  lastFailedOperation.value = () => fetchTrials(opts);
  loadingStates.value.trials = true;

  try {
    const { limit = trials.value.limit, offset = trials.value.offset, ...filters } = opts;
    const { data } = await api.get(`/project/${props.projectId}/trial`, {
      params: { limit, offset, ...filters }
    });

    trials.value.items = data.items || [];
    trials.value.total = data.total || 0;
    trials.value.limit = limit;
    trials.value.offset = offset;

    for (const t of trials.value.items) trialCache.value[t.id] = t;

    lastFailedOperation.value = null;
  } catch (err) {
    console.error('Failed to load trials:', err);
  } finally {
    loadingStates.value.trials = false;
  }
};

const pageBack = () => {
  const newOffset = Math.max(0, trials.value.offset - trials.value.limit);
  fetchTrials({ offset: newOffset, limit: trials.value.limit });
};
const pageForward = () => {
  const newOffset = Math.min(
    trials.value.total,
    trials.value.offset + trials.value.limit
  );
  if (newOffset !== trials.value.offset) {
    fetchTrials({ offset: newOffset, limit: trials.value.limit });
  }
};

// Lazy fetch full trial (only if a view ever needs more than the summary)
const fetchTrialIfMissing = async (id) => {
  if (trialCache.value[id]?.results || pendingTrialFetches.has(id)) return;
  pendingTrialFetches.add(id);
  try {
    const { data } = await api.get(`/project/${props.projectId}/trial/${id}`);
    trialCache.value[id] = data;
  } catch {
    /* no-op */
  } finally {
    pendingTrialFetches.delete(id);
  }
};

// Utility functions for evaluation display
const getTrialModel = (trialId) => {
  const t = trialCache.value[trialId];
  if (t?.llm_model) return t.llm_model;
  fetchTrialIfMissing(trialId);
  return 'Unknown';
};

const getTrialName = (trialId) => {
  const t = trialCache.value[trialId];
  if (t && typeof t.name === 'string' && t.name.trim().length > 0) {
    return t.name;
  }

  // If not in the current page cache, try to warm it with the full Trial.
  // (This may update reactively; until then, show a deterministic fallback.)
  if (!t) fetchTrialIfMissing(trialId);

  return `Trial #${trialId}`;
};

const getAccuracyPercentage = (evaluation) => {
  const accuracy = evaluation.overall_metrics?.accuracy || evaluation.metrics?.accuracy || 0;
  return (accuracy * 100).toFixed(1);
};

const getDocumentCount = (evaluation) => {
  return evaluation.document_summaries?.length || evaluation.document_metrics?.length || 0;
};

const hasEvaluationErrors = (evaluation) => {
  const documents = evaluation.document_summaries || evaluation.document_metrics || [];
  return documents.some(doc => doc.error || doc.has_error);
};

const getErrorCount = (evaluation) => {
  const documents = evaluation.document_summaries || evaluation.document_metrics || [];
  return documents.filter(doc => doc.error || doc.has_error).length;
};

// Validation functions
const validateEvaluationPrerequisites = () => {
  const errors = [];

  if (!selectedGroundTruth.value) {
    errors.push('Please select a ground truth file');
  }

  if (selectedGroundTruth.value && !selectedGroundTruth.value.field_mappings?.length) {
    errors.push('Ground truth file has no field mappings configured');
  }

  return errors;
};

const showTrialSelectorWithValidation = () => {
  const validationErrors = validateEvaluationPrerequisites();

  if (validationErrors.length > 0) {
    error.value = `Cannot start evaluation: ${validationErrors.join(', ')}`;
    toast.error(error.value);
    return;
  }

  showTrialSelector.value = true;
};

// Event handlers
const selectGroundTruth = async (groundTruth) => {
  try {
    error.value = null;
    selectedGroundTruth.value = groundTruth;
    await fetchEvaluations();
  } catch (err) {
    handleApiError(err, 'Selecting ground truth');
  }
};

const selectGroundTruthWithValidation = async (groundTruth) => {
  if (!groundTruth) {
    error.value = 'Invalid ground truth file selected';
    return;
  }
  await selectGroundTruth(groundTruth);
};

const fetchEvaluations = async () => {
  if (!selectedGroundTruth.value) return;

  lastFailedOperation.value = fetchEvaluations;
  loadingStates.value.evaluations = true;
  error.value = null;

  try {
    const { data } = await api.get(
      `/project/${props.projectId}/evaluation?groundtruth_id=${selectedGroundTruth.value.id}`
    );

    // 1) store the evaluations
    evaluations.value = Array.isArray(data) ? data : (data?.items ?? []);

    // 2) warm trial names/models for rows we’ll render
    for (const ev of evaluations.value) {
      if (!trialCache.value[ev.trial_id]) {
        fetchTrialIfMissing(ev.trial_id);
      }
    }

    lastFailedOperation.value = null;
  } catch (err) {
    handleApiError(err, 'Loading evaluations');
  } finally {
    loadingStates.value.evaluations = false;
  }
};


const onGroundTruthUploaded = async (groundTruth) => {
  try {
    groundTruthFiles.value.push(groundTruth);
    await selectGroundTruth(groundTruth);
    showUploadModal.value = false;
    toast.success('Ground truth uploaded successfully');
  } catch (err) {
    handleApiError(err, 'Processing uploaded ground truth');
  }
};

const onTrialEvaluate = async (evaluationSummary) => {
  try {
    // Normalize to evaluation-like object for table
    const evaluation = {
      id: evaluationSummary.id,
      trial_id: evaluationSummary.trial_id,
      groundtruth_id: evaluationSummary.groundtruth_id,
      metrics: evaluationSummary.overall_metrics,
      overall_metrics: evaluationSummary.overall_metrics,
      field_metrics: {},
      document_metrics: evaluationSummary.document_summaries || [],
      document_summaries: evaluationSummary.document_summaries,
      created_at: evaluationSummary.created_at
    };

    evaluations.value.push(evaluation);
    showTrialSelector.value = false;
    toast.success(`Trial #${evaluationSummary.trial_id} evaluation completed successfully`);
  } catch (err) {
    handleApiError(err, 'Processing evaluation result');
  }
};

const onMappingConfigured = async () => {
  try {
    showGroundTruthPreview.value = false;
    await fetchGroundTruthFiles();

    if (selectedGroundTruth.value) {
      const updatedGroundTruth = groundTruthFiles.value.find(
        gt => gt.id === selectedGroundTruth.value.id
      );
      if (updatedGroundTruth) {
        selectedGroundTruth.value = updatedGroundTruth;
      }
    }

    toast.success('Field mappings configured successfully');
  } catch (err) {
    handleApiError(err, 'Refreshing after mapping configuration');
  }
};

// Modal actions
const previewGroundTruth = () => {
  if (!selectedGroundTruth.value) {
    error.value = 'No ground truth file selected';
    return;
  }
  showGroundTruthPreview.value = true;
};

const viewEvaluationAnalysis = (evaluation) => {
  selectedEvaluation.value = evaluation;
  showEvaluationAnalysis.value = true;
};

// Initialize component
onMounted(async () => {
  loadingStates.value.groundTruthFiles = true;
  try {
    await Promise.all([
      fetchGroundTruthFiles(),
      fetchTrials() // just to warm the cache for model lookups
    ]);
  } catch (err) {
    handleApiError(err, 'Initializing evaluation view');
  } finally {
    loadingStates.value.groundTruthFiles = false;
  }
});
</script>
