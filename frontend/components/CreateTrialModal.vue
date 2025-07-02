<script setup>
import { ref, computed, watch } from 'vue';
import { formatDate } from '@/utils/formatters';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

const toast = useToast();

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
  }
});

const emit = defineEmits(['close', 'create']);

const trialData = ref({
  schema_id: '',
  document_ids: [],
  llm_model: '',
  api_key: '',
  base_url: ''
});

const advancedOptionsVisible = ref(false);
const searchTerm = ref('');
const availableModels = ref([]);
const isLoadingModels = ref(false);
const isTestingConnection = ref(false);
const isTestingModel = ref(false);
const connectionTested = ref(false);
const connectionValid = ref(false);
const modelTested = ref(false);
const modelValid = ref(false);
const systemConfigError = ref(null);
const customConfigError = ref(null);
const modelTestError = ref(null);
const hasSystemConfig = ref(true);

// Test connection first, then load models
const testAndLoadModels = async (apiKey = '', baseUrl = '') => {
  console.log('testAndLoadModels called with:', { apiKey: !!apiKey, baseUrl: !!baseUrl });

  isTestingConnection.value = true;
  connectionTested.value = false;
  connectionValid.value = false;
  availableModels.value = [];
  systemConfigError.value = null;
  customConfigError.value = null;

  // Reset model testing when connection changes
  resetModelTest();

  try {
    const params = {};
    if (apiKey.trim()) params.api_key = apiKey.trim();
    if (baseUrl.trim()) params.base_url = baseUrl.trim();

    console.log('Testing connection with params:', params);
    const testResponse = await api.post('/project/llm/test-connection', null, { params });

    console.log('Connection test response:', testResponse.data);

    if (testResponse.data.success) {
      connectionValid.value = true;
      connectionTested.value = true;

      // Connection successful, now load models
      await loadModels(apiKey, baseUrl);

      if (availableModels.value.length === 0) {
        const errorMsg = 'Connection successful but no models available';
        if (hasCustomApiSettings.value) {
          customConfigError.value = errorMsg;
          toast.error(errorMsg);
        } else {
          systemConfigError.value = errorMsg;
          toast.error('No models available. Please contact your administrator.');
        }
      } else {
        toast.success(`Connection successful. Loaded ${availableModels.value.length} models.`);
      }
    } else {
      connectionValid.value = false;
      connectionTested.value = true;

      const errorMsg = testResponse.data.message || 'Connection test failed';

      if (hasCustomApiSettings.value) {
        customConfigError.value = errorMsg;
        toast.error(errorMsg);
      } else {
        systemConfigError.value = errorMsg;
        hasSystemConfig.value = false;

        if (testResponse.data.error_type === 'incomplete_config') {
          toast.error('System LLM configuration is incomplete. Please contact your administrator or provide custom API settings.');
        } else {
          toast.error(`System LLM configuration error: ${errorMsg}. Please contact your administrator.`);
        }
      }
    }
  } catch (error) {
    console.error('Connection test failed:', error);
    connectionValid.value = false;
    connectionTested.value = true;

    const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message;

    if (hasCustomApiSettings.value) {
      customConfigError.value = errorMsg;
      toast.error(`Connection failed: ${errorMsg}`);
    } else {
      systemConfigError.value = errorMsg;
      hasSystemConfig.value = false;
      toast.error(`System configuration error: ${errorMsg}. Please contact your administrator.`);
    }
  } finally {
    isTestingConnection.value = false;
  }
};

// Load models from API
const loadModels = async (apiKey = '', baseUrl = '') => {
  console.log('loadModels called with:', { apiKey: !!apiKey, baseUrl: !!baseUrl });
  isLoadingModels.value = true;

  try {
    const params = {};
    if (apiKey.trim()) params.api_key = apiKey.trim();
    if (baseUrl.trim()) params.base_url = baseUrl.trim();

    console.log('Making API call to /project/llm/models with params:', params);
    const response = await api.get('/project/llm/models', { params });

    console.log('API response:', response.data);

    if (response.data.success) {
      availableModels.value = response.data.models || [];
      console.log('Loaded models:', availableModels.value);

      // Clear previous model selection when models change
      if (trialData.value.llm_model && !availableModels.value.includes(trialData.value.llm_model)) {
        trialData.value.llm_model = '';
        resetModelTest();
      }
    } else {
      console.error('API returned error:', response.data.message);
      availableModels.value = [];
      throw new Error(response.data.message || 'Failed to load models');
    }
  } catch (error) {
    console.error('Failed to load models:', error);
    availableModels.value = [];
    throw error;
  } finally {
    isLoadingModels.value = false;
  }
};

// Reset model test state
const resetModelTest = () => {
  modelTested.value = false;
  modelValid.value = false;
  modelTestError.value = null;
};

// Test specific model - MANDATORY before submission
const testSelectedModel = async () => {
  if (!trialData.value.llm_model) {
    toast.error('Please select a model first');
    return;
  }

  isTestingModel.value = true;
  modelTested.value = false;
  modelValid.value = false;
  modelTestError.value = null;

  try {
    const params = {
      llm_model: trialData.value.llm_model
    };

    if (trialData.value.api_key.trim()) {
      params.api_key = trialData.value.api_key.trim();
    }
    if (trialData.value.base_url.trim()) {
      params.base_url = trialData.value.base_url.trim();
    }

    console.log('Testing model with params:', params);
    const response = await api.post('/project/llm/test-model', null, { params });

    console.log('Model test response:', response.data);

    modelTested.value = true;

    if (response.data.success) {
      modelValid.value = true;
      toast.success(`Model '${trialData.value.llm_model}' is available and working!`);
    } else {
      modelValid.value = false;
      modelTestError.value = response.data.message || 'Model test failed';

      if (response.data.error_type === 'model_not_found') {
        toast.error(`Model '${trialData.value.llm_model}' is not available. Please select a different model.`);
      } else {
        toast.error(response.data.message || 'Model test failed');
      }
    }
  } catch (error) {
    console.error('Model test failed:', error);
    modelTested.value = true;
    modelValid.value = false;

    const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message;
    modelTestError.value = errorMsg;
    toast.error(`Model test failed: ${errorMsg}`);
  } finally {
    isTestingModel.value = false;
  }
};

// Initialize form when modal opens
const initializeForm = () => {
  console.log('Initializing form...');

  trialData.value = {
    schema_id: props.schemas.length > 0 ? props.schemas[0].id.toString() : '',
    document_ids: [],
    llm_model: '',
    api_key: '',
    base_url: ''
  };

  searchTerm.value = '';
  connectionTested.value = false;
  connectionValid.value = false;
  systemConfigError.value = null;
  customConfigError.value = null;
  hasSystemConfig.value = true;
  availableModels.value = [];
  resetModelTest();

  // Always test connection and load models when modal opens
  testAndLoadModels();
};

// Watch for modal open/close
watch(() => props.open, (newValue) => {
  console.log('Modal open changed to:', newValue);
  if (newValue) {
    initializeForm();
  }
}, { immediate: true });

// Watch for changes in custom API settings
watch([() => trialData.value.api_key, () => trialData.value.base_url], () => {
  connectionTested.value = false;
  connectionValid.value = false;
  customConfigError.value = null;
  resetModelTest();

  // Clear model selection when settings change
  trialData.value.llm_model = '';
  availableModels.value = [];

  // If custom settings are provided, test them
  if (hasCustomApiSettings.value) {
    // Debounce the API call to avoid too many requests while typing
    clearTimeout(window.customSettingsTimeout);
    window.customSettingsTimeout = setTimeout(() => {
      testAndLoadModels(trialData.value.api_key, trialData.value.base_url);
    }, 1000);
  } else {
    // If custom settings are cleared, test system config
    testAndLoadModels();
  }
});

// Watch for model selection changes - reset model test when model changes
watch(() => trialData.value.llm_model, (newModel, oldModel) => {
  if (newModel !== oldModel) {
    resetModelTest();
  }
});

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

// Check if custom API settings are provided
const hasCustomApiSettings = computed(() => {
  return trialData.value.api_key.trim() || trialData.value.base_url.trim();
});

// Check if system has valid configuration
const hasValidSystemConfig = computed(() => {
  return hasSystemConfig.value && !systemConfigError.value && !hasCustomApiSettings.value;
});

// Check if custom configuration is valid
const hasValidCustomConfig = computed(() => {
  return hasCustomApiSettings.value && connectionTested.value && connectionValid.value && !customConfigError.value;
});

// Check if any configuration is valid
const hasValidConfig = computed(() => {
  return hasValidSystemConfig.value || hasValidCustomConfig.value;
});

// Form validation - NOW REQUIRES MODEL TESTING
const isFormValid = computed(() => {
  const basicValidation = trialData.value.schema_id &&
                         trialData.value.document_ids.length > 0 &&
                         trialData.value.llm_model &&
                         availableModels.value.length > 0;

  // Must have valid configuration (either system or custom)
  const configValid = hasValidConfig.value;

  // MANDATORY: Model must be tested and valid
  const modelValidated = modelTested.value && modelValid.value;

  return basicValidation && configValid && modelValidated;
});

// Get current error message
const currentError = computed(() => {
  if (hasCustomApiSettings.value) {
    return customConfigError.value;
  }
  return systemConfigError.value;
});

// Get configuration status
const configStatus = computed(() => {
  if (isTestingConnection.value || isLoadingModels.value) {
    return { type: 'loading', message: 'Testing configuration...' };
  }

  if (hasCustomApiSettings.value) {
    if (!connectionTested.value) {
      return { type: 'warning', message: 'Custom API settings need to be tested' };
    }
    if (!connectionValid.value) {
      return { type: 'error', message: customConfigError.value || 'Custom API connection failed' };
    }
    if (availableModels.value.length === 0) {
      return { type: 'error', message: 'No models available with current settings' };
    }
    return { type: 'success', message: `Custom API connected - ${availableModels.value.length} models available` };
  } else {
    if (!hasSystemConfig.value) {
      return { type: 'error', message: 'System configuration incomplete - please contact administrator or use custom settings' };
    }
    if (systemConfigError.value) {
      return { type: 'error', message: `System configuration error - please contact administrator: ${systemConfigError.value}` };
    }
    if (availableModels.value.length === 0) {
      return { type: 'error', message: 'No models available - please contact administrator' };
    }
    return { type: 'success', message: `System configuration active - ${availableModels.value.length} models available` };
  }
});

// Get model test status
const modelTestStatus = computed(() => {
  if (!trialData.value.llm_model) {
    return { type: 'none', message: 'Select a model first' };
  }

  if (isTestingModel.value) {
    return { type: 'loading', message: 'Testing model availability...' };
  }

  if (!modelTested.value) {
    return { type: 'warning', message: 'Model must be tested before creating trial' };
  }

  if (!modelValid.value) {
    return { type: 'error', message: modelTestError.value || 'Model test failed' };
  }

  return { type: 'success', message: `Model '${trialData.value.llm_model}' is available` };
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

// Handle create submission
const handleSubmit = () => {
  if (!isFormValid.value) {
    if (!modelTested.value || !modelValid.value) {
      toast.error('Please test the selected model before creating the trial');
    }
    return;
  }

  const formData = {
    schema_id: parseInt(trialData.value.schema_id),
    document_ids: trialData.value.document_ids,
    llm_model: trialData.value.llm_model
  };

  // Only include custom API settings if they are provided and not empty
  if (trialData.value.api_key.trim()) {
    formData.api_key = trialData.value.api_key.trim();
  }
  if (trialData.value.base_url.trim()) {
    formData.base_url = trialData.value.base_url.trim();
  }

  emit('create', formData);
};
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
    @click="emit('close')"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col" @click.stop>
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-xl font-semibold">Start New Trial</h3>
        <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-6 overflow-y-auto flex-1">
        <!-- Configuration Status -->
        <div class="mb-6">
          <div
            :class="[
              'p-4 rounded-md border',
              {
                'bg-blue-50 border-blue-200': configStatus.type === 'loading',
                'bg-yellow-50 border-yellow-200': configStatus.type === 'warning',
                'bg-red-50 border-red-200': configStatus.type === 'error',
                'bg-green-50 border-green-200': configStatus.type === 'success'
              }
            ]"
          >
            <div class="flex items-center gap-2">
              <!-- Loading spinner -->
              <svg v-if="configStatus.type === 'loading'" class="animate-spin w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <!-- Warning icon -->
              <svg v-else-if="configStatus.type === 'warning'" class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <!-- Error icon -->
              <svg v-else-if="configStatus.type === 'error'" class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <!-- Success icon -->
              <svg v-else class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>

              <span
                :class="[
                  'font-medium',
                  {
                    'text-blue-700': configStatus.type === 'loading',
                    'text-yellow-700': configStatus.type === 'warning',
                    'text-red-700': configStatus.type === 'error',
                    'text-green-700': configStatus.type === 'success'
                  }
                ]"
              >
                {{ configStatus.message }}
              </span>
            </div>
          </div>
        </div>

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
          <div class="relative">
            <select
              v-model="trialData.llm_model"
              :disabled="isLoadingModels || isTestingConnection || availableModels.length === 0"
              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="" disabled>
                {{ isLoadingModels || isTestingConnection ? 'Loading models...' :
                   availableModels.length === 0 ? 'No models available' : 'Select a model' }}
              </option>
              <option v-for="model in availableModels" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
            <div v-if="isLoadingModels || isTestingConnection" class="absolute right-3 top-1/2 transform -translate-y-1/2">
              <svg class="animate-spin h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          </div>
        </div>

        <!-- Model Test Section - MANDATORY -->
        <div v-if="trialData.llm_model && hasValidConfig" class="mb-6">
          <div
            :class="[
              'p-4 rounded-md border',
              {
                'bg-blue-50 border-blue-200': modelTestStatus.type === 'loading',
                'bg-yellow-50 border-yellow-200': modelTestStatus.type === 'warning',
                'bg-red-50 border-red-200': modelTestStatus.type === 'error',
                'bg-green-50 border-green-200': modelTestStatus.type === 'success',
                'bg-gray-50 border-gray-200': modelTestStatus.type === 'none'
              }
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <!-- Loading spinner -->
                <svg v-if="modelTestStatus.type === 'loading'" class="animate-spin w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <!-- Warning icon -->
                <svg v-else-if="modelTestStatus.type === 'warning'" class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <!-- Error icon -->
                <svg v-else-if="modelTestStatus.type === 'error'" class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <!-- Success icon -->
                <svg v-else-if="modelTestStatus.type === 'success'" class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <!-- Info icon -->
                <svg v-else class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>

                <div>
                  <h4 class="font-medium text-gray-900">Model Availability Test</h4>
                  <p
                    :class="[
                      'text-sm',
                      {
                        'text-blue-700': modelTestStatus.type === 'loading',
                        'text-yellow-700': modelTestStatus.type === 'warning',
                        'text-red-700': modelTestStatus.type === 'error',
                        'text-green-700': modelTestStatus.type === 'success',
                        'text-gray-600': modelTestStatus.type === 'none'
                      }
                    ]"
                  >
                    {{ modelTestStatus.message }}
                  </p>
                </div>
              </div>

              <button
                @click="testSelectedModel"
                :disabled="isTestingModel || !trialData.llm_model"
                class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <svg v-if="isTestingModel" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ isTestingModel ? 'Testing...' : 'Test Model' }}
              </button>
            </div>

            <div v-if="modelTestStatus.type === 'warning'" class="mt-3 p-3 bg-yellow-100 border border-yellow-200 rounded-md">
              <p class="text-yellow-800 text-sm">
                <strong>Required:</strong> You must test the selected model to ensure it's available before creating a trial.
              </p>
            </div>
          </div>
        </div>

        <!-- Advanced Options Toggle -->
        <div class="mb-6">
          <button
            @click="advancedOptionsVisible = !advancedOptionsVisible"
            class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
          >
            {{ advancedOptionsVisible ? 'Hide custom API settings' : 'Use custom API settings' }}
            <span class="ml-1">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4 transition-transform"
                :class="{ 'rotate-180': advancedOptionsVisible }"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>

          <!-- Custom LLM API Settings -->
          <div v-if="advancedOptionsVisible" class="mt-3 bg-gray-50 p-4 rounded-md">
            <div class="mb-3">
              <p class="text-sm text-gray-600">
                Provide your own API key and base URL to use a different LLM service.
              </p>
            </div>
            <div class="grid grid-cols-1 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  v-model="trialData.api_key"
                  type="password"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., sk-1234567890abcdef..."
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  v-model="trialData.base_url"
                  type="text"
                  class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., https://api.openai.com/v1"
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
              title="Select all visible documents"
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
          class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="!isFormValid"
          :title="!isFormValid ? 'Please ensure all fields are filled, model is tested, and configuration is valid' : ''"
        >
          Start Trial
        </button>
      </div>
    </div>
  </div>
</template>

