// EvaluationView.vue
<template>
  <div class="evaluation-view p-4">
    <div class="header flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Evaluation</h1>
        <p class="text-gray-600">Compare trial results against ground truth data</p>
      </div>
      <div class="flex gap-2">
        <button
          @click="showUploadModal = true"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="isLoading"
        >
          Upload Ground Truth
        </button>
        <button
          v-if="evaluations.length > 0"
          @click="showExportModal = true"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-green-600 text-white hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed"
          :disabled="isLoading"
        >
          <span class="flex items-center">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Results
          </span>
        </button>
      </div>
    </div>
    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />
    <!-- No ground truth files yet -->
    <EmptyState
      v-else-if="groundTruthFiles.length === 0"
      title="No ground truth files yet"
      description="Upload ground truth data to evaluate your trial results"
      actionText="Upload Ground Truth"
      @action="showUploadModal = true"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
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
            @click="selectGroundTruth(gt)"
          >
            <div class="font-medium text-sm">{{ gt.name || `Ground Truth #${index + 1}` }}</div>
            <div class="text-xs text-gray-500">{{ gt.format?.toUpperCase() }} • {{ formatDate(gt.created_at) }}</div>
            <div v-if="gt.field_mappings?.length" class="text-xs text-green-600 mt-1">
              {{ gt.field_mappings.length }} field mappings configured
            </div>
          </div>
        </div>
      </div>
      <!-- Trial selection and evaluation panel -->
      <div class="bg-white shadow-sm rounded-lg p-4 xl:col-span-3">
        <div v-if="!selectedGroundTruth" class="text-center py-12 text-gray-500">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p>Select a ground truth file to start evaluation</p>
        </div>
        <div v-else>
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-medium">Evaluation Dashboard</h2>
            <div class="flex gap-2">
              <button
                @click="showTrialSelector = true"
                class="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm hover:bg-blue-100 transition-colors"
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
          <!-- Evaluation results table -->
          <div v-if="evaluations.length === 0" class="text-center py-8 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2-2V7a2 2 0 012-2h2a2 2 0 002 2v2a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 00-2 2h-2a2 2 0 00-2 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2z" />
            </svg>
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
                  <th class="px-4 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="evaluation in evaluations" :key="evaluation.id" class="hover:bg-gray-50">
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="font-medium">Trial #{{ evaluation.trial_id }}</div>
                    <div class="text-xs text-gray-500">{{ formatDate(evaluation.created_at) }}</div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    {{ getTrialModel(evaluation.trial_id) }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex items-center">
                      <!-- Fix: Use overall_metrics instead of metrics -->
                      <div class="mr-2">{{ ((evaluation.overall_metrics?.accuracy || evaluation.metrics?.accuracy || 0) * 100).toFixed(1) }}%</div>
                      <div class="w-16 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" :style="{width: `${((evaluation.overall_metrics?.accuracy || evaluation.metrics?.accuracy || 0) * 100)}%`}"></div>
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    {{ evaluation.document_summaries?.length || evaluation.document_metrics?.length || 0 }}
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm">
                    <div class="flex gap-2">
                      <button
                        @click="viewEvaluationDetails(evaluation)"
                        class="text-blue-600 hover:text-blue-800 text-sm underline"
                      >
                        Details
                      </button>
                      <button
                        @click="viewDocumentEvaluations(evaluation)"
                        class="text-green-600 hover:text-green-800 text-sm underline"
                      >
                        Documents
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
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
      v-if="showGroundTruthManager"
      :project-id="projectId"
      :ground-truth-files="groundTruthFiles"
      @close="showGroundTruthManager = false"
      @updated="fetchGroundTruthFiles"
    />
    <TrialSelectorModal
      v-if="showTrialSelector"
      :project-id="projectId"
      :ground-truth="selectedGroundTruth"
      @close="showTrialSelector = false"
      @evaluate="onTrialEvaluate"
    />
    <EvaluationDetailsModal
      v-if="showEvaluationDetails"
      :project-id="projectId"
      :evaluation="selectedEvaluation"
      @close="showEvaluationDetails = false"
    />
    <DocumentEvaluationModal
      v-if="showDocumentEvaluation"
      :project-id="projectId"
      :evaluation="selectedEvaluation"
      @close="showDocumentEvaluation = false"
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
import ErrorBanner from '@/components/ErrorBanner.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';
import GroundTruthUploadModal from './GroundTruthUploadModal.vue';
import GroundTruthManager from './GroundTruthManager.vue';
import TrialSelectorModal from './TrialSelectorModal.vue';
import EvaluationDetailsModal from './EvaluationDetailsModal.vue';
import DocumentEvaluationModal from './DocumentEvaluationModal.vue';
import GroundTruthPreviewModal from './GroundTruthPreviewModal.vue';
import MetricsExportModal from './MetricsExportModal.vue';
const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});
const toast = useToast();
const isLoading = ref(false);
const error = ref(null);
// Data
const groundTruthFiles = ref([]);
const selectedGroundTruth = ref(null);
const evaluations = ref([]);
const trials = ref([]);
// Modal states
const showUploadModal = ref(false);
const showGroundTruthManager = ref(false);
const showTrialSelector = ref(false);
const showEvaluationDetails = ref(false);
const showDocumentEvaluation = ref(false);
const showGroundTruthPreview = ref(false);
const showExportModal = ref(false);
// Selected items
const selectedEvaluation = ref(null);
// Load ground truth files
const fetchGroundTruthFiles = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/groundtruth`);
    groundTruthFiles.value = response.data;
    // Auto-select first ground truth if none selected
    if (groundTruthFiles.value.length > 0 && !selectedGroundTruth.value) {
      selectGroundTruth(groundTruthFiles.value[0]);
    }
  } catch (err) {
    error.value = `Failed to load ground truth files: ${err.message}`;
    console.error(err);
  }
};
// Load trials for model names
const fetchTrials = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/trial`);
    trials.value = response.data;
  } catch (err) {
    console.error('Failed to load trials:', err);
  }
};
// Select ground truth and load evaluations
const selectGroundTruth = async (groundTruth) => {
  selectedGroundTruth.value = groundTruth;
  await fetchEvaluations();
};
// Load evaluations for selected ground truth
const fetchEvaluations = async () => {
  if (!selectedGroundTruth.value) return;
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/evaluation?groundtruth_id=${selectedGroundTruth.value.id}`);
    evaluations.value = response.data;
  } catch (err) {
    error.value = `Failed to load evaluations: ${err.message}`;
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};
// Get trial model name
const getTrialModel = (trialId) => {
  const trial = trials.value.find(t => t.id === trialId);
  return trial?.llm_model || 'Unknown';
};
// Event handlers
const onGroundTruthUploaded = (groundTruth) => {
  groundTruthFiles.value.push(groundTruth);
  selectGroundTruth(groundTruth);
  showUploadModal.value = false;
  toast.success('Ground truth uploaded successfully');
};
const onTrialEvaluate = async (evaluationSummary) => {
  // Convert EvaluationSummary to Evaluation format for consistency
  const evaluation = {
    id: evaluationSummary.id,
    trial_id: evaluationSummary.trial_id,
    groundtruth_id: evaluationSummary.groundtruth_id,
    metrics: evaluationSummary.overall_metrics, // Map overall_metrics to metrics
    overall_metrics: evaluationSummary.overall_metrics,
    field_metrics: {}, // Can be populated from field_summaries if needed
    document_metrics: evaluationSummary.document_summaries || [],
    document_summaries: evaluationSummary.document_summaries,
    created_at: evaluationSummary.created_at
  };

  evaluations.value.push(evaluation);
  showTrialSelector.value = false;
  toast.success('Trial evaluation completed');
};

const onMappingConfigured = () => {
  showGroundTruthPreview.value = false;
  fetchGroundTruthFiles(); // Refresh to get updated mappings
  toast.success('Field mappings configured successfully');
};
// Modal actions
const previewGroundTruth = () => {
  showGroundTruthPreview.value = true;
};
const viewEvaluationDetails = (evaluation) => {
  selectedEvaluation.value = evaluation;
  showEvaluationDetails.value = true;
};
const viewDocumentEvaluations = (evaluation) => {
  selectedEvaluation.value = evaluation;
  showDocumentEvaluation.value = true;
};
// Initialize
onMounted(async () => {
  isLoading.value = true;
  try {
    await Promise.all([
      fetchGroundTruthFiles(),
      fetchTrials()
    ]);
  } catch (err) {
    error.value = 'Failed to initialize evaluation view';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
});
</script>