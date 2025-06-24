<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-lg font-medium text-gray-900">JSON Schemas</h2>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
      >
        <svg class="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        Create Schema
      </button>
    </div>
    <div v-if="isLoading" class="flex justify-center py-12">
      <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>
    <div v-else-if="schemas.length === 0" class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
      <p class="mt-2 text-sm text-gray-600">No schemas created yet</p>
      <p class="mt-1 text-sm text-gray-500">Create a schema to define the structure for information extraction</p>
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="schema in schemas"
        :key="schema.id"
        class="bg-white border rounded-lg shadow-sm overflow-hidden"
      >
        <div class="p-4 border-b">
          <div class="flex justify-between items-start">
            <h3 class="text-lg font-medium text-gray-900">{{ schema.schema_name }}</h3>
            <div class="flex space-x-2">
              <button
                @click="viewSchema(schema)"
                class="text-blue-600 hover:text-blue-800"
                title="View Schema"
              >
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                </svg>
              </button>
              <button
                @click="editSchema(schema)"
                class="text-gray-600 hover:text-gray-800"
                title="Edit Schema"
              >
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
              <button
                @click="confirmDelete(schema)"
                class="text-gray-600 hover:text-red-600"
                title="Delete Schema"
              >
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
          <p class="mt-1 text-sm text-gray-500">Created: {{ formatDate(schema.created_at) }}</p>
        </div>
        <div class="bg-gray-50 p-4 max-h-64 overflow-auto">
          <pre class="text-xs text-gray-700">{{ formatJSON(schema.schema_definition) }}</pre>
        </div>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="showCreateModal || showEditModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="cancelSchemaModal"
      >
        <div class="bg-white rounded-lg max-w-2xl w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ showEditModal ? 'Edit Schema' : 'Create New Schema' }}
          </h3>
          <form @submit.prevent="showEditModal ? updateSchema() : createSchema()">
            <div class="space-y-4">
              <div>
                <label for="schema-name" class="block text-sm font-medium text-gray-700">Schema Name</label>
                <input
                  id="schema-name"
                  v-model="schemaForm.schema_name"
                  class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter schema name"
                  required
                />
              </div>
              <div>
                <label for="schema-definition" class="block text-sm font-medium text-gray-700">Schema Definition (JSON)</label>
                <div class="mt-1 relative">
                  <textarea
                    id="schema-definition"
                    v-model="schemaForm.schema_definition"
                    rows="12"
                    class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm font-mono"
                    placeholder='{"type": "object", "properties": {...}}'
                    required
                  ></textarea>
                  <button
                    type="button"
                    @click="formatJsonInput"
                    class="absolute top-2 right-2 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                    title="Format JSON"
                  >
                    Format
                  </button>
                </div>
                <p v-if="schemaError" class="mt-2 text-sm text-red-600">{{ schemaError }}</p>
              </div>
            </div>
            <div class="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                @click="cancelSchemaModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                :disabled="isSubmitting"
              >
                <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ showEditModal ? 'Update' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="showViewModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showViewModal = false"
      >
        <div class="bg-white rounded-lg max-w-2xl w-full p-6" @click.stop>
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">{{ currentSchema?.schema_name }}</h3>
            <button @click="showViewModal = false" class="text-gray-400 hover:text-gray-500">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96">
            <pre class="text-sm text-gray-700">{{ formatJSON(currentSchema?.schema_definition) }}</pre>
          </div>
          <div class="mt-6 flex justify-end">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showViewModal = false"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showDeleteModal = false"
      >
        <div class="bg-white rounded-lg max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900">Delete Schema</h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete the schema "{{ schemaToDelete?.schema_name }}"? This action cannot be undone.
          </p>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showDeleteModal = false"
            >
              Cancel
            </button>
            <button
              class="inline-flex justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              @click="deleteSchema"
              :disabled="isDeleting"
            >
              <svg v-if="isDeleting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { api } from '@/services/api';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const schemas = ref([]);
const isLoading = ref(true);
const error = ref('');
const isSubmitting = ref(false);
const isDeleting = ref(false);
const schemaError = ref('');

const showCreateModal = ref(false);
const showEditModal = ref(false);
const showViewModal = ref(false);
const showDeleteModal = ref(false);

const currentSchema = ref(null);
const schemaToDelete = ref(null);
const schemaForm = ref({
  schema_name: '',
  schema_definition: ''
});

const validateSchema = (schema) => {
  try {
    console.log("Validating schema:", schema);
    const schemaCopy = JSON.parse(JSON.stringify(schema));
    delete schemaCopy.$schema;
    schemaError.value = '';
    return true;
  } catch (err) {
    schemaError.value = 'Invalid JSON: ' + err.message;
    return false;
  }
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const formatJSON = (json) => {
  try {
    if (typeof json === 'string') {
      json = JSON.parse(json);
    }
    return JSON.stringify(json, null, 2);
  } catch (err) {
    return json || '{}';
  }
};

const formatJsonInput = () => {
  try {
    const parsedJson = JSON.parse(schemaForm.value.schema_definition);
    schemaForm.value.schema_definition = JSON.stringify(parsedJson, null, 2);
    schemaError.value = '';
  } catch (err) {
    schemaError.value = 'Invalid JSON: ' + err.message;
  }
};

const fetchSchemas = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/schema`);
    schemas.value = response.data;
  } catch (err) {
    error.value = 'Failed to load schemas';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

const createSchema = async () => {
  schemaError.value = '';
  isSubmitting.value = true;
  try {
    let schemaDefinition;
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition);
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message;
      isSubmitting.value = false;
      return;
    }

    if (!validateSchema(schemaDefinition)) {
      isSubmitting.value = false;
      return;
    }

    const response = await api.post(`/project/${props.projectId}/schema`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition // Send as dictionary
    });

    schemas.value.push(response.data);
    showCreateModal.value = false;
  } catch (err) {
    schemaError.value = err.response?.data?.detail || 'Failed to create schema';
    console.error(err);
  } finally {
    isSubmitting.value = false;
  }
};

const updateSchema = async () => {
  schemaError.value = '';
  isSubmitting.value = true;
  try {
    let schemaDefinition;
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition);
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message;
      isSubmitting.value = false;
      return;
    }

    if (!validateSchema(schemaDefinition)) {
      isSubmitting.value = false;
      return;
    }

    const response = await api.put(`/project/${props.projectId}/schema/${currentSchema.value.id}`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition // Send as dictionary
    });

    const index = schemas.value.findIndex(s => s.id === currentSchema.value.id);
    if (index !== -1) {
      schemas.value[index] = response.data;
    }
    showEditModal.value = false;
  } catch (err) {
    schemaError.value = err.response?.data?.detail || 'Failed to update schema';
    console.error(err);
  } finally {
    isSubmitting.value = false;
  }
};

const deleteSchema = async () => {
  if (!schemaToDelete.value) return;
  isDeleting.value = true;
  try {
    await api.delete(`/project/${props.projectId}/schema/${schemaToDelete.value.id}`);
    schemas.value = schemas.value.filter(s => s.id !== schemaToDelete.value.id);
    showDeleteModal.value = false;
  } catch (err) {
    error.value = 'Failed to delete schema';
    console.error(err);
  } finally {
    isDeleting.value = false;
    schemaToDelete.value = null;
  }
};

const viewSchema = (schema) => {
  currentSchema.value = schema;
  showViewModal.value = true;
};

const editSchema = (schema) => {
  currentSchema.value = schema;
  schemaForm.value = {
    schema_name: schema.schema_name,
    schema_definition: formatJSON(schema.schema_definition)
  };
  showEditModal.value = true;
};

const confirmDelete = (schema) => {
  schemaToDelete.value = schema;
  showDeleteModal.value = true;
};

const cancelSchemaModal = () => {
  showCreateModal.value = false;
  showEditModal.value = false;
  schemaError.value = '';
  schemaForm.value = {
    schema_name: '',
    schema_definition: ''
  };
};

onMounted(() => {
  fetchSchemas();
});
</script>