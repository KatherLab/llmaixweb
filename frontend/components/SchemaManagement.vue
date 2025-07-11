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

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal || showEditModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md z-50"
        @click="cancelSchemaModal"
      >
        <div class="bg-white rounded-lg w-full h-[90vh] max-w-[1600px] my-8 flex flex-col mx-auto" @click.stop>
          <div class="p-6 border-b flex items-center justify-between flex-shrink-0">
            <h3 class="text-lg font-medium text-gray-900">
              {{ showEditModal ? 'Edit Schema' : 'Create New Schema' }}
            </h3>
          </div>

          <form @submit.prevent="showEditModal ? updateSchema() : createSchema()" class="flex flex-col flex-1 min-h-0">
            <div class="flex-1 flex flex-col min-h-0">
              <!-- Schema Name Input -->
              <div class="px-6 pt-4 pb-2 flex-shrink-0">
                <label for="schema-name" class="block text-sm font-medium text-gray-700">Schema Name</label>
                <input
                  id="schema-name"
                  v-model="schemaForm.schema_name"
                  class="mt-1 block w-full max-w-md border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter schema name"
                  required
                />
              </div>

              <!-- Schema validation indicator -->
              <div class="px-6 pb-2 flex items-center space-x-2">
                <div v-if="schemaForm.schema_definition" class="flex items-center space-x-2 text-sm">
                  <div v-if="!schemaError" class="flex items-center text-green-600">
                    <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Valid JSON Schema</span>
                  </div>
                  <div v-else class="flex items-center text-red-600">
                    <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Invalid Schema</span>
                  </div>
                </div>
              </div>

              <!-- Tab Navigation -->
              <div class="px-6 border-b border-gray-200 flex-shrink-0">
                <nav class="-mb-px flex items-center justify-between">
                  <div class="flex space-x-8">
                    <button
                      type="button"
                      @click="activeTab = 'visual'"
                      :class="[
                        activeTab === 'visual'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                        'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm'
                      ]"
                    >
                      <svg class="h-4 w-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a2 2 0 002-2V5z" />
                      </svg>
                      Visual Editor
                    </button>
                    <button
                      type="button"
                      @click="activeTab = 'raw'"
                      :class="[
                        activeTab === 'raw'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                        'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm'
                      ]"
                    >
                      <svg class="h-4 w-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      Raw JSON
                    </button>
                  </div>

                  <div class="flex items-center space-x-4">
                    <!-- Advanced Features Toggle - Only show in Visual tab -->
                    <label v-if="activeTab === 'visual'" class="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        v-model="advancedMode"
                        class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span class="text-gray-700">Enable advanced features</span>
                    </label>

                    <!-- Split View Toggle - Only show in Visual tab -->
                    <label v-if="activeTab === 'visual'" class="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        v-model="splitView"
                        class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span class="text-gray-700">Split view</span>
                    </label>

                    <!-- Templates Button -->
                    <button
                      type="button"
                      @click="showTemplates = true"
                      class="text-sm text-blue-600 hover:text-blue-800 flex items-center"
                    >
                      <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      Templates
                    </button>
                  </div>
                </nav>
              </div>

              <!-- Tab Content -->
              <div class="flex-1 min-h-0" :class="splitView && activeTab === 'visual' ? 'flex' : ''">
                <!-- Visual Editor Tab -->
                <div
                  v-if="activeTab === 'visual' || (splitView && activeTab === 'visual')"
                  :class="[
                    'bg-gray-50',
                    splitView && activeTab === 'visual' ? 'w-1/2 border-r' : 'h-full'
                  ]"
                >
                  <VisualSchemaEditor
                    :schema="visualSchema"
                    @update:schema="updateVisualSchema"
                    :advanced-mode="advancedMode"
                  />
                </div>

                <!-- Raw JSON Tab -->
                <div
                  v-if="activeTab === 'raw' || (splitView && activeTab === 'visual')"
                  :class="[
                    'relative flex flex-col',
                    splitView && activeTab === 'visual' ? 'w-1/2' : 'h-full'
                  ]"
                >
                  <div class="flex-1 p-6 min-h-0">
                    <textarea
                      ref="rawJsonTextarea"
                      v-model="schemaForm.schema_definition"
                      @input="onRawSchemaChange"
                      @keydown="preserveCursorPosition"
                      class="block w-full h-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm font-mono resize-none"
                      placeholder='{"type": "object", "properties": {...}}'
                      required
                    ></textarea>
                    <button
                      type="button"
                      @click="formatJsonInput"
                      class="absolute top-8 right-8 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                      title="Format JSON"
                    >
                      Format
                    </button>
                  </div>
                </div>

              </div>

              <p v-if="schemaError" class="px-6 py-2 text-sm text-red-600 flex-shrink-0">{{ schemaError }}</p>
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t flex justify-end space-x-3 flex-shrink-0">
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

    <!-- Templates Modal -->
    <Teleport to="body">
      <div
        v-if="showTemplates"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showTemplates = false"
      >
        <div class="bg-white rounded-lg max-w-4xl w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900 mb-4">Schema Templates</h3>
          <p class="text-sm text-gray-600 mb-6">Select a template for common medical document structures</p>

          <div class="grid grid-cols-2 gap-4">
            <button
              v-for="template in schemaTemplates"
              :key="template.name"
              @click="applyTemplate(template)"
              class="p-4 border rounded-lg hover:border-blue-500 hover:bg-blue-50 text-left transition-colors"
            >
              <h4 class="font-medium text-gray-900">{{ template.name }}</h4>
              <p class="text-sm text-gray-600 mt-1">{{ template.description }}</p>
            </button>
          </div>

          <div class="mt-6 flex justify-end">
            <button
              class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showTemplates = false"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- View Modal -->
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

    <!-- Delete Modal -->
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
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { api } from '@/services/api';
import VisualSchemaEditor from './VisualSchemaEditor.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const hasUnsavedChanges = ref(false);
const originalSchemaForm = ref({});

const rawJsonTextarea = ref(null);
const cursorPosition = ref(0);


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
const showTemplates = ref(false);

const currentSchema = ref(null);
const schemaToDelete = ref(null);
const schemaForm = ref({
  schema_name: '',
  schema_definition: ''
});

let isUpdating = false;

const preserveCursorPosition = (event) => {
  cursorPosition.value = event.target.selectionStart;
};

// New refs for visual editor
const activeTab = ref('visual');
const visualSchema = ref({
  type: 'object',
  properties: {}
});

// UI preferences
const advancedMode = ref(false);
const splitView = ref(false);



// Schema templates for medical documents
const schemaTemplates = [
  {
    name: 'Patient Information',
    description: 'Basic patient demographics and contact details',
    schema: {
      type: 'object',
      properties: {
        patient_id: { type: 'string', title: 'Patient ID' },
        first_name: { type: 'string', title: 'First Name' },
        last_name: { type: 'string', title: 'Last Name' },
        date_of_birth: { type: 'string', format: 'date', title: 'Date of Birth' },
        gender: {
          type: 'string',
          title: 'Gender',
          enum: ['Male', 'Female', 'Other']
        },
        contact: {
          type: 'object',
          title: 'Contact Information',
          properties: {
            phone: { type: 'string', title: 'Phone Number' },
            email: { type: 'string', format: 'email', title: 'Email' },
            address: { type: 'string', title: 'Address' }
          }
        }
      }
    }
  },
  {
    name: 'Medical History',
    description: 'Patient medical history and conditions',
    schema: {
      type: 'object',
      properties: {
        conditions: {
          type: 'array',
          title: 'Medical Conditions',
          items: {
            type: 'object',
            properties: {
              condition_name: { type: 'string', title: 'Condition' },
              diagnosis_date: { type: 'string', format: 'date', title: 'Diagnosis Date' },
              status: {
                type: 'string',
                title: 'Status',
                enum: ['Active', 'Resolved', 'Chronic']
              }
            }
          }
        },
        allergies: {
          type: 'array',
          title: 'Allergies',
          items: {
            type: 'object',
            properties: {
              allergen: { type: 'string', title: 'Allergen' },
              severity: {
                type: 'string',
                title: 'Severity',
                enum: ['Mild', 'Moderate', 'Severe']
              }
            }
          }
        }
      }
    }
  },
  {
    name: 'Lab Results',
    description: 'Laboratory test results and measurements',
    schema: {
      type: 'object',
      properties: {
        test_date: { type: 'string', format: 'date', title: 'Test Date' },
        lab_name: { type: 'string', title: 'Laboratory Name' },
        results: {
          type: 'array',
          title: 'Test Results',
          items: {
            type: 'object',
            properties: {
              test_name: { type: 'string', title: 'Test Name' },
              value: { type: 'number', title: 'Value' },
              unit: { type: 'string', title: 'Unit' },
              reference_range: { type: 'string', title: 'Reference Range' },
              abnormal: { type: 'boolean', title: 'Abnormal' }
            }
          }
        }
      }
    }
  },
  {
    name: 'Prescription',
    description: 'Medication prescriptions and dosage information',
    schema: {
      type: 'object',
      properties: {
        prescription_date: { type: 'string', format: 'date', title: 'Prescription Date' },
        prescriber: { type: 'string', title: 'Prescriber Name' },
        medications: {
          type: 'array',
          title: 'Medications',
          items: {
            type: 'object',
            properties: {
              medication_name: { type: 'string', title: 'Medication' },
              dosage: { type: 'string', title: 'Dosage' },
              frequency: { type: 'string', title: 'Frequency' },
              duration: { type: 'string', title: 'Duration' },
              instructions: { type: 'string', title: 'Instructions' }
            }
          }
        }
      }
    }
  }
];

watch(visualSchema, (newSchema) => {
  // Only update if not currently focused on textarea
  if (document.activeElement !== rawJsonTextarea.value) {
    schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2);
  }
}, { deep: true });

// Watch for tab changes to sync data
watch(activeTab, (newTab) => {
  if (newTab === 'visual' && !splitView.value) {
    // Convert raw JSON to visual schema
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition || '{"type": "object", "properties": {}}');
      visualSchema.value = parsed;
    } catch (err) {
      console.warn('Invalid JSON, using default schema');
      visualSchema.value = { type: 'object', properties: {} };
    }
  } else if (newTab === 'raw' && !splitView.value) {
    // Convert visual schema to raw JSON
    schemaForm.value.schema_definition = JSON.stringify(visualSchema.value, null, 2);
  }
});

watch([showCreateModal, showEditModal], ([create, edit]) => {
  if (create || edit) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
});

// Initialize visual schema when opening create modal
watch(showCreateModal, (newValue) => {
  if (newValue) {
    activeTab.value = 'visual';
    visualSchema.value = { type: 'object', properties: {} };
    schemaForm.value = {
      schema_name: '',
      schema_definition: JSON.stringify({ type: 'object', properties: {} }, null, 2)
    };
  }
});

// Initialize visual schema when opening edit modal
watch(showEditModal, (newValue) => {
  if (newValue && currentSchema.value) {
    activeTab.value = 'visual';
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition);
      visualSchema.value = parsed;
    } catch (err) {
      visualSchema.value = { type: 'object', properties: {} };
    }
  }
});

watch([schemaForm, visualSchema], () => {
  if (isUpdating) return;
  hasUnsavedChanges.value = true;
}, { deep: true });

// Handle visual schema updates
const updateVisualSchema = (newSchema) => {
  visualSchema.value = newSchema;
  // Auto-sync to raw JSON
  schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2);
  schemaError.value = '';
};

const applyTemplate = (template) => {
  visualSchema.value = template.schema;
  schemaForm.value.schema_definition = JSON.stringify(template.schema, null, 2);
  schemaForm.value.schema_name = template.name;
  showTemplates.value = false;
};

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

// Enhanced formatJsonInput to sync with visual editor
const formatJsonInput = () => {
  try {
    const parsedJson = JSON.parse(schemaForm.value.schema_definition);
    schemaForm.value.schema_definition = JSON.stringify(parsedJson, null, 2);
    visualSchema.value = parsedJson;
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

watch([schemaForm, visualSchema], () => {
  hasUnsavedChanges.value = true;
}, { deep: true });

const cancelSchemaModal = () => {
  if (hasUnsavedChanges.value) {
    if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
      return;
    }
  }

  showCreateModal.value = false;
  showEditModal.value = false;
  schemaError.value = '';
  activeTab.value = 'visual';
  schemaForm.value = {
    schema_name: '',
    schema_definition: ''
  };
  visualSchema.value = { type: 'object', properties: {} };
  currentSchema.value = null;
  hasUnsavedChanges.value = false;
};


const createSchema = async () => {
  schemaError.value = '';
  isSubmitting.value = true;
  let response;
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
    response = await api.post(`/project/${props.projectId}/schema`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition
    });
    schemas.value.push(response.data);
    showCreateModal.value = false;
    hasUnsavedChanges.value = false;
    cancelSchemaModal();
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
  let response;
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
    response = await api.put(`/project/${props.projectId}/schema/${currentSchema.value.id}`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition
    });
    const index = schemas.value.findIndex(s => s.id === currentSchema.value.id);
    if (index !== -1) {
      schemas.value[index] = response.data;
    }
    showEditModal.value = false;
    hasUnsavedChanges.value = false;
    cancelSchemaModal();
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

// Enhanced editSchema function to properly initialize both views
const editSchema = (schema) => {
  currentSchema.value = schema;
  const formattedJson = formatJSON(schema.schema_definition);
  schemaForm.value = {
    schema_name: schema.schema_name,
    schema_definition: formattedJson
  };

  // Initialize visual schema
  try {
    visualSchema.value = JSON.parse(formattedJson);
  } catch (err) {
    console.warn('Failed to parse existing schema for visual editor:', err);
    visualSchema.value = { type: 'object', properties: {} };
  }

  showEditModal.value = true;
};

const onRawSchemaChange = () => {
  // Store cursor position
  const textarea = rawJsonTextarea.value;
  const savedPosition = textarea ? textarea.selectionStart : 0;

  // Auto-sync to visual if valid JSON
  try {
    const parsed = JSON.parse(schemaForm.value.schema_definition);
    visualSchema.value = parsed;
    schemaError.value = '';
  } catch (err) {
    // Don't update visual schema if JSON is invalid
    schemaError.value = 'Invalid JSON: ' + err.message;
  }

  // Restore cursor position after Vue updates
  nextTick(() => {
    if (textarea) {
      textarea.setSelectionRange(savedPosition, savedPosition);
    }
  });
};

const confirmDelete = (schema) => {
  schemaToDelete.value = schema;
  showDeleteModal.value = true;
};

onMounted(() => {
  fetchSchemas();
});

onUnmounted(() => {
  document.body.style.overflow = '';
});

</script>
