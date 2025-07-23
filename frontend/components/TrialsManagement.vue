<template>
  <div class="p-6 space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Trials</h1>
        <p class="text-gray-500 mt-1">Run and manage information extraction trials</p>
      </div>
      <div class="flex items-center gap-4">
        <label class="flex items-center text-sm gap-2">
          <input type="checkbox" v-model="showCompleted" class="rounded border-gray-300" />
          <span class="text-gray-700">Show completed</span>
        </label>
        <button
          @click="openCreateTrialModal"
          class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition"
          :disabled="isLoading || schemas.length === 0 || documents.length === 0 || prompts.length === 0"
        >
          Start New Trial
        </button>
      </div>
    </div>

    <!-- Advanced Filter Panel -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-6 gap-4">
        <!-- Search -->
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <div class="relative">
            <input
              v-model="filters.search"
              type="text"
              placeholder="Search in name, description, or ID..."
              class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
          </div>
        </div>
        <!-- Status -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select v-model="filters.status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <!-- Schema -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Schema</label>
          <select v-model="filters.schemaId" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option value="">All Schemas</option>
            <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
              {{ schema.schema_name }}
            </option>
          </select>
        </div>
        <!-- Model -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
          <select v-model="filters.llmModel" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option value="">All Models</option>
            <option v-for="model in availableTrialModels" :key="model" :value="model">{{ model }}</option>
          </select>
        </div>
        <!-- Prompt -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
          <select v-model="filters.promptId" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option value="">All Prompts</option>
            <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">
              {{ prompt.name }}
            </option>
          </select>
        </div>
        <!-- Date Range & Clear -->
        <div class="flex flex-col gap-2">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Created</label>
            <select v-model="filters.dateRange" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
              <option value="">All Time</option>
              <option value="today">Today</option>
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
            </select>
          </div>
          <button
            @click="clearFilters"
            class="mt-2 w-full px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
          >
            Clear
          </button>
        </div>
      </div>
    </div>

    <!-- Batch Action Bar -->
    <div v-if="selectedTrials.length > 0" class="bg-blue-50 border border-blue-200 rounded-lg flex flex-wrap items-center gap-4 px-4 py-3 shadow mb-4">
      <span class="font-medium text-blue-700 text-sm">{{ selectedTrials.length }} selected</span>
      <button
        class="text-blue-700 hover:bg-blue-100 rounded-md px-3 py-1 text-sm font-medium"
        @click="openBatchModal('retry')"
      >
        <svg class="inline w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Retry
      </button>
      <button
        class="text-blue-700 hover:bg-blue-100 rounded-md px-3 py-1 text-sm font-medium"
        @click="openBatchModal('export')"
      >
        <svg class="inline w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Export
      </button>
      <button
        class="text-red-600 hover:bg-red-50 border border-red-100 rounded-md px-3 py-1 text-sm font-medium"
        @click="openBatchModal('delete')"
      >
        <svg class="inline w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
        Delete
      </button>
      <button
        class="text-gray-600 hover:text-blue-700 px-3 py-1 text-sm font-medium"
        @click="selectedTrials = []"
      >
        Clear
      </button>
    </div>

    <!-- Error, Loading, Empty -->
    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />

    <!-- No trials -->
    <EmptyState
      v-else-if="filteredTrials.length === 0"
      title="No trials found"
      description="Try changing your filters or create a new trial."
      actionText="Start a Trial"
      @action="openCreateTrialModal"
      :disabled="schemas.length === 0 || documents.length === 0 || prompts.length === 0"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </template>
    </EmptyState>

    <!-- Trials Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <TrialCard
        v-for="trial in filteredTrials"
        :key="trial.id"
        :trial="trial"
        :schemas="schemas"
        :prompts="prompts"
        :selected="selectedTrials.includes(trial.id)"
        @select="toggleTrialSelection(trial.id)"
        @rename="openRenameModal(trial)"
        @delete="confirmDeleteTrial(trial)"
        @retry="retryTrial(trial)"
        @download="openDownloadModal(trial)"
        @view-results="viewTrialResults(trial)"
        @view-schema="viewTrialSchema(trial)"
        @view-prompt="viewTrialPrompt(trial)"
      />
    </div>

    <!-- Modals -->
    <CreateTrialModal
      v-if="isModalOpen"
      :open="isModalOpen"
      :documents="documents"
      :schemas="schemas"
      :prompts="prompts"
      :projectId="props.projectId"
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
    <RenameTrialModal
      v-if="showRenameModal"
      :open="showRenameModal"
      :trial="editingTrial"
      @close="showRenameModal = false"
      @rename="submitRename"
    />
    <BatchActionsModal
      v-if="showBatchModal"
      :action="batchAction"
      :trials="selectedTrials"
      :projectId="props.projectId"
      @close="showBatchModal = false"
      @complete="handleBatchActionComplete"
    />
    <TrialSchemaModal
      v-if="showSchemaModal"
      :open="showSchemaModal"
      :schema="selectedSchema"
      @close="showSchemaModal = false"
    />
    <TrialPromptModal
      v-if="showPromptModal"
      :open="showPromptModal"
      :prompt="selectedPrompt"
      @close="showPromptModal = false"
    />
    <DownloadModal
      v-if="showDownloadModal"
      :open="showDownloadModal"
      :trial="trialToDownload"
      :projectId="props.projectId"
      @close="showDownloadModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useToast } from 'vue-toastification';
import { api } from '@/services/api';
import CreateTrialModal from '@/components/trials/CreateTrialModal.vue';
import TrialCard from '@/components/trials/TrialCard.vue';
import BatchActionsModal from '@/components/documents/BatchActionsModal.vue';
import RenameTrialModal from '@/components/trials/RenameTrialModal.vue';
import TrialResults from '@/components/trials/TrialResults.vue';
import TrialSchemaModal from '@/components/trials/TrialSchemaModal.vue';
import TrialPromptModal from '@/components/trials/TrialPromptModal.vue';
import DownloadModal from '@/components/trials/DownloadModal.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';
import ConfirmationDialog from '@/components/ConfirmationDialog.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const toast = useToast();

const documents = ref([]);
const schemas = ref([]);
const prompts = ref([]);
const trials = ref([]);
const isLoading = ref(true);
const error = ref(null);
const isModalOpen = ref(false);
const isConfirmDialogOpen = ref(false);
const trialToDelete = ref(null);
const showCompleted = ref(true);
const showRenameModal = ref(false);
const editingTrial = ref(null);
const selectedTrials = ref([]);
const showBatchModal = ref(false);
const batchAction = ref('');
const showTrialResultsModal = ref(false);
const selectedTrialId = ref(null);
const showSchemaModal = ref(false);
const selectedSchema = ref(null);
const showPromptModal = ref(false);
const selectedPrompt = ref(null);
const showDownloadModal = ref(false);
const trialToDownload = ref(null);

const pollInterval = ref(null);
const isPollingActive = ref(false);
const POLL_INTERVAL_MS = 3000;


const filters = ref({
  search: '',
  status: '',
  schemaId: '',
  llmModel: '',
  promptId: '',
  dateRange: '',
});
const clearFilters = () => {
  filters.value = {
    search: '',
    status: '',
    schemaId: '',
    llmModel: '',
    promptId: '',
    dateRange: '',
  };
};

const availableTrialModels = computed(() => {
  const allModels = trials.value.map(t => t.llm_model).filter(Boolean);
  return [...new Set(allModels)];
});
const filteredTrials = computed(() => {
  let result = [...trials.value];
  // Search filter
  if (filters.value.search) {
    const q = filters.value.search.toLowerCase();
    result = result.filter(trial =>
      (trial.name && trial.name.toLowerCase().includes(q)) ||
      (trial.description && trial.description.toLowerCase().includes(q)) ||
      trial.id.toString().includes(q)
    );
  }
  // Status filter
  if (filters.value.status) {
    result = result.filter(trial => trial.status === filters.value.status);
  }
  // Schema filter
  if (filters.value.schemaId) {
    result = result.filter(trial => trial.schema_id == filters.value.schemaId);
  }
  // Model filter
  if (filters.value.llmModel) {
    result = result.filter(trial => trial.llm_model === filters.value.llmModel);
  }
  // Prompt filter
  if (filters.value.promptId) {
    result = result.filter(trial => trial.prompt_id == filters.value.promptId);
  }
  // Date range filter
  if (filters.value.dateRange) {
    const now = new Date();
    let startDate = null;
    switch (filters.value.dateRange) {
      case 'today':
        startDate = new Date();
        startDate.setHours(0, 0, 0, 0);
        break;
      case 'week':
        startDate = new Date();
        startDate.setDate(now.getDate() - 7);
        break;
      case 'month':
        startDate = new Date();
        startDate.setDate(now.getDate() - 30);
        break;
    }
    if (startDate) {
      result = result.filter(trial => new Date(trial.created_at) >= startDate);
    }
  }
  if (!showCompleted.value) {
    result = result.filter(trial => !['completed', 'failed'].includes(trial.status));
  }
  return result;
});

function openCreateTrialModal() {
  isModalOpen.value = true;
}
async function handleCreateTrial(trialData) {
  try {
    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.push(response.data);
    isModalOpen.value = false;
    startPolling();
    toast.success('Trial created!');
  } catch (e) {
    toast.error('Failed to create trial.');
  }
}

function openRenameModal(trial) {
  editingTrial.value = trial;
  showRenameModal.value = true;
}
async function submitRename({ id, name, description }) {
  try {
    await api.patch(`/project/${props.projectId}/trial/${id}`, { name, description });
    const idx = trials.value.findIndex(t => t.id === id);
    if (idx !== -1) {
      trials.value[idx].name = name;
      trials.value[idx].description = description;
    }
    toast.success('Trial renamed');
    showRenameModal.value = false;
  } catch (e) {
    toast.error('Failed to rename trial');
  }
}
function toggleTrialSelection(id) {
  if (selectedTrials.value.includes(id)) {
    selectedTrials.value = selectedTrials.value.filter(tid => tid !== id);
  } else {
    selectedTrials.value.push(id);
  }
}
function openBatchModal(action) {
  batchAction.value = action;
  showBatchModal.value = true;
}
function handleBatchActionComplete(updated = false) {
  selectedTrials.value = [];
  showBatchModal.value = false;
  if (updated) {
    fetchTrials().then(() => startPolling());
  }
}

function confirmDeleteTrial(trial) {
  trialToDelete.value = trial;
  isConfirmDialogOpen.value = true;
}
async function deleteTrial() {
  if (!trialToDelete.value) return;
  try {
    await api.delete(`/project/${props.projectId}/trial/${trialToDelete.value.id}`);
    trials.value = trials.value.filter(trial => trial.id !== trialToDelete.value.id);
    toast.success('Trial deleted');
  } catch (e) {
    toast.error('Failed to delete trial');
  } finally {
    isConfirmDialogOpen.value = false;
    trialToDelete.value = null;
  }
}
async function retryTrial(trial) {
  try {
    const data = {
      schema_id: trial.schema_id,
      prompt_id: trial.prompt_id,
      document_ids: trial.document_ids,
      llm_model: trial.llm_model,
      api_key: trial.api_key,
      base_url: trial.base_url,
      advanced_options: trial.advanced_options || {},
    };
    const response = await api.post(`/project/${props.projectId}/trial`, data);
    trials.value.push(response.data);
    toast.success('Trial restarted');
    startPolling();
  } catch (e) {
    toast.error('Failed to restart trial');
  }
}
function openDownloadModal(trial) {
  trialToDownload.value = trial;
  showDownloadModal.value = true;
}

function viewTrialResults(trial) {
  selectedTrialId.value = trial.id;
  showTrialResultsModal.value = true;
}
function viewTrialSchema(trial) {
  selectedSchema.value = schemas.value.find(s => s.id === trial.schema_id);
  showSchemaModal.value = true;
}
function viewTrialPrompt(trial) {
  selectedPrompt.value = prompts.value.find(p => p.id === trial.prompt_id);
  showPromptModal.value = true;
}

function getActiveTrialIds() {
  return trials.value.filter(trial =>
    trial.status === 'pending' || trial.status === 'processing'
  ).map(trial => trial.id);
}

function startPolling() {
  if (isPollingActive.value) return;
  isPollingActive.value = true;
  pollTrials();
}

function stopPolling() {
  isPollingActive.value = false;
  if (pollInterval.value) {
    clearTimeout(pollInterval.value);
    pollInterval.value = null;
  }
}

async function pollTrials() {
  if (!isPollingActive.value) return;

  const activeIds = getActiveTrialIds();
  if (activeIds.length === 0) {
    stopPolling();
    return;
  }

  try {
    const updates = await Promise.all(
      activeIds.map(id =>
        api.get(`/project/${props.projectId}/trial/${id}`).then(r => r.data).catch(() => null)
      )
    );
    for (const updated of updates) {
      if (updated) {
        const idx = trials.value.findIndex(t => t.id === updated.id);
        if (idx !== -1) trials.value[idx] = updated;
      }
    }
  } catch (e) {
    // Silently fail: polling should be robust
  }
  pollInterval.value = setTimeout(pollTrials, POLL_INTERVAL_MS);
}


onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, promptsResponse, trialsResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/document`),
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/prompt`),
      api.get(`/project/${props.projectId}/trial`)
    ]);
    documents.value = documentsResponse.data;
    schemas.value = schemasResponse.data;
    prompts.value = promptsResponse.data;
    trials.value = trialsResponse.data;
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
    startPolling(); // Start polling once trials are loaded
  }
});

onUnmounted(() => {
  stopPolling();
});

</script>
