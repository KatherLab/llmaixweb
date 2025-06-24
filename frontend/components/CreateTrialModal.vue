<script setup>
import { ref, computed } from 'vue';
import { formatDate } from '@/utils/formatters';

const props = defineProps({
  open: {
    type: Boolean,
    required: true
  },
  documents: {
    type: Array,
    required: true
  },
  schemas: {
    type: Array,
    required: true
  },
  models: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['close', 'create']);

const trialData = ref({
  schema_id: '',
  document_ids: [],
  llm_model: 'Llama-4-Maverick-17B-128E-Instruct-FP8',
  api_key: 'sk-dnrTNqmkgvyVKRHPw_iqPA',
  base_url: 'http://pluto/v1'
});

const advancedOptionsVisible = ref(false);
const searchTerm = ref('');

// Reset form when modal is opened
const resetForm = () => {
  trialData.value = {
    schema_id: props.schemas.length > 0 ? props.schemas[0].id.toString() : '',
    document_ids: [],
    llm_model: 'Llama-4-Maverick-17B-128E-Instruct-FP8',
    api_key: 'sk-dnrTNqmkgvyVKRHPw_iqPA',
    base_url: 'http://pluto/v1'
  };
  searchTerm.value = '';
};

// Filter documents based on search term
const filteredDocuments = computed(() => {
  if (!searchTerm.value) {
    return props.documents;
  }

  const term = searchTerm.value.toLowerCase();
  return props.documents.filter(doc => {
    const fileName = doc.original_file?.file_name || '';
    return fileName.toLowerCase().includes(term);
  });
});

const selectedSchema = computed(() => {
  if (!trialData.value.schema_id) return null;
  return props.schemas.find(schema => schema.id.toString() === trialData.value.schema_id);
});

// Toggle document selection
const toggleDocumentSelection = (docId) => {
  const index = trialData.value.document_ids.indexOf(docId);
  if (index === -1) {
    trialData.value.document_ids.push(docId);
  } else {
    trialData.value.document_ids.splice(index, 1);
  }
};

// Select all documents
const selectAllDocuments = () => {
  trialData.value.document_ids = filteredDocuments.value.map(doc => doc.id);
};

// Clear document selection
const clearDocumentSelection = () => {
  trialData.value.document_ids = [];
};

// Form validation
const isFormValid = computed(() => {
  return trialData.value.schema_id && trialData.value.document_ids.length > 0;
});

// Handle create submission
const handleSubmit = () => {
  if (!isFormValid.value) return;

  const formData = {
    ...trialData.value,
    schema_id: parseInt(trialData.value.schema_id)
  };

  emit('create', formData);
  resetForm();
};

// Initialize the form when component is mounted
resetForm();
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-xl font-semibold">Start New Trial</h3>
        <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-6 overflow-y-auto flex-1">
        <!-- Schema Selection -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">Select Schema</label>
          <select
            v-model="trialData.schema_id"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option v-for="schema in schemas" :key="schema.id" :value="schema.id.toString()">
              {{ schema.schema_name }}
            </option>
          </select>
        </div>

        <!-- Schema Preview -->
        <div v-if="selectedSchema" class="mb-6 p-4 bg-gray-50 rounded-md">
          <h4 class="font-medium mb-2">Schema Definition:</h4>
          <pre class="text-xs overflow-auto max-h-24">{{ JSON.stringify(selectedSchema.schema_definition, null, 2) }}</pre>
        </div>

        <!-- Model Selection -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">Select LLM Model</label>
          <select
            v-model="trialData.llm_model"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option v-for="model in models" :key="model" :value="model">
              {{ model }}
            </option>
          </select>
        </div>

        <!-- Advanced Options Toggle -->
        <div class="mb-6">
          <button
            @click="advancedOptionsVisible = !advancedOptionsVisible"
            class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
          >
            {{ advancedOptionsVisible ? 'Hide advanced options' : 'Show advanced options' }}
            <span class="ml-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>

          <!-- LLM API Settings -->
          <div v-if="advancedOptionsVisible" class="mt-3 bg-gray-50 p-4 rounded-md">
            <div class="grid grid-cols-1 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  v-model="trialData.api_key"
                  type="text"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter API Key"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  v-model="trialData.base_url"
                  type="text"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter Base URL"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Document Selection -->
        <div class="mb-6">
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">Select Documents</label>
            <span class="text-sm text-gray-500">{{ trialData.document_ids.length }} selected</span>
          </div>

          <div class="flex gap-2 mb-2">
            <input
              v-model="searchTerm"
              type="text"
              placeholder="Search documents..."
              class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />

            <button
              @click="selectAllDocuments"
              class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
              title="Select all documents"
            >
              Select All
            </button>

            <button
              @click="clearDocumentSelection"
              class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
              title="Clear selection"
            >
              Clear
            </button>
          </div>

          <div class="border rounded-md overflow-hidden">
            <div v-if="filteredDocuments.length === 0" class="p-4 text-center text-gray-500">
              No documents match your search criteria
            </div>

            <div v-else class="max-h-60 overflow-y-auto">
              <div
                v-for="doc in filteredDocuments"
                :key="doc.id"
                :class="[
                  'p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 flex items-center',
                  {'bg-blue-50': trialData.document_ids.includes(doc.id)}
                ]"
                @click="toggleDocumentSelection(doc.id)"
              >
                <input
                  type="checkbox"
                  :checked="trialData.document_ids.includes(doc.id)"
                  class="mr-3"
                  @click.stop
                />

                <div class="flex-1">
                  <div class="font-medium">{{ doc.original_file?.file_name || `Document #${doc.id}` }}</div>
                  <div class="text-xs text-gray-500">
                    Method: {{ doc.preprocessing_method || 'N/A' }} •
                    Created: {{ formatDate(doc.created_at) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t flex justify-end gap-2">
        <button @click="emit('close')" class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md">
          Cancel
        </button>
        <button
          @click="handleSubmit"
          class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:bg-blue-300"
          :disabled="!isFormValid"
        >
          Start Trial
        </button>
      </div>
    </div>
  </div>
</template>
