<template>
  <div
    v-if="isModal"
    class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
    @click="$emit('close')"
  >
    <div
      class="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[95vh] flex flex-col"
      @click.stop
    >
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-xl font-semibold">Trial Results</h3>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="overflow-y-auto flex-1 p-6">
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
            <p v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-2xl text-gray-400">
              Please wait for the trial to complete.
            </p>
          </div>

          <!-- Accordion-style results -->
          <div v-else class="grid grid-cols-1 gap-4">
            <div v-for="(result, index) in trial.results" :key="index"
                class="bg-white shadow-sm rounded-lg overflow-hidden">
              <div
                @click="toggleResultExpansion(index)"
                class="p-4 cursor-pointer border-b flex justify-between items-center hover:bg-gray-50"
              >
                <h3 class="font-medium">Document #{{ index + 1 }}</h3>
                <svg
                  class="w-5 h-5 transition-transform"
                  :class="{ 'transform rotate-180': expandedResults[index] }"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </div>

              <div v-if="expandedResults[index]" class="p-4">
                <div
                  class="flex gap-4"
                  :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
                >
                  <!-- Document content panel -->
                  <div class="bg-gray-50 p-4 rounded-md overflow-auto flex-1 max-h-[500px]">
                    <h4 class="text-sm font-medium mb-2">Document Content</h4>
                    <pre class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContents[index] }}</pre>
                  </div>

                  <!-- Extracted data panel -->
                  <div class="bg-gray-50 p-4 rounded-md overflow-auto flex-1 max-h-[500px]">
                    <h4 class="text-sm font-medium mb-2">Extracted Information</h4>
                    <JsonViewer :data="result.result" />
                  </div>
                </div>

                <div class="mt-4 flex justify-end">
                  <button
                    @click="toggleViewMode(index)"
                    class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
                  >
                    {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="text-center py-12">
          <p class="text-gray-500">Trial not found</p>
          <button @click="$emit('close')" class="mt-4 inline-block text-blue-500 hover:text-blue-700">
            Return to trials
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="trial-results container mx-auto px-4 py-6">
    <div class="mb-6 flex items-center">
      <button @click="goBack" class="mr-4 text-gray-500 hover:text-gray-700">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd"
            d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
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
        <p v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-2xl text-gray-400">
          Please wait for the trial to complete.
        </p>
      </div>

      <!-- Accordion-style results -->
      <div v-else class="grid grid-cols-1 gap-4">
        <div v-for="(result, index) in trial.results" :key="index"
            class="bg-white shadow-sm rounded-lg overflow-hidden">
          <div
            @click="toggleResultExpansion(index)"
            class="p-4 cursor-pointer border-b flex justify-between items-center hover:bg-gray-50"
          >
            <h3 class="font-medium">Document #{{ index + 1 }}</h3>
            <svg
              class="w-5 h-5 transition-transform"
              :class="{ 'transform rotate-180': expandedResults[index] }"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </div>

          <div v-if="expandedResults[index]" class="p-4">
            <div
              class="flex gap-4"
              :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
            >
              <!-- Document content panel -->
              <div class="bg-gray-50 p-4 rounded-md overflow-auto flex-1 max-h-[500px]">
                <h4 class="text-sm font-medium mb-2">Document Content</h4>
                <pre class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContents[index] }}</pre>
              </div>

              <!-- Extracted data panel -->
              <div class="bg-gray-50 p-4 rounded-md overflow-auto flex-1 max-h-[500px]">
                <h4 class="text-sm font-medium mb-2">Extracted Information</h4>
                <JsonViewer :data="result.result" />
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <button
                @click="toggleViewMode(index)"
                class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
              >
                {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="text-center py-12">
      <p class="text-gray-500">Trial not found</p>
      <router-link :to="`/projects/${props.projectId}/trials`" class="mt-4 inline-block text-blue-500 hover:text-blue-700">
        Return to trials
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters.js';
import { useToast } from 'vue-toastification';
import JsonViewer from './JsonViewer.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  trialId: {
    type: [String, Number],
    required: true
  },
  isModal: {
    type: Boolean,
    default: false
  }
});

defineEmits(['close']);

const route = useRoute();
const router = useRouter();
const toast = useToast();

const trialId = computed(() => props.trialId || parseInt(route.params.trialId));
const isLoading = ref(true);
const error = ref(null);
const trial = ref(null);
const selectedResultIndex = ref(0);

// New state variables for accordion and document content
const expandedResults = ref({});
const documentContents = ref({});
const viewMode = ref({}); // 'vertical' or 'horizontal'

// Fetch trial data
const fetchData = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Load trial data
    const response = await api.get(`/project/${props.projectId}/trial/${trialId.value}`);
    trial.value = response.data;
  } catch (err) {
    console.error('Error loading trial data:', err);
    error.value = err.message || 'Failed to load trial data';
  } finally {
    isLoading.value = false;
  }
};

// Navigation functions
const goBack = () => {
  if (props.isModal) {
    $emit('close');
  } else {
    router.push(`/projects/${props.projectId}/trials`);
  }
};

// Toggle results expansion
const toggleResultExpansion = async (index) => {
  // Toggle expansion state
  expandedResults.value[index] = !expandedResults.value[index];

  // Set default view mode if not set
  if (viewMode.value[index] === undefined) {
    viewMode.value[index] = 'horizontal';
  }

  // Load document content if expanded and not already loaded
  if (expandedResults.value[index] && !documentContents.value[index]) {
    try {
      const docId = trial.value.document_ids[index];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      documentContents.value[index] = response.data.text || 'No text content available';
    } catch (err) {
      documentContents.value[index] = 'Error loading document content';
      console.error(err);
    }
  }
};

// Toggle view mode between vertical and horizontal
const toggleViewMode = (index) => {
  viewMode.value[index] = viewMode.value[index] === 'vertical' ? 'horizontal' : 'vertical';
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

<style>
.json-viewer {
  font-family: monospace;
  font-size: 14px;
}

.json-item {
  margin: 2px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
}

.toggle-icon {
  width: 16px;
  display: inline-block;
}

.key-name {
  color: #881391;
  margin-right: 5px;
}

.json-value {
  color: #1a1aa6;
}

.json-children {
  border-left: 1px dashed #ccc;
  padding-left: 1rem;
}
</style>
