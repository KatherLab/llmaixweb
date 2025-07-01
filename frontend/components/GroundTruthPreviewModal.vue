<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import JsonViewer from '@/components/JsonViewer.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  groundTruth: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close', 'configured']);

const toast = useToast();
const isLoading = ref(false);
const isSaving = ref(false);
const isLoadingSuggestions = ref(false);
const error = ref(null);

// Data
const schemas = ref([]);
const selectedSchemaId = ref('');
const schemaFields = ref({});
const groundTruthPreview = ref(null);
const fieldMappings = ref([]);
const existingMappings = ref({}); // Store mappings per schema

// Debug logging
const debugLog = (message, data = null) => {
  console.log(`[GroundTruthPreview] ${message}`, data);
};

// Computed properties
const groundTruthFields = computed(() => {
  if (!groundTruthPreview.value?.fields) return [];
  return groundTruthPreview.value.fields;
});

const groundTruthSamples = computed(() => {
  if (!groundTruthPreview.value?.sample_values) return {};
  return groundTruthPreview.value.sample_values;
});

const previewData = computed(() => {
  if (!groundTruthPreview.value?.preview_data) return [];

  // Convert the object with numeric keys to an array
  const data = groundTruthPreview.value.preview_data;
  return Object.keys(data)
    .sort((a, b) => parseInt(a) - parseInt(b))
    .map(key => data[key]);
});

const availableSchemaFields = computed(() => {
  const usedFields = new Set(fieldMappings.value.map(m => m.schema_field).filter(Boolean));
  return Object.keys(schemaFields.value || {}).filter(field => !usedFields.has(field));
});

const canSave = computed(() => {
  return selectedSchemaId.value && fieldMappings.value.length > 0 &&
         fieldMappings.value.every(mapping =>
           mapping.schema_field && mapping.ground_truth_field
         );
});

const canAddMapping = computed(() => {
  return availableSchemaFields.value.length > 0;
});

const hasMappingForSchema = computed(() => {
  return selectedSchemaId.value && existingMappings.value[selectedSchemaId.value]?.length > 0;
});

// Load initial data
const fetchInitialData = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    debugLog('Loading initial data...');

    // Load schemas and ground truth preview in parallel
    const [schemasResponse, previewResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/groundtruth/${props.groundTruth.id}/preview`)
    ]);

    schemas.value = schemasResponse.data;
    groundTruthPreview.value = previewResponse.data;

    debugLog('Schemas loaded:', schemas.value);
    debugLog('Ground truth preview loaded:', groundTruthPreview.value);

    // Load existing mappings for all schemas
    await loadAllExistingMappings();

  } catch (err) {
    error.value = `Failed to load data: ${err.message}`;
    debugLog('Error loading initial data:', err);
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

// Load existing mappings for all schemas
const loadAllExistingMappings = async () => {
  debugLog('Loading existing mappings for all schemas...');

  const mappingPromises = schemas.value.map(async (schema) => {
    try {
      const response = await api.get(
        `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${schema.id}/mapping`
      );
      existingMappings.value[schema.id] = response.data;
      debugLog(`Loaded mappings for schema ${schema.id}:`, response.data);
    } catch (err) {
      // If no mappings exist, that's okay
      existingMappings.value[schema.id] = [];
      debugLog(`No mappings found for schema ${schema.id}`);
    }
  });

  await Promise.all(mappingPromises);
  debugLog('All existing mappings loaded:', existingMappings.value);
};

// Load schema fields when schema is selected
const onSchemaChange = async () => {
  debugLog('Schema changed to:', selectedSchemaId.value);

  if (!selectedSchemaId.value) {
    schemaFields.value = {};
    fieldMappings.value = [];
    return;
  }

  await Promise.all([
    loadSchemaFields(),
    loadExistingMappings()
  ]);
};

const loadSchemaFields = async () => {
  try {
    debugLog('Loading schema fields for schema:', selectedSchemaId.value);

    const response = await api.get(
      `/project/${props.projectId}/schema/${selectedSchemaId.value}/field_types`
    );
    schemaFields.value = response.data;

    debugLog('Schema fields loaded:', schemaFields.value);
  } catch (err) {
    toast.error(`Failed to load schema fields: ${err.message}`);
    console.error(err);
  }
};

const loadExistingMappings = async () => {
  try {
    debugLog('Loading existing mappings for selected schema:', selectedSchemaId.value);

    const response = await api.get(
      `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${selectedSchemaId.value}/mapping`
    );

    // Convert backend response to frontend format
    fieldMappings.value = response.data.map(mapping => ({
      schema_field: mapping.schema_field,
      ground_truth_field: mapping.ground_truth_field,
      schema_id: parseInt(selectedSchemaId.value),
      field_type: mapping.field_type || 'string',
      comparison_method: mapping.comparison_method || 'exact',
      comparison_options: mapping.comparison_options || getDefaultComparisonOptions('exact')
    }));

    debugLog('Existing mappings loaded and converted:', fieldMappings.value);
  } catch (err) {
    // If no mappings exist, start fresh
    fieldMappings.value = [];
    debugLog('No existing mappings found, starting fresh');
  }
};

// Auto-suggest mappings
const suggestMappings = async () => {
  if (!selectedSchemaId.value) {
    toast.warning('Please select a schema first');
    return;
  }

  debugLog('Starting auto-suggest for schema:', selectedSchemaId.value);

  isLoadingSuggestions.value = true;
  try {
    const response = await api.get(
      `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${selectedSchemaId.value}/mapping/suggest`
    );

    debugLog('Suggestions received:', response.data);

    // Replace current mappings with suggestions
    fieldMappings.value = response.data.map(suggestion => ({
      schema_field: suggestion.schema_field,
      ground_truth_field: suggestion.ground_truth_field,
      schema_id: parseInt(selectedSchemaId.value),
      field_type: suggestion.field_type || 'string',
      comparison_method: suggestion.comparison_method || 'exact',
      comparison_options: suggestion.comparison_options || getDefaultComparisonOptions('exact')
    }));

    debugLog('Field mappings updated:', fieldMappings.value);

    toast.success(`${response.data.length} field mappings suggested`);
  } catch (err) {
    toast.error(`Failed to suggest mappings: ${err.message}`);
    debugLog('Error suggesting mappings:', err);
    console.error(err);
  } finally {
    isLoadingSuggestions.value = false;
  }
};

// Add new mapping
const addMapping = () => {
  if (!canAddMapping.value) {
    toast.warning('No more schema fields available to map');
    return;
  }

  const newMapping = {
    schema_field: '',
    ground_truth_field: '',
    schema_id: parseInt(selectedSchemaId.value),
    field_type: 'string',
    comparison_method: 'exact',
    comparison_options: getDefaultComparisonOptions('exact')
  };

  fieldMappings.value.push(newMapping);
  debugLog('Added new mapping:', newMapping);
  debugLog('Current mappings:', fieldMappings.value);
};

// Remove mapping
const removeMapping = (index) => {
  fieldMappings.value.splice(index, 1);
  debugLog('Removed mapping at index:', index);
  debugLog('Current mappings:', fieldMappings.value);
};

// Update comparison options when method changes
const updateComparisonOptions = (mapping) => {
  mapping.comparison_options = getDefaultComparisonOptions(mapping.comparison_method);
  debugLog('Updated comparison options for mapping:', mapping);
};

// Get default comparison options
const getDefaultComparisonOptions = (method) => {
  switch (method) {
    case 'fuzzy':
      return { threshold: 85 };
    case 'numeric':
      return { tolerance: 0.001, relative: false };
    case 'exact':
      return { case_sensitive: false };
    default:
      return {};
  }
};

// Format preview values
const formatPreviewValue = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string' && value.length > 50) {
    return value.substring(0, 50) + '...';
  }
  return String(value);
};

// Save mappings for the selected schema
const saveMappings = async () => {
  if (!canSave.value) {
    toast.warning('Please select a schema and configure at least one complete field mapping');
    return;
  }

  debugLog('Saving mappings:', fieldMappings.value);

  isSaving.value = true;
  try {
    const mappingsToSave = fieldMappings.value.map(mapping => ({
      schema_field: mapping.schema_field,
      ground_truth_field: mapping.ground_truth_field,
      schema_id: parseInt(selectedSchemaId.value),
      field_type: mapping.field_type,
      comparison_method: mapping.comparison_method,
      comparison_options: mapping.comparison_options
    }));

    debugLog('Mappings to save:', mappingsToSave);

    await api.post(
      `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${selectedSchemaId.value}/mapping`,
      mappingsToSave
    );

    // Update the existing mappings cache
    existingMappings.value[selectedSchemaId.value] = [...fieldMappings.value];

    emit('configured');
    toast.success('Field mappings saved successfully');
  } catch (err) {
    toast.error(`Failed to save mappings: ${err.message}`);
    debugLog('Error saving mappings:', err);
    console.error(err);
  } finally {
    isSaving.value = false;
  }
};

// Delete mappings for the selected schema
const deleteMappings = async () => {
  if (!selectedSchemaId.value || !hasMappingForSchema.value) return;

  if (!confirm('Are you sure you want to delete all field mappings for this schema?')) {
    return;
  }

  try {
    await api.delete(
      `/project/${props.projectId}/groundtruth/${props.groundTruth.id}/schema/${selectedSchemaId.value}/mapping`
    );

    // Clear the mappings
    fieldMappings.value = [];
    existingMappings.value[selectedSchemaId.value] = [];

    toast.success('Field mappings deleted successfully');
  } catch (err) {
    toast.error(`Failed to delete mappings: ${err.message}`);
    console.error(err);
  }
};

onMounted(() => {
  fetchInitialData();
});

// Watch for changes in fieldMappings for debugging
watch(fieldMappings, (newMappings) => {
  debugLog('Field mappings changed:', newMappings);
}, { deep: true });
</script>

<template>
  <!-- The template remains the same as in the previous implementation -->
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-lg shadow-lg w-full max-w-6xl max-h-[95vh] flex flex-col"
        @click.stop
      >
        <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 class="text-lg font-medium text-gray-900">Configure Field Mappings</h3>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="isLoading" class="text-center py-12">
            <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            <p class="mt-2 text-gray-500">Loading ground truth preview...</p>
          </div>

          <div v-else-if="error" class="p-6">
            <div class="bg-red-50 border border-red-200 rounded-md p-4">
              <div class="flex">
                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
                <div class="ml-3">
                  <p class="text-sm text-red-700">{{ error }}</p>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="p-6">
            <!-- Debug info (remove in production) -->
            <div v-if="false" class="mb-4 p-4 bg-gray-100 rounded text-xs">
              <div><strong>Selected Schema ID:</strong> {{ selectedSchemaId }}</div>
              <div><strong>Field Mappings Count:</strong> {{ fieldMappings.length }}</div>
              <div><strong>Available Schema Fields:</strong> {{ availableSchemaFields.length }}</div>
              <div><strong>Ground Truth Fields:</strong> {{ groundTruthFields.length }}</div>
            </div>

            <!-- Schema Selection -->
            <div class="mb-6">
              <label for="schema-select" class="block text-sm font-medium text-gray-700 mb-2">
                Select Schema for Mapping
              </label>
              <div class="flex gap-3 items-center">
                <select
                  id="schema-select"
                  v-model="selectedSchemaId"
                  @change="onSchemaChange"
                  class="flex-1 rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                >
                  <option value="">Select a schema...</option>
                  <option v-for="schema in schemas" :key="schema.id" :value="schema.id">
                    {{ schema.schema_name }}
                    <span v-if="existingMappings[schema.id]?.length" class="text-green-600">
                      ({{ existingMappings[schema.id].length }} mappings)
                    </span>
                  </option>
                </select>

                <div v-if="selectedSchemaId" class="flex gap-2">
                  <span
                    v-if="hasMappingForSchema"
                    class="px-3 py-2 bg-green-100 text-green-800 rounded-md text-sm font-medium"
                  >
                    {{ existingMappings[selectedSchemaId].length }} mappings configured
                  </span>
                  <span
                    v-else
                    class="px-3 py-2 bg-yellow-100 text-yellow-800 rounded-md text-sm font-medium"
                  >
                    No mappings yet
                  </span>
                </div>
              </div>
            </div>

            <!-- Ground Truth Preview -->
            <div v-if="groundTruthPreview" class="mb-6">
              <h4 class="text-md font-medium text-gray-900 mb-3">Ground Truth Preview</h4>
              <div class="bg-gray-50 rounded-lg p-4 max-h-64 overflow-auto">
                <div class="overflow-x-auto">
                  <table class="min-w-full text-xs">
                    <thead>
                      <tr class="border-b">
                        <th v-for="field in groundTruthFields" :key="field" class="text-left p-2 font-medium text-gray-700">
                          {{ field }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in previewData.slice(0, 3)" :key="idx" class="border-b">
                        <td v-for="field in groundTruthFields" :key="field" class="p-2 text-gray-600">
                          {{ formatPreviewValue(row[field]) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-if="previewData.length > 3" class="text-xs text-gray-500 mt-2">
                    ... and {{ previewData.length - 3 }} more rows
                  </p>
                </div>
              </div>
            </div>

            <!-- Field Mapping Configuration -->
            <div v-if="selectedSchemaId && schemaFields">
              <div class="flex justify-between items-center mb-4">
                <h4 class="text-md font-medium text-gray-900">
                  Field Mappings for "{{ schemas.find(s => s.id == selectedSchemaId)?.schema_name }}"
                </h4>
                <div class="flex gap-2">
                  <button
                    @click="suggestMappings"
                    class="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm hover:bg-blue-100 transition-colors"
                    :disabled="isLoadingSuggestions"
                  >
                    <span v-if="isLoadingSuggestions" class="flex items-center">
                      <svg class="animate-spin -ml-1 mr-1 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Suggesting...
                    </span>
                    <span v-else>Auto-suggest Mappings</span>
                  </button>
                  <button
                    @click="addMapping"
                    class="px-3 py-1.5 bg-green-50 text-green-700 rounded-md text-sm hover:bg-green-100 transition-colors"
                    :disabled="!canAddMapping"
                  >
                    Add Mapping
                  </button>
                  <button
                    v-if="hasMappingForSchema"
                    @click="deleteMappings"
                    class="px-3 py-1.5 bg-red-50 text-red-700 rounded-md text-sm hover:bg-red-100 transition-colors"
                  >
                    Delete All
                  </button>
                </div>
              </div>

              <!-- Mapping Table -->
              <div class="bg-white border rounded-lg overflow-hidden">
                <table v-if="fieldMappings.length > 0" class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">
                        Schema Field
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">
                        Ground Truth Field
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">
                        Type
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">
                        Comparison
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/6">
                        Options
                      </th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-16">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr v-for="(mapping, index) in fieldMappings" :key="index" class="hover:bg-gray-50">
                      <td class="px-4 py-3">
                        <select
                          v-model="mapping.schema_field"
                          class="block w-full rounded-md border border-gray-300 shadow-sm py-1.5 px-2 text-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                        >
                          <option value="">Select field...</option>
                          <option v-for="field in availableSchemaFields" :key="field" :value="field">
                            {{ field }}
                          </option>
                          <!-- Include the currently selected field even if it's used -->
                          <option v-if="mapping.schema_field && !availableSchemaFields.includes(mapping.schema_field)" :value="mapping.schema_field">
                            {{ mapping.schema_field }}
                          </option>
                        </select>
                        <div v-if="mapping.schema_field" class="mt-1 text-xs text-gray-500">
                          Type: {{ schemaFields[mapping.schema_field] }}
                        </div>
                      </td>
                      <td class="px-4 py-3">
                        <select
                          v-model="mapping.ground_truth_field"
                          class="block w-full rounded-md border border-gray-300 shadow-sm py-1.5 px-2 text-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                        >
                          <option value="">Select field...</option>
                          <option v-for="field in groundTruthFields" :key="field" :value="field">
                            {{ field }}
                          </option>
                        </select>
                        <div v-if="mapping.ground_truth_field && groundTruthSamples[mapping.ground_truth_field]" class="mt-1 text-xs text-gray-500">
                          Sample: {{ formatPreviewValue(Array.isArray(groundTruthSamples[mapping.ground_truth_field]) ? groundTruthSamples[mapping.ground_truth_field][0] : groundTruthSamples[mapping.ground_truth_field]) }}
                        </div>
                      </td>
                      <td class="px-4 py-3">
                        <select
                          v-model="mapping.field_type"
                          class="block w-full rounded-md border border-gray-300 shadow-sm py-1.5 px-2 text-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                        >
                          <option value="string">String</option>
                          <option value="number">Number</option>
                          <option value="boolean">Boolean</option>
                          <option value="date">Date</option>
                          <option value="category">Category</option>
                        </select>
                      </td>
                      <td class="px-4 py-3">
                        <select
                          v-model="mapping.comparison_method"
                          @change="updateComparisonOptions(mapping)"
                          class="block w-full rounded-md border border-gray-300 shadow-sm py-1.5 px-2 text-sm focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
                        >
                          <option value="exact">Exact</option>
                          <option value="fuzzy">Fuzzy</option>
                          <option value="numeric">Numeric</option>
                          <option value="boolean">Boolean</option>
                          <option value="category">Category</option>
                          <option value="date">Date</option>
                        </select>
                      </td>
                      <td class="px-4 py-3">
                        <div class="space-y-1">
                          <!-- Fuzzy matching threshold -->
                          <div v-if="mapping.comparison_method === 'fuzzy'" class="flex items-center">
                            <label class="text-xs text-gray-600 mr-2">Threshold:</label>
                            <input
                              v-model.number="mapping.comparison_options.threshold"
                              type="number"
                              min="0"
                              max="100"
                              class="w-16 px-1 py-0.5 text-xs border border-gray-300 rounded"
                            />
                            <span class="text-xs text-gray-500 ml-1">%</span>
                          </div>
                          <!-- Numeric tolerance -->
                          <div v-if="mapping.comparison_method === 'numeric'" class="space-y-1">
                            <div class="flex items-center">
                              <label class="text-xs text-gray-600 mr-2">Tolerance:</label>
                              <input
                                v-model.number="mapping.comparison_options.tolerance"
                                type="number"
                                step="0.001"
                                class="w-20 px-1 py-0.5 text-xs border border-gray-300 rounded"
                              />
                            </div>
                            <div class="flex items-center">
                              <input
                                v-model="mapping.comparison_options.relative"
                                type="checkbox"
                                class="h-3 w-3 text-blue-600"
                              />
                              <label class="text-xs text-gray-600 ml-1">Relative</label>
                            </div>
                          </div>
                          <!-- Case sensitivity -->
                          <div v-if="mapping.comparison_method === 'exact'" class="flex items-center">
                            <input
                              v-model="mapping.comparison_options.case_sensitive"
                              type="checkbox"
                              class="h-3 w-3 text-blue-600"
                            />
                            <label class="text-xs text-gray-600 ml-1">Case sensitive</label>
                          </div>
                        </div>
                      </td>
                      <td class="px-4 py-3">
                        <button
                          @click="removeMapping(index)"
                          class="text-red-600 hover:text-red-800 p-1"
                        >
                          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div v-else class="text-center py-8 text-gray-500">
                  <p>No field mappings configured yet.</p>
                  <p class="text-sm mt-1">Click "Auto-suggest Mappings" or "Add Mapping" to get started.</p>
                </div>
              </div>

              <!-- Info about remaining fields -->
              <div v-if="!canAddMapping" class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p class="text-sm text-yellow-800">
                  All available schema fields have been mapped. Remove a mapping to add a new one.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="saveMappings"
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
            :disabled="isSaving || !canSave"
          >
            <span v-if="isSaving" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Saving...
            </span>
            <span v-else>Save Mappings</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

