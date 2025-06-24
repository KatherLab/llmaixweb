<!-- views/TrialResults.vue -->
<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useTrialsStore } from '@/stores/trialsStore';
import { useProjectStore } from '@/stores/projectStore';
import { formatDate } from '@/utils/formatters';
import { useToast } from 'vue-toastification';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const trialsStore = useTrialsStore();
const projectStore = useProjectStore();
const { currentProject } = storeToRefs(projectStore);

const projectId = computed(() => parseInt(route.params.id));
const trialId = computed(() => parseInt(route.params.trialId));
const isLoading = ref(true);
const error = ref(null);
const trial = ref(null);
const selectedResultIndex = ref(0);

// Fetch trial data
const fetchData = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Load project if not already loaded
    if (!currentProject.value || currentProject.value.id !== projectId.value) {
      await projectStore.fetchProject(projectId.value);
    }

    // Load trial data
    trial.value = await trialsStore.fetchTrial(projectId.value, trialId.value);
  } catch (err) {
    console.error('Error loading trial data:', err);
    error.value = err.message || 'Failed to load trial data';
  } finally {
    isLoading.value = false;
  }
};

// Navigation functions
const goBack = () => {
  router.push(`/projects/${projectId.value}/trials`);
};

// Format JSON for display
const prettyJson = (obj) => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return 'Invalid JSON';
  }
};

// Get currently selected result
const currentResult = computed(() => {
  if (!trial.value?.results || trial.value.results.length === 0) {
    return null;
  }

  return trial.value.results[selectedResultIndex.value] || trial.value.results[0];
});

// Load data on mount
onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="trial-results container mx-auto px-4 py-6">
    <div class="mb-6 flex items-center">
      <button @click="goBack" class="mr-4 text-gray-500 hover:text-gray-700">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd"
            d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L4.414 9H17a1 1 0 110 2H4.414l5.293 5.293a1 1 0 010 1.414z"
            clip-rule="evenodd" />
        </svg>
      </button>
      <h1 class="text-2xl font-bold">Trial Results</h1>
    </div>

    <div v-if="isLoading" class="text-center py-12">
      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <p class="mt-2 text-gray-500">Loading trial results...</p>
    </div>

    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{{ error }}</p>
        </div>
      </div>
    </div>

    <template v-else-if="trial">
      <!-- Trial information -->
      <div class="bg-white shadow-sm rounded-lg p-4 mb-6">
        <div class="flex flex-col md:flex-row md:justify-between">
          <div>
            <h2 class="text-lg font-medium">Trial #{{ trial.id }}</h2>
            <div class="text-sm text-gray-500 mt-1">
              <div>Started: {{ formatDate(trial.created_at, true) }}</div>
              <div>Status: <span :class="{
                  'text-green-600': trial.status === 'completed',
                  'text-blue-600': trial.status === 'processing',
                  'text-yellow-600': trial.status === 'pending',
                  'text-red-600': trial.status === 'failed'
                }">{{ trial.status }}</span>
              </div>
              <div>Model: {{ trial.llm_model }}</div>
            </div>
          </div>
          <div class="mt-4 md:mt-0">
            <div class="text-sm">
              <div class="font-medium">{{ trial.results?.length || 0 }} documents processed</div>
            </div>
          </div>
        </div>
      </div>

      <!-- No results message -->
      <div v-if="!trial.results || trial.results.length === 0" class="text-center py-8 bg-gray-50 rounded-lg">
        <p class="text-gray-500">No results available for this trial.</p>
        <p v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-gray-400">
          Please wait for the trial to complete.
        </p>
      </div>

      <!-- Results display -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- Results navigation sidebar -->
        <div class="bg-white shadow-sm rounded-lg p-4 lg:col-span-1">
          <h3 class="font-medium mb-3">Documents</h3>
          <div class="space-y-2 max-h-96 overflow-y-auto">
            <button v-for="(result, index) in trial.results" :key="index"
              @click="selectedResultIndex = index"
              :class="[
                'block w-full text-left p-2 rounded text-sm',
                selectedResultIndex === index
                  ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500'
                  : 'text-gray-700 hover:bg-gray-50'
              ]">
              Document #{{ index + 1 }}
            </button>
          </div>
        </div>

        <!-- Selected result display -->
        <div class="bg-white shadow-sm rounded-lg p-4 lg:col-span-3">
          <div v-if="currentResult">
            <h3 class="font-medium mb-3">Extracted Information</h3>
            <div class="bg-gray-50 p-4 rounded-md overflow-x-auto">
              <pre class="text-xs text-gray-800">{{ prettyJson(currentResult.result) }}</pre>
            </div>
          </div>
          <div v-else class="text-center py-8">
            <p class="text-gray-500">Select a document to view results</p>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="text-center py-12">
      <p class="text-gray-500">Trial not found</p>
      <router-link :to="`/projects/${projectId}/trials`" class="mt-4 inline-block text-blue-500 hover:text-blue-700">
        Return to trials
      </router-link>
    </div>
  </div>
</template>
