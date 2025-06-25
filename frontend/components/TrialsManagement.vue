<template>
  <div class="trials-management p-4">
    <div class="header flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Trials</h1>
        <p class="text-gray-600">Run information extraction trials on your documents</p>
      </div>
      <div class="flex gap-4">
        <label class="flex items-center">
          <input
            type="checkbox"
            v-model="showCompleted"
            class="mr-2"
          />
          Show completed trials
        </label>
        <button
          @click="openCreateTrialModal"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="isLoading || schemas.length === 0 || documents.length === 0"
          :title="`isLoading: ${isLoading}, schemas.length: ${schemas.length}, documents.length: ${documents.length}`"
        >
          Start New Trial
        </button>
      </div>
    </div>
    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />
    <EmptyState
      v-else-if="trials.length === 0"
      title="No trials yet"
      description="Run a trial to extract structured information from your documents"
      actionText="Start a Trial"
      @action="openCreateTrialModal"
      :disabled="schemas.length === 0 || documents.length === 0"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </template>
    </EmptyState>
    <div v-else-if="filteredTrials.length === 0" class="text-center py-8 bg-gray-50 rounded-md">
      <p>No trials match your filter criteria.</p>
    </div>
    <div v-else class="grid gap-4">
      <TrialCard
        v-for="trial in filteredTrials"
        :key="trial.id"
        :trial="trial"
        :projectId="projectId"
        @view="viewTrialResults"
        @retry="retryTrial"
        @delete="confirmDeleteTrial"
      />
    </div>
    <CreateTrialModal
      v-if="isModalOpen"
      :open="isModalOpen"
      :documents="documents"
      :schemas="schemas"
      :models="availableModels"
      @close="isModalOpen = false"
      @create="handleCreateTrial"
    />
    <ConfirmationDialog
      v-if="isConfirmDialogOpen"
      :open="isConfirmDialogOpen"
      title="Delete Trial"
      message="Are you sure you want to delete this trial? This action cannot be undone."
      @confirm="deleteTrial"
      @cancel="isConfirmDialogOpen = false"
    />
    <TrialResults
      v-if="showTrialResultsModal"
      :isModal="true"
      :projectId="props.projectId"
      :trialId="selectedTrialId"
      @close="showTrialResultsModal = false"
    />
    <ModalDialog
      v-if="showDownloadModal"
      title="Download Trial Results"
      @close="showDownloadModal = false"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Format</label>
          <div class="mt-2 space-y-2">
            <div class="flex items-center">
              <input
                id="format-json"
                v-model="downloadFormat"
                type="radio"
                value="json"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <label for="format-json" class="ml-2 block text-sm text-gray-700">
                JSON (one file per document)
              </label>
            </div>
            <div class="flex items-center">
              <input
                id="format-csv"
                v-model="downloadFormat"
                type="radio"
                value="csv"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <label for="format-csv" class="ml-2 block text-sm text-gray-700">
                CSV (flattened structure)
              </label>
            </div>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Include</label>
          <div class="mt-2">
            <div class="flex items-center">
              <input
                id="include-content"
                v-model="includeContent"
                type="checkbox"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label for="include-content" class="ml-2 block text-sm text-gray-700">
                Include document content
              </label>
            </div>
          </div>
        </div>
        <div class="mt-6 flex justify-end space-x-3">
          <button
            type="button"
            @click="showDownloadModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="downloadTrialResults(trialToDownload, { format: downloadFormat, includeContent }); showDownloadModal = false;"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Download
          </button>
        </div>
      </div>
    </ModalDialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useToast } from 'vue-toastification';
import { api } from '@/services/api';
import CreateTrialModal from '@/components/CreateTrialModal.vue';
import TrialCard from '@/components/TrialCard.vue';
import TrialResults from '@/components/TrialResults.vue';
import ModalDialog from '@/components/ModalDialog.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';
import ConfirmationDialog from '@/components/ConfirmationDialog.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const router = useRouter();
const route = useRoute();
const toast = useToast();

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const documents = ref([]);
const schemas = ref([]);
const trials = ref([]);
const isLoading = ref(true);
const error = ref(null);
const isModalOpen = ref(false);
const isConfirmDialogOpen = ref(false);
const trialToDelete = ref(null);
const showCompleted = ref(true);
const availableModels = ref([
  'Llama-4-Maverick-17B-128E-Instruct-FP8',
  'GPT-4o',
  'Claude-3-Opus'
]);

const filteredTrials = computed(() => {
  if (showCompleted.value) {
    return trials.value;
  }
  return trials.value.filter(trial => trial.status !== 'completed' && trial.status !== 'failed');
});

const showTrialResultsModal = ref(false);
const selectedTrialId = ref(null);

const viewTrialResults = (trial) => {
  selectedTrialId.value = trial.id;
  showTrialResultsModal.value = true;
};

onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, trialsResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/document`),
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/trial`)
    ]);

    documents.value = documentsResponse.data;
    schemas.value = schemasResponse.data;
    trials.value = trialsResponse.data;
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
});

const openCreateTrialModal = () => {
  isModalOpen.value = true;
};

const handleCreateTrial = async (trialData) => {
  try {
    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.push(response.data);
    toast.success('Trial created successfully');
    isModalOpen.value = false;
  } catch (err) {
    toast.error(`Failed to create trial: ${err.message || 'Unknown error'}`);
  }
};

const confirmDeleteTrial = (trial) => {
  trialToDelete.value = trial;
  isConfirmDialogOpen.value = true;
};

const deleteTrial = async () => {
  if (!trialToDelete.value) return;

  try {
    await api.delete(`/project/${props.projectId}/trial/${trialToDelete.value.id}`);
    trials.value = trials.value.filter(trial => trial.id !== trialToDelete.value.id);
    toast.success('Trial deleted successfully');
  } catch (err) {
    toast.error(`Failed to delete trial: ${err.message || 'Unknown error'}`);
  } finally {
    isConfirmDialogOpen.value = false;
    trialToDelete.value = null;
  }
};

const retryTrial = async (trial) => {
  try {
    const trialData = {
      schema_id: trial.schema_id,
      document_ids: trial.document_ids,
      llm_model: trial.llm_model,
      api_key: trial.api_key,
      base_url: trial.base_url
    };

    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.push(response.data);
    toast.success('Trial restarted successfully');
  } catch (err) {
    toast.error(`Failed to restart trial: ${err.message || 'Unknown error'}`);
  }
};

const downloadTrialResults = async (trial, options = {}) => {
  const { format = 'json', includeContent = true } = options;

  try {
    const response = await api.get(
      `/project/${props.projectId}/trial/${trial.id}/download?format=${format}&include_content=${includeContent}`,
      { responseType: 'blob' }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `trial_${trial.id}_results.${format}`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    toast.success('Trial results downloaded successfully');
  } catch (err) {
    toast.error(`Failed to download trial results: ${err.message}`);
    console.error(err);
  }
};

const trialToDownload = ref(null);
const showDownloadModal = ref(false);

const openDownloadModal = (trial) => {
  trialToDownload.value = trial;
  showDownloadModal.value = true;
};

const downloadFormat = ref('json');
const includeContent = ref(true);
</script>