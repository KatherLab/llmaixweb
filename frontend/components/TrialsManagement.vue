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
          :disabled="isLoadingTrials || schemas.length === 0 || documents.length === 0"
        >
          Start New Trial
        </button>
      </div>
    </div>

    <ErrorBanner v-if="trialsError" :message="trialsError" />

    <LoadingSpinner v-if="isLoadingTrials" />

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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch, provide } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useToast } from 'vue-toastification';
import { useProjectStore } from '@/stores/projectStore';
import { useTrialsStore } from '@/stores/trialsStore';
import { useDocumentsStore } from '@/stores/documentStore';
import { useSchemasStore } from '@/stores/schemasStore';

import CreateTrialModal from '@/components/CreateTrialModal.vue';
import TrialCard from '@/components/TrialCard.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';
import ConfirmationDialog from '@/components/ConfirmationDialog.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const router = useRouter();
const route = useRoute();
const toast = useToast();
const projectStore = useProjectStore();
const trialsStore = useTrialsStore();
const documentsStore = useDocumentsStore();
const schemasStore = useSchemasStore();

const { currentProject } = storeToRefs(projectStore);
const { trials, isLoading: isLoadingTrials, error: trialsError } = storeToRefs(trialsStore);
const { documents } = storeToRefs(documentsStore);
const { schemas } = storeToRefs(schemasStore);

const projectId = computed(() => parseInt(route.params.id));
const isModalOpen = ref(false);
const isConfirmDialogOpen = ref(false);
const trialToDelete = ref(null);
const pollingIntervals = ref([]);
const showCompleted = ref(true);

// Filtered trials based on showCompleted toggle
const filteredTrials = computed(() => {
  if (showCompleted.value) {
    return trials.value;
  }
  return trials.value.filter(trial => trial.status !== 'completed' && trial.status !== 'failed');
});

// Compute options for model selection
const availableModels = ref([
  'Llama-4-Maverick-17B-128E-Instruct-FP8',
  'GPT-4o',
  'Claude-3-Opus'
]);

// Fetch data on component mount
onMounted(async () => {
  if (!currentProject.value || currentProject.value.id !== projectId.value) {
    await projectStore.fetchProject(projectId.value);
  }
  await Promise.all([
    trialsStore.fetchTrials(projectId.value),
    documentsStore.fetchDocuments(projectId.value),
    schemasStore.fetchSchemas(projectId.value)
  ]);

  // Setup polling for in-progress trials
  setupPollingForActiveTrials();
});

// Watch for changes in trials to update polling
watch(trials, () => {
  // Clear existing polling intervals
  clearPollingIntervals();
  // Set up new polling for active trials
  setupPollingForActiveTrials();
}, { deep: true });

// Clean up polling intervals when component unmounts
onUnmounted(() => {
  clearPollingIntervals();
});

// Setup polling for active trials
const setupPollingForActiveTrials = () => {
  const activeTrials = trials.value.filter(
    trial => !['completed', 'failed'].includes(trial.status)
  );

  if (activeTrials.length > 0) {
    activeTrials.forEach(trial => {
      const intervalId = setInterval(() => {
        trialsStore.fetchTrial(projectId.value, trial.id);
      }, 5000); // Poll every 5 seconds

      pollingIntervals.value.push(intervalId);
    });
  }
};

// Clear all polling intervals
const clearPollingIntervals = () => {
  pollingIntervals.value.forEach(intervalId => {
    clearInterval(intervalId);
  });
  pollingIntervals.value = [];
};

// Open modal to create a new trial
const openCreateTrialModal = () => {
  if (schemas.value.length === 0) {
    toast.error('You need to create at least one schema before you can run a trial');
    return;
  }

  if (documents.value.length === 0) {
    toast.error('You need to have processed documents before you can run a trial');
    return;
  }

  isModalOpen.value = true;
};

// Handle trial creation
const handleCreateTrial = async (trialData) => {
  try {
    await trialsStore.createTrial(projectId.value, trialData);
    toast.success('Trial created successfully');
    isModalOpen.value = false;
  } catch (err) {
    toast.error(`Failed to create trial: ${err.message || 'Unknown error'}`);
  }
};

// Confirm trial deletion
const confirmDeleteTrial = (trial) => {
  trialToDelete.value = trial;
  isConfirmDialogOpen.value = true;
};

// Delete a trial
const deleteTrial = async () => {
  if (!trialToDelete.value) return;

  try {
    await trialsStore.deleteTrial(projectId.value, trialToDelete.value.id);
    toast.success('Trial deleted successfully');
  } catch (err) {
    toast.error(`Failed to delete trial: ${err.message || 'Unknown error'}`);
  } finally {
    isConfirmDialogOpen.value = false;
    trialToDelete.value = null;
  }
};

// View trial results
const viewTrialResults = (trial) => {
  router.push({
    name: 'trial-results',
    params: {
      id: projectId.value,
      trialId: trial.id
    }
  });
};

// Retry a trial with same configuration
const retryTrial = async (trial) => {
  try {
    const trialData = {
      schema_id: trial.schema_id,
      document_ids: trial.document_ids,
      llm_model: trial.llm_model,
      api_key: trial.api_key,
      base_url: trial.base_url
    };

    await trialsStore.createTrial(projectId.value, trialData);
    toast.success('Trial restarted successfully');
  } catch (err) {
    toast.error(`Failed to restart trial: ${err.message || 'Unknown error'}`);
  }
};

// Providing context for child components
provide('projectId', projectId);
provide('availableModels', availableModels);
</script>