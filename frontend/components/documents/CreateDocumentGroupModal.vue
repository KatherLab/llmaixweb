<template>
  <div class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50" @click="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col" @click.stop>
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-xl font-semibold">
          {{ group ? 'Edit Document Group' : 'Create Document Group' }}
        </h3>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-6 overflow-y-auto flex-1">
        <!-- Group Name -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Group Name <span class="text-red-500">*</span>
          </label>
          <input
            v-model="formData.name"
            type="text"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., Q4 Financial Reports"
          />
        </div>

        <!-- Description -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            v-model="formData.description"
            rows="3"
            class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="Describe the purpose of this document group..."
          />
        </div>

        <!-- Tags -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Tags</label>
          <div class="flex flex-wrap gap-2 mb-2">
            <span
              v-for="(tag, index) in formData.tags"
              :key="index"
              class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
            >
              {{ tag }}
              <button
                @click="removeTag(index)"
                class="ml-2 text-blue-600 hover:text-blue-800"
              >
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="newTag"
              type="text"
              @keyup.enter="addTag"
              class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              placeholder="Add a tag..."
            />
            <button
              @click="addTag"
              :disabled="!newTag.trim()"
              class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300"
            >
              Add
            </button>
          </div>
        </div>

        <!-- Document Selection -->
        <div class="mb-4">
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">
              Select Documents <span class="text-red-500">*</span>
            </label>
            <span class="text-sm text-gray-500">
              {{ formData.document_ids.length }} selected
            </span>
          </div>

          <!-- Quick Filters -->
          <div class="flex gap-2 mb-2">
            <input
              v-model="searchTerm"
              type="text"
              placeholder="Search documents..."
              class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <select
              v-model="filterConfig"
              class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Configurations</option>
              <option
                v-for="config in preprocessingConfigs"
                :key="config.id"
                :value="config.id"
              >
                {{ config.name }}
              </option>
            </select>
          </div>

          <!-- Document List -->
          <div class="border rounded-md overflow-hidden max-h-64 overflow-y-auto">
            <div v-if="filteredDocuments.length === 0" class="p-4 text-center text-gray-500">
              No documents found
            </div>
            <div v-else>
              <div
                v-for="doc in filteredDocuments"
                :key="doc.id"
                :class="[
                  'p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 flex items-center',
                  { 'bg-blue-50': formData.document_ids.includes(doc.id) }
                ]"
                @click="toggleDocument(doc.id)"
              >
                <input
                  type="checkbox"
                  :checked="formData.document_ids.includes(doc.id)"
                  class="mr-3"
                  @click.stop
                />
                <div class="flex-1">
                  <div class="font-medium text-sm">
                    {{ doc.original_file?.file_name || `Document #${doc.id}` }}
                  </div>
                  <div class="text-xs text-gray-500">
                    Config: {{ doc.preprocessing_config?.name || 'N/A' }} •
                    Created: {{ formatDate(doc.created_at) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex gap-2 mt-2">
            <button
              @click="selectAll"
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              Select All Visible
            </button>
            <span class="text-gray-300">|</span>
            <button
              @click="clearSelection"
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear Selection
            </button>
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t flex justify-end gap-2">
        <button
          @click="$emit('close')"
          class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md"
        >
          Cancel
        </button>
        <button
          @click="handleSave"
          :disabled="!isFormValid"
          class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:bg-blue-300 disabled:cursor-not-allowed"
        >
          {{ group ? 'Update' : 'Create' }} Group
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters';

const props = defineProps({
  group: {
    type: Object,
    default: null
  },
  documents: {
    type: Array,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'save']);

// Form data
const formData = ref({
  name: '',
  description: '',
  tags: [],
  document_ids: []
});

const newTag = ref('');
const searchTerm = ref('');
const filterConfig = ref('');
const preprocessingConfigs = ref([]);

// Initialize form
onMounted(async () => {
  if (props.group) {
    formData.value = {
      name: props.group.name,
      description: props.group.description || '',
      tags: [...(props.group.tags || [])],
      document_ids: props.group.documents.map(d => d.id)
    };
  }

  // Load preprocessing configs
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    preprocessingConfigs.value = response.data;
  } catch (error) {
    console.error('Failed to load preprocessing configs:', error);
  }
});

// Computed
const filteredDocuments = computed(() => {
  let docs = [...props.documents];

  if (searchTerm.value) {
    const search = searchTerm.value.toLowerCase();
    docs = docs.filter(doc =>
      doc.original_file?.file_name?.toLowerCase().includes(search) ||
      doc.text?.toLowerCase().includes(search)
    );
  }

  if (filterConfig.value) {
    docs = docs.filter(doc =>
      doc.preprocessing_config?.id === parseInt(filterConfig.value)
    );
  }

  return docs;
});

const isFormValid = computed(() => {
  return formData.value.name.trim() && formData.value.document_ids.length > 0;
});

// Methods
const addTag = () => {
  const tag = newTag.value.trim();
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag);
    newTag.value = '';
  }
};

const removeTag = (index) => {
  formData.value.tags.splice(index, 1);
};

const toggleDocument = (docId) => {
  const index = formData.value.document_ids.indexOf(docId);
  if (index === -1) {
    formData.value.document_ids.push(docId);
  } else {
    formData.value.document_ids.splice(index, 1);
  }
};

const selectAll = () => {
  const visibleIds = filteredDocuments.value.map(d => d.id);
  const newIds = visibleIds.filter(id => !formData.value.document_ids.includes(id));
  formData.value.document_ids.push(...newIds);
};

const clearSelection = () => {
  formData.value.document_ids = [];
};

const handleSave = () => {
  emit('save', {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
    tags: formData.value.tags,
    document_ids: formData.value.document_ids
  });
};
</script>
