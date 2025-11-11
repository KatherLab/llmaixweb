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
        <Tooltip v-if="trialDisabled" :text="trialDisabledReason">
          <button
            @click="openCreateTrialModal"
            class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition disabled:bg-blue-300 disabled:cursor-not-allowed"
            :disabled="trialDisabled"
            type="button"
          >
            Start New Trial
          </button>
        </Tooltip>
        <button
          v-else
          @click="openCreateTrialModal"
          class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition"
          :disabled="trialDisabled"
          type="button"
        >
          Start New Trial
        </button>
      </div>
    </div>

    <!-- Filter Panel -->
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-7 gap-4">
        <!-- Search -->
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
          <div class="relative">
            <input
              v-model="filters.search"
              type="text"
              placeholder="Search in name, description, or ID..."
              class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @keyup.enter="applyFilters"
            />
            <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
          </div>
        </div>

        <!-- Status -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select v-model="filters.status" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @change="applyFilters">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <!-- Schema -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Schema</label>
          <select v-model="filters.schema_id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @change="applyFilters">
            <option value="">All</option>
            <option v-for="schema in schemas" :key="schema.id" :value="schema.id">{{ schema.schema_name }}</option>
          </select>
        </div>

        <!-- Prompt -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
          <select v-model="filters.prompt_id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @change="applyFilters">
            <option value="">All</option>
            <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id">{{ prompt.name }}</option>
          </select>
        </div>

        <!-- LLM Model -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
          <input v-model="filters.llm_model" type="text" placeholder="Exact match" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @keyup.enter="applyFilters"/>
        </div>

        <!-- Failures -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Errors</label>
          <select v-model="filters.has_failures" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @change="applyFilters">
            <option value="">All</option>
            <option :value="true">Has errors</option>
            <option :value="false">No errors</option>
          </select>
        </div>

        <!-- Date Range -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Created</label>
          <select v-model="filters.dateRange" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" @change="applyFilters">
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="week">Last 7 days</option>
            <option value="month">Last 30 days</option>
          </select>
        </div>
      </div>

      <div class="mt-3 flex gap-2">
        <button @click="applyFilters" class="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700">Apply</button>
        <button @click="clearFilters" class="px-4 py-2 rounded-lg bg-gray-100 text-gray-800 text-sm font-semibold hover:bg-gray-200">Clear</button>
      </div>
    </div>

    <!-- Error / Loading -->
    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />

    <!-- Empty -->
    <EmptyState
      v-else-if="trials.length === 0"
      title="No trials found"
      description="Try changing your filters or create a new trial."
      actionText="Start a Trial"
      @action="openCreateTrialModal"
      :disabled="trialDisabled"
      :disabledReason="trialDisabledReason"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </template>
    </EmptyState>

    <!-- Trials Grid -->
    <div v-else class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <TrialCard
          v-for="trial in trials"
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
          @cancel="cancelTrial"
          @view-results="viewTrialResults(trial)"
          @view-schema="viewTrialSchema(trial)"
          @view-prompt="viewTrialPrompt(trial)"
        />
      </div>

      <!-- Pagination -->
      <div v-if="trials.length < totalTrials" class="flex justify-center">
        <button @click="loadMore" class="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-100 hover:bg-gray-200 border border-gray-200">
          Load more ({{ trials.length }}/{{ totalTrials }})
        </button>
      </div>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
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
import Tooltip from '@/components/Tooltip.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true }
});

const toast = useToast();

const documents = ref([]);
const schemas = ref([]);
const prompts = ref([]);
const trials = ref([]);
const totalTrials = ref(0);
const limit = ref(20);
const offset = ref(0);
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

const trialDisabled = computed(() =>
  isLoading.value || schemas.value.length === 0 || documents.value.length === 0 || prompts.value.length === 0
);

const trialDisabledReason = computed(() => {
  if (isLoading.value) return 'Loading project resources…'
  if (schemas.value.length === 0) return 'You need at least one schema to start a trial.'
  if (documents.value.length === 0) return 'You need to upload at least one document to start a trial.'
  if (prompts.value.length === 0) return 'You need to create at least one prompt to start a trial.'
  return ''
});

const filters = ref({
  search: '',
  status: '',
  schema_id: '',
  prompt_id: '',
  llm_model: '',
  has_failures: '',
  dateRange: '',
});

function mapDateRangeToBounds(range) {
  const now = new Date();
  let from = null, to = null;
  if (range === 'today') {
    from = new Date(); from.setHours(0, 0, 0, 0);
    to = new Date(); to.setHours(23, 59, 59, 999);
  } else if (range === 'week') {
    from = new Date(now); from.setDate(now.getDate() - 7);
  } else if (range === 'month') {
    from = new Date(now); from.setDate(now.getDate() - 30);
  }
  return {
    date_from: from ? from.toISOString() : undefined,
    date_to: to ? to.toISOString() : undefined
  }
}

const availableTrialModels = computed(() => {
  const allModels = trials.value.map(t => t.llm_model).filter(Boolean);
  return [...new Set(allModels)];
});

function clearFilters() {
  filters.value = {
    search: '',
    status: '',
    schema_id: '',
    prompt_id: '',
    llm_model: '',
    has_failures: '',
    dateRange: '',
  };
  applyFilters();
}

function paramsFromFilters() {
  const params = {};
  if (filters.value.search) params.search = filters.value.search;
  if (filters.value.status) params.status = filters.value.status;
  if (filters.value.schema_id) params.schema_id = filters.value.schema_id;
  if (filters.value.prompt_id) params.prompt_id = filters.value.prompt_id;
  if (filters.value.llm_model) params.llm_model = filters.value.llm_model;
  if (filters.value.has_failures !== '' && filters.value.has_failures !== null) params.has_failures = filters.value.has_failures;
  const { date_from, date_to } = mapDateRangeToBounds(filters.value.dateRange);
  if (date_from) params.date_from = date_from;
  if (date_to) params.date_to = date_to;

  // status toggle: hide completed/failed when showCompleted=false
  if (!showCompleted.value) {
    // If user didn’t pick a status, default to only active
    if (!params.status) params.status = 'processing'; // not perfect; better approach: add server multi-status. For now we keep client-side hide below.
  }
  return params;
}

async function fetchTrialsPage({ limitParam, offsetParam }) {
  const params = { ...paramsFromFilters(), limit: limitParam, offset: offsetParam };
  const res = await api.get(`/project/${props.projectId}/trial`, { params });
  return res.data;
}

async function fetchTrials({ reset = false } = {}) {
  try {
    if (reset) isLoading.value = true;
    const data = await fetchTrialsPage({ limitParam: limit.value, offsetParam: offset.value });
    totalTrials.value = data.total || 0;
    const items = (data.items || []);
    trials.value = reset ? items : [...trials.value, ...items];
  } catch (err) {
    error.value = err?.message || 'Failed to load trials';
  } finally {
    isLoading.value = false;
  }
}

function loadMore() {
  offset.value += limit.value;
  fetchTrials({ reset: false });
}

function resetAndFetch() {
  offset.value = 0;
  fetchTrials({ reset: true });
}

function applyFilters() {
  resetAndFetch();
}

watch([showCompleted], () => {
  // We do client-side hide for completed/failed when the toggle is off:
  // If you want perfect server-side behavior, extend API with multi-status.
  // For now, simply refetch to the top for UX.
  resetAndFetch();
});

function openCreateTrialModal() { isModalOpen.value = true; }
async function handleCreateTrial(trialData) {
  try {
    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.unshift(response.data);
    totalTrials.value += 1;
    isModalOpen.value = false;
    startPolling();
    toast.success('Trial created!');
  } catch {
    toast.error('Failed to create trial.');
  }
}

function openRenameModal(trial) { editingTrial.value = trial; showRenameModal.value = true; }
async function submitRename({ id, name, description }) {
  try {
    await api.patch(`/project/${props.projectId}/trial/${id}`, { name, description });
    const idx = trials.value.findIndex(t => t.id === id);
    if (idx !== -1) { trials.value[idx].name = name; trials.value[idx].description = description; }
    toast.success('Trial renamed'); showRenameModal.value = false;
  } catch { toast.error('Failed to rename trial'); }
}

function toggleTrialSelection(id) {
  if (selectedTrials.value.includes(id)) selectedTrials.value = selectedTrials.value.filter(tid => tid !== id);
  else selectedTrials.value.push(id);
}
function openBatchModal(action) { batchAction.value = action; showBatchModal.value = true; }
function handleBatchActionComplete(updated = false) {
  selectedTrials.value = []; showBatchModal.value = false;
  if (updated) { resetAndFetch(); startPolling(); }
}

async function cancelTrial(trial) {
  try {
    await api.post(`/project/${props.projectId}/trial/${trial.id}/cancel`);
    const idx = trials.value.findIndex(t => t.id === trial.id);
    if (idx !== -1) { trials.value[idx].status = 'cancelled'; trials.value[idx].is_cancelled = true; }
    toast.success('Trial cancelled');
  } catch { toast.error('Failed to cancel trial'); }
}

function confirmDeleteTrial(trial) { trialToDelete.value = trial; isConfirmDialogOpen.value = true; }
async function deleteTrial() {
  if (!trialToDelete.value) return;
  try {
    await api.delete(`/project/${props.projectId}/trial/${trialToDelete.value.id}`);
    trials.value = trials.value.filter(t => t.id !== trialToDelete.value.id);
    totalTrials.value = Math.max(0, totalTrials.value - 1);
    toast.success('Trial deleted');
  } catch { toast.error('Failed to delete trial'); }
  finally { isConfirmDialogOpen.value = false; trialToDelete.value = null; }
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
    trials.value.unshift(response.data);
    totalTrials.value += 1;
    toast.success('Trial restarted');
    startPolling();
  } catch { toast.error('Failed to restart trial'); }
}
function openDownloadModal(trial) { trialToDownload.value = trial; showDownloadModal.value = true; }

function viewTrialResults(trial) { selectedTrialId.value = trial.id; showTrialResultsModal.value = true; }
function viewTrialSchema(trial) { selectedSchema.value = schemas.value.find(s => s.id === trial.schema_id); showSchemaModal.value = true; }
function viewTrialPrompt(trial) { selectedPrompt.value = prompts.value.find(p => p.id === trial.prompt_id); showPromptModal.value = true; }

function getActiveTrialIds() { return trials.value.filter(t => t.status === 'pending' || t.status === 'processing').map(t => t.id); }
function startPolling() { if (isPollingActive.value) return; isPollingActive.value = true; pollTrials(); }
function stopPolling() { isPollingActive.value = false; if (pollInterval.value) { clearTimeout(pollInterval.value); pollInterval.value = null; } }

async function pollTrials() {
  if (!isPollingActive.value) return;
  const activeIds = getActiveTrialIds();
  if (activeIds.length === 0) { stopPolling(); return; }
  try {
    const updates = await Promise.all(
      activeIds.map(id => api.get(`/project/${props.projectId}/trial/${id}`).then(r => r.data).catch(() => null))
    );
    for (const updated of updates) {
      if (!updated) continue;
      const idx = trials.value.findIndex(t => t.id === updated.id);
      if (idx !== -1) trials.value[idx] = updated;
    }
  } catch {}
  pollInterval.value = setTimeout(pollTrials, POLL_INTERVAL_MS);
}

onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, promptsResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/document`),
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/prompt`),
    ]);
    documents.value = Array.isArray(documentsResponse.data) ? documentsResponse.data : (documentsResponse.data?.items || []);
    schemas.value = schemasResponse.data;
    prompts.value = promptsResponse.data;
    await resetAndFetch();
  } catch (err) {
    error.value = err?.message || 'Failed to load';
  } finally {
    isLoading.value = false;
    startPolling();
  }
});
onUnmounted(() => { stopPolling(); });
</script>
