<template>
  <div class="h-full flex flex-col bg-gray-50">
    <!-- Toolbar -->
    <div class="bg-white border-b px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <!-- Navigation Breadcrumb -->
        <nav class="flex items-center space-x-2 text-sm">
          <button
            type="button"
            @click="navigateToRoot"
            class="text-gray-600 hover:text-gray-900 font-medium"
          >
            Root
          </button>
          <template v-for="(segment, index) in navigationPath" :key="index">
            <svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            <button
              type="button"
              @click="navigateToPath(index)"
              class="text-gray-600 hover:text-gray-900 font-medium"
            >
              {{ segment }}
            </button>
          </template>
        </nav>
      </div>

      <!-- Quick Actions -->
      <div class="flex items-center space-x-2">
        <button
          type="button"
          @click="showHelp = true"
          class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          title="Help"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Main Editor Area -->
    <div class="flex-1 overflow-hidden flex">
      <!-- Tree Navigation (Collapsible) -->
      <div
        v-if="showTreeNav"
        class="w-64 bg-white border-r overflow-y-auto"
      >
        <div class="p-4">
          <h3 class="text-sm font-medium text-gray-900 mb-3">Schema Structure</h3>
          <SchemaTree
            :schema="schema"
            :current-path="currentPath"
            @navigate="navigateToPath"
          />
        </div>
      </div>

      <!-- Editor Canvas -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Current Schema Block -->
        <div class="max-w-4xl mx-auto">
          <SchemaBlock
            :schema="currentSchema"
            :path="currentPath"
            :advanced-mode="advancedMode"
            @update="updateCurrentSchema"
            @add-property="showAddPropertyModal = true"
            @edit-property="editProperty"
            @delete-property="confirmDeleteProperty"
            @navigate="navigateToProperty"
            @edit-root="editRootSchema"
          />


          <!-- Empty State -->
          <div
            v-if="currentSchema.type === 'object' && (!currentSchema.properties || Object.keys(currentSchema.properties).length === 0)"
            class="mt-6 text-center py-12 border-2 border-dashed border-gray-300 rounded-lg"
          >
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p class="mt-2 text-sm text-gray-600">No properties defined</p>
            <button
              type="button"
              @click="showAddPropertyModal = true"
              class="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Add First Property
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Property Modal -->
    <Teleport to="body">
      <div
        v-if="showAddPropertyModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        @click="showAddPropertyModal = false"
      >
        <div class="bg-white rounded-lg max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            Add {{ advancedMode ? 'Property' : 'Field' }}
          </h3>

          <form @submit.prevent="addProperty">
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700">
                  {{ advancedMode ? 'Property Name' : 'Field Name' }}
                </label>
                <input
                  v-model="newProperty.name"
                  ref="propertyNameInput"
                  class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="e.g., patient_name"
                  required
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700">
                  {{ advancedMode ? 'Type' : 'Field Type' }}
                </label>
                <div class="mt-2 grid grid-cols-2 gap-2">
                  <button
                    v-for="type in availableTypes"
                    :key="type.value"
                    type="button"
                    @click="newProperty.type = type.value"
                    :class="[
                      'relative rounded-lg border p-4 flex flex-col items-center cursor-pointer focus:outline-none transition-all',
                      newProperty.type === type.value
                        ? 'border-blue-500 ring-2 ring-blue-500 bg-blue-50'
                        : 'border-gray-300 hover:border-gray-400'
                    ]"
                  >
                    <div :class="['rounded-lg p-2 mb-2', type.color]">
                      <component :is="type.icon" class="h-6 w-6 text-white" />
                    </div>
                    <span class="text-sm font-medium">{{ type.label }}</span>
                  </button>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700">
                  Display Name
                </label>
                <input
                  v-model="newProperty.title"
                  class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="e.g., Patient Name"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  v-model="newProperty.description"
                  rows="2"
                  class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Brief description of this field"
                />
              </div>
            </div>

            <div class="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                @click="showAddPropertyModal = false"
                class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Add {{ advancedMode ? 'Property' : 'Field' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit Property Modal -->
    <Teleport to="body">
      <div
        v-if="showEditPropertyModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        @click="showEditPropertyModal = false"
      >
        <div class="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col" @click.stop>
          <div class="p-6 border-b">
            <h3 class="text-lg font-medium text-gray-900">
              Edit {{ editingProperty?.key === '__root__' ? 'Root Schema' : (advancedMode ? 'Property' : 'Field') }}: {{ editingProperty?.key === '__root__' ? '' : editingProperty?.key }}
            </h3>

          </div>

          <div class="flex-1 overflow-y-auto p-6">
            <PropertyDetailsEditor
              v-if="editingProperty"
              :property="editingProperty.schema"
              :property-key="editingProperty.key"
              :advanced-mode="advancedMode"
              @update="updateEditingProperty"
            />
          </div>

          <div class="p-6 border-t bg-gray-50 flex justify-end space-x-3">
            <button
              type="button"
              @click="showEditPropertyModal = false"
              class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="savePropertyEdits"
              class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        @click="showDeleteModal = false"
      >
        <div class="bg-white rounded-lg max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900">Delete {{ advancedMode ? 'Property' : 'Field' }}</h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete "{{ propertyToDelete }}"? This action cannot be undone.
          </p>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              @click="showDeleteModal = false"
              class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="deleteProperty"
              class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Enum Editor Modal -->
    <Teleport to="body">
      <div
        v-if="showEnumModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        @click="showEnumModal = false"
      >
        <div class="bg-white rounded-lg max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            Edit Options for {{ enumProperty?.key }}
          </h3>

          <div class="space-y-3">
            <div
              v-for="(value, index) in enumValues"
              :key="index"
              class="flex items-center space-x-2"
            >
              <input
                v-model="enumValues[index]"
                class="flex-1 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Option value"
              />
              <button
                type="button"
                @click="removeEnumValue(index)"
                class="text-red-600 hover:text-red-800"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>

            <button
              type="button"
              @click="addEnumValue"
              class="w-full py-2 border-2 border-dashed border-gray-300 rounded-md text-sm text-gray-600 hover:border-gray-400 hover:text-gray-700"
            >
              + Add Option
            </button>
          </div>

          <div class="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              @click="showEnumModal = false"
              class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="saveEnumValues"
              class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Save Options
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Help Modal -->
    <Teleport to="body">
      <div
        v-if="showHelp"
        class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        @click="showHelp = false"
      >
        <div class="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden" @click.stop>
          <div class="p-6 border-b">
            <h3 class="text-lg font-medium text-gray-900">Schema Editor Help</h3>
          </div>
          <div class="p-6 overflow-y-auto">
            <div class="space-y-4">
              <div>
                <h4 class="font-medium text-gray-900 mb-2">Field Types</h4>
                <div class="grid grid-cols-2 gap-3">
                  <div v-for="type in availableTypes" :key="type.value" class="flex items-start space-x-3">
                    <div :class="['rounded-lg p-2', type.color]">
                      <component :is="type.icon" class="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p class="font-medium text-sm">{{ type.label }}</p>
                      <p class="text-xs text-gray-600">{{ type.description }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 class="font-medium text-gray-900 mb-2">Tips</h4>
                <ul class="text-sm text-gray-600 space-y-1">
                  <li>• Click on any field block to edit its properties</li>
                  <li>• Use the navigation breadcrumb to move between nested structures</li>
                  <li>• Drag and drop to reorder fields (coming soon)</li>
                  <li>• Enable "Advanced features" to access more JSON Schema options</li>
                </ul>
              </div>
            </div>
          </div>
          <div class="p-6 border-t bg-gray-50">
            <button
              type="button"
              @click="showHelp = false"
              class="w-full px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, h, onUnmounted, onMounted } from 'vue';
import SchemaBlock from './SchemaBlock.vue';
import SchemaTree from './SchemaTree.vue';
import PropertyDetailsEditor from './PropertyDetailsEditor.vue';

const props = defineProps({
  schema: {
    type: Object,
    required: true
  },
  advancedMode: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:schema']);

// UI State
const showTreeNav = ref(true);
const showAddPropertyModal = ref(false);
const showEditPropertyModal = ref(false);
const showDeleteModal = ref(false);
const showEnumModal = ref(false);
const showHelp = ref(false);

// Navigation
const currentPath = ref([]);
const navigationPath = computed(() => {
  return currentPath.value.map(segment => {
    // Make path segments more readable
    return segment.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  });
});

// Schema Data
const localSchema = ref(JSON.parse(JSON.stringify(props.schema)));
const currentSchema = computed(() => {
  let schema = localSchema.value;
  for (const segment of currentPath.value) {
    if (schema.properties && schema.properties[segment]) {
      schema = schema.properties[segment];
    } else if (schema.items) {
      schema = schema.items;
    }
  }
  return schema;
});

// Property Management
const newProperty = ref({
  name: '',
  type: 'string',
  title: '',
  description: ''
});

const editingProperty = ref(null);
const propertyToDelete = ref('');
const enumProperty = ref(null);
const enumValues = ref([]);

// Property type definitions with icons
const StringIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'
      })
    ]);
  }
};

const NumberIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M7 20l4-16m2 16l4-16M6 9h14M4 15h14'
      })
    ]);
  }
};

const BooleanIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
      })
    ]);
  }
};

const ObjectIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10'
      })
    ]);
  }
};

const ArrayIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
      h('path', {
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-width': '2',
        d: 'M4 6h16M4 10h16M4 14h16M4 18h16'
      })
    ]);
  }
};

const availableTypes = computed(() => [
  {
    value: 'string',
    label: props.advancedMode ? 'String' : 'Text',
    color: 'bg-green-500',
    icon: StringIcon,
    description: 'Single line or multi-line text'
  },
  {
    value: 'number',
    label: props.advancedMode ? 'Number' : 'Number',
    color: 'bg-blue-500',
    icon: NumberIcon,
    description: 'Numeric values, decimals allowed'
  },
  {
    value: 'boolean',
    label: props.advancedMode ? 'Boolean' : 'Yes/No',
    color: 'bg-purple-500',
    icon: BooleanIcon,
    description: 'True or false values'
  },
  {
    value: 'object',
    label: props.advancedMode ? 'Object' : 'Group',
    color: 'bg-orange-500',
    icon: ObjectIcon,
    description: 'Group of related fields'
  },
  {
    value: 'array',
    label: props.advancedMode ? 'Array' : 'List',
    color: 'bg-pink-500',
    icon: ArrayIcon,
    description: 'List of items'
  }
]);

// Watch for external schema changes
watch(() => props.schema, (newSchema) => {
  localSchema.value = JSON.parse(JSON.stringify(newSchema));
}, { deep: true });

// Emit changes
watch(localSchema, (newSchema) => {
  emit('update:schema', newSchema);
}, { deep: true });

// Navigation methods
const navigateToRoot = () => {
  currentPath.value = [];
};

const navigateToPath = (pathIndex) => {
  if (typeof pathIndex === 'number') {
    currentPath.value = currentPath.value.slice(0, pathIndex + 1);
  } else if (Array.isArray(pathIndex)) {
    currentPath.value = pathIndex;
  }
};

const navigateToProperty = (propertyKey) => {
  currentPath.value = [...currentPath.value, propertyKey];
};

// Schema update methods
const updateCurrentSchema = (updates) => {
  let schema = localSchema.value;
  const path = [...currentPath.value];
  const lastSegment = path.pop();

  // Navigate to parent
  for (const segment of path) {
    if (schema.properties && schema.properties[segment]) {
      schema = schema.properties[segment];
    } else if (schema.items) {
      schema = schema.items;
    }
  }

  // Update the schema
  if (lastSegment) {
    if (schema.properties && schema.properties[lastSegment]) {
      schema.properties[lastSegment] = { ...schema.properties[lastSegment], ...updates };
    }
  } else {
    // Update root
    Object.assign(localSchema.value, updates);
  }
};

// Property management methods
const addProperty = () => {
  if (!newProperty.value.name.trim()) return;

  const propertyKey = newProperty.value.name.trim();
  const propertySchema = {
    type: newProperty.value.type,
    title: newProperty.value.title || propertyKey,
    description: newProperty.value.description
  };

  // Add type-specific defaults
  if (propertySchema.type === 'object') {
    propertySchema.properties = {};
  } else if (propertySchema.type === 'array') {
    propertySchema.items = { type: 'string' };
  }

  // Add to current schema
  if (!currentSchema.value.properties) {
    currentSchema.value.properties = {};
  }
  currentSchema.value.properties[propertyKey] = propertySchema;

  // Reset form
  newProperty.value = {
    name: '',
    type: 'string',
    title: '',
    description: ''
  };
  showAddPropertyModal.value = false;
};

const editProperty = ({ key, schema }) => {
  editingProperty.value = { key, schema: JSON.parse(JSON.stringify(schema)) };
  showEditPropertyModal.value = true;
};

const updateEditingProperty = (updates) => {
  if (editingProperty.value) {
    Object.assign(editingProperty.value.schema, updates);
  }
};

// Add this method after the other property management methods
const editRootSchema = () => {
  editingProperty.value = {
    key: '__root__',
    schema: JSON.parse(JSON.stringify(localSchema.value))
  };
  showEditPropertyModal.value = true;
};

const savePropertyEdits = () => {
  if (editingProperty.value) {
    if (editingProperty.value.key === '__root__') {
      // Update root schema properties
      Object.assign(localSchema.value, editingProperty.value.schema);
    } else if (currentSchema.value.properties) {
      currentSchema.value.properties[editingProperty.value.key] = editingProperty.value.schema;
    }
  }
  showEditPropertyModal.value = false;
  editingProperty.value = null;
};


const confirmDeleteProperty = (propertyKey) => {
  propertyToDelete.value = propertyKey;
  showDeleteModal.value = true;
};

const deleteProperty = () => {
  if (propertyToDelete.value && currentSchema.value.properties) {
    delete currentSchema.value.properties[propertyToDelete.value];
  }
  showDeleteModal.value = false;
  propertyToDelete.value = '';
};

// Enum management
const editEnum = (propertyKey, currentEnum) => {
  enumProperty.value = { key: propertyKey };
  enumValues.value = currentEnum ? [...currentEnum] : [''];
  showEnumModal.value = true;
};

const addEnumValue = () => {
  enumValues.value.push('');
};

const removeEnumValue = (index) => {
  enumValues.value.splice(index, 1);
};

const saveEnumValues = () => {
  if (enumProperty.value && currentSchema.value.properties) {
    const property = currentSchema.value.properties[enumProperty.value.key];
    property.enum = enumValues.value.filter(v => v.trim());
  }
  showEnumModal.value = false;
  enumProperty.value = null;
  enumValues.value = [];
};

// Focus on input when modal opens
watch(showAddPropertyModal, async (newVal) => {
  if (newVal) {
    await nextTick();
    const input = document.querySelector('input[ref="propertyNameInput"]');
    if (input) input.focus();
  }
});

onMounted(() => {
  const handleKeyboard = (e) => {
    // Ctrl/Cmd + N for new property
    if ((e.ctrlKey || e.metaKey) && e.key === 'n' && currentSchema.value.type === 'object') {
      e.preventDefault();
      showAddPropertyModal.value = true;
    }
    // Escape to close modals
    if (e.key === 'Escape') {
      showAddPropertyModal.value = false;
      showEditPropertyModal.value = false;
      showDeleteModal.value = false;
      showEnumModal.value = false;
      showHelp.value = false;
    }
  };

  window.addEventListener('keydown', handleKeyboard);

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyboard);
  });
});

</script>
