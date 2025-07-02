<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-gradient-to-r from-red-50 to-white rounded-lg p-6 border border-red-200">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-800">Field Error Analysis</h2>
          <p class="text-gray-600">Detailed breakdown of field-level extraction errors</p>
        </div>
        <div class="text-right">
          <div class="text-2xl font-bold text-red-600">{{ totalErrors }}</div>
          <div class="text-sm text-gray-500">Total Errors</div>
        </div>
      </div>

      <!-- Error summary -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white rounded-lg p-4 text-center border">
          <div class="text-lg font-semibold text-red-600">{{ errorsByType.missing || 0 }}</div>
          <div class="text-sm text-gray-500">Missing Fields</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border">
          <div class="text-lg font-semibold text-orange-600">{{ errorsByType.mismatch || 0 }}</div>
          <div class="text-sm text-gray-500">Value Mismatches</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border">
          <div class="text-lg font-semibold text-yellow-600">{{ errorsByType.type_error || 0 }}</div>
          <div class="text-sm text-gray-500">Type Errors</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border">
          <div class="text-lg font-semibold text-purple-600">{{ Object.keys(fieldErrors).length }}</div>
          <div class="text-sm text-gray-500">Fields Affected</div>
        </div>
      </div>
    </div>

    <!-- Field selector -->
    <div class="bg-white rounded-lg border p-4">
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex items-center gap-2">
          <label class="text-sm font-medium text-gray-700">Field:</label>
          <select
            :value="selectedField"
            @change="$emit('select-field', $event.target.value)"
            class="rounded-md border border-gray-300 text-sm py-1 px-2 focus:border-blue-500 focus:ring focus:ring-blue-500 focus:ring-opacity-50"
          >
            <option value="">All Fields</option>
            <option v-for="fieldName in fieldNames" :key="fieldName" :value="fieldName">
              {{ fieldName }} ({{ fieldErrors[fieldName]?.length || 0 }} errors)
            </option>
          </select>
        </div>
        <div class="flex items-center gap-2 ml-auto">
          <span class="text-sm text-gray-600">
            {{ selectedField ? fieldErrors[selectedField]?.length || 0 : totalErrors }} errors
          </span>
        </div>
      </div>
    </div>

    <!-- Error details -->
    <div v-if="selectedField && fieldErrors[selectedField]" class="space-y-4">
      <div class="bg-white rounded-lg border p-6">
        <h3 class="text-lg font-semibold text-gray-800 mb-4">
          Errors for "{{ selectedField }}"
        </h3>

        <div class="space-y-4">
          <div
            v-for="error in fieldErrors[selectedField]"
            :key="`${error.document_id}-${error.field_name}`"
            class="border border-red-200 rounded-lg p-4 bg-red-50"
          >
            <div class="flex justify-between items-start mb-3">
              <div>
                <h4 class="text-sm font-medium text-red-800">
                  Document #{{ error.document_id }}
                </h4>
                <p class="text-xs text-red-600 mt-1">
                  {{ error.document_name || 'Unknown file' }}
                </p>
              </div>
              <div class="text-xs text-gray-500">
                <span class="px-2 py-1 bg-red-100 text-red-800 rounded">
                  {{ error.error_type }}
                </span>
              </div>
            </div>

            <!-- Error comparison -->
            <div class="grid grid-cols-2 gap-4 mb-3">
              <div class="bg-white border border-green-200 rounded p-3">
                <h5 class="text-xs font-medium text-green-700 mb-1">Ground Truth</h5>
                <p class="text-sm text-gray-800">
                  {{ formatFieldValue(error.ground_truth_value) }}
                </p>
              </div>
              <div class="bg-white border border-red-200 rounded p-3">
                <h5 class="text-xs font-medium text-red-700 mb-1">Predicted</h5>
                <p class="text-sm text-gray-800">
                  {{ formatFieldValue(error.predicted_value) }}
                </p>
              </div>
            </div>

            <!-- Error analysis -->
            <div class="mt-3 bg-white border border-gray-200 rounded p-3">
              <h5 class="text-xs font-medium text-gray-700 mb-2">Error Analysis:</h5>
              <div class="text-xs text-gray-600 space-y-1">
                <div>
                  <strong>Type:</strong> {{ getErrorTypeDescription(error.error_type) }}
                </div>
                <div v-if="error.confidence_score !== null">
                  <strong>Confidence:</strong> {{ (error.confidence_score * 100).toFixed(1) }}%
                </div>
                <div>
                  <strong>Suggestion:</strong> {{ getErrorSuggestion(error.error_type) }}
                </div>
              </div>

              <!-- Context if available -->
              <div v-if="error.context" class="mt-2">
                <h6 class="text-xs font-medium text-gray-700 mb-1">Document Context:</h6>
                <p class="text-xs text-gray-600 bg-gray-50 p-2 rounded">{{ error.context }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- All fields overview -->
    <div v-else class="bg-white rounded-lg border p-6">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Error Summary by Field</h3>

      <div class="space-y-3">
        <div
          v-for="fieldName in fieldNames"
          :key="fieldName"
          class="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
          @click="$emit('select-field', fieldName)"
        >
          <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-red-500"></div>
            <div>
              <div class="font-medium text-gray-800">{{ fieldName }}</div>
              <div class="text-sm text-gray-500">
                {{ fieldErrors[fieldName]?.length || 0 }} errors across {{ getDocumentCount(fieldName) }} documents
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="text-sm text-red-600 font-medium">
              {{ fieldErrors[fieldName]?.length || 0 }} errors
            </div>
            <span class="text-gray-400">→</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  evaluation: {
    type: Object,
    required: true
  },
  fieldErrors: {
    type: Object,
    required: true
  },
  selectedField: {
    type: String,
    default: null
  }
});

const emit = defineEmits(['select-field']);

// Computed properties
const fieldNames = computed(() => {
  return Object.keys(props.fieldErrors).sort();
});

const totalErrors = computed(() => {
  return Object.values(props.fieldErrors).reduce((total, errors) => total + errors.length, 0);
});

const errorsByType = computed(() => {
  const types = {};
  Object.values(props.fieldErrors).forEach(errors => {
    errors.forEach(error => {
      types[error.error_type] = (types[error.error_type] || 0) + 1;
    });
  });
  return types;
});

// Helper functions
const formatFieldValue = (value) => {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const getDocumentCount = (fieldName) => {
  const errors = props.fieldErrors[fieldName] || [];
  const uniqueDocuments = new Set(errors.map(error => error.document_id));
  return uniqueDocuments.size;
};

const getErrorTypeDescription = (errorType) => {
  const descriptions = {
    'missing': 'Field was not extracted from the document',
    'mismatch': 'Extracted value does not match ground truth',
    'fuzzy_mismatch': 'Extracted value is similar but not close enough to ground truth',
    'numeric_mismatch': 'Numeric value is outside acceptable tolerance',
    'boolean_mismatch': 'Boolean value is incorrect',
    'category_mismatch': 'Category value does not match expected options',
    'date_mismatch': 'Date value is incorrect or in wrong format',
    'type_error': 'Value type is incorrect (e.g., text instead of number)',
    'extra': 'Field was extracted but not expected in ground truth'
  };
  return descriptions[errorType] || 'Unknown error type';
};

const getErrorSuggestion = (errorType) => {
  const suggestions = {
    'missing': 'Check if the field exists in the document or improve extraction prompts',
    'mismatch': 'Review extraction accuracy or ground truth data',
    'fuzzy_mismatch': 'Consider adjusting fuzzy matching threshold or improving extraction',
    'numeric_mismatch': 'Check numeric parsing or adjust tolerance settings',
    'boolean_mismatch': 'Review boolean value mapping or extraction logic',
    'category_mismatch': 'Verify category mappings or improve classification',
    'date_mismatch': 'Check date format parsing or improve date extraction',
    'type_error': 'Review data type conversion or schema definition',
    'extra': 'Check if this field should be included in ground truth'
  };
  return suggestions[errorType] || 'Review extraction logic and ground truth data';
};
</script>
