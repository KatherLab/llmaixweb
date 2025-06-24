<!-- src/components/DocumentsManagement.vue -->
<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-lg font-medium text-gray-900">Documents</h2>

      <div class="flex items-center space-x-2">
        <!-- Filter by preprocessing task -->
        <select
          v-model="currentFilter"
          class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
        >
          <option value="all">All Documents</option>
          <option v-for="task in preprocessingTasks" :key="task.id" :value="task.id">
            Task #{{ task.id }} ({{ task.documentCount || 0 }} docs)
          </option>
        </select>

        <button
          v-if="selectedDocuments.length > 0"
          @click="selectedDocuments = []"
          class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        >
          Clear selection ({{ selectedDocuments.length }})
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="documents.length === 0" class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p class="mt-2 text-sm text-gray-600">No documents available</p>
      <p class="mt-1 text-sm text-gray-500">Process files to create documents</p>
    </div>

    <div v-else-if="filteredDocuments.length === 0" class="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
      <p class="text-sm text-gray-600">No documents match the current filter</p>
    </div>

    <div v-else class="border rounded-md overflow-hidden">
      <!-- Table header -->
      <div class="bg-gray-50 px-4 py-3 flex items-center border-b">
        <div class="w-8">
          <input
            type="checkbox"
            :checked="areAllDocumentsInViewSelected"
            @change="toggleSelectAllDocumentsInView"
            class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
        </div>
        <div class="w-1/2 sm:w-1/3 font-medium text-sm text-gray-700">Document</div>
        <div class="hidden sm:block w-1/4 font-medium text-sm text-gray-700">Method</div>
        <div class="w-1/2 sm:w-1/3 font-medium text-sm text-gray-700 text-right sm:text-left">Created</div>
      </div>

      <!-- Document list -->
      <div class="bg-white divide-y">
        <div
          v-for="doc in filteredDocuments"
          :key="doc.id"
          class="px-4 py-4 flex items-start hover:bg-gray-50 transition-colors"
        >
          <div class="w-8 pt-1">
            <input
              type="checkbox"
              v-model="selectedDocuments"
              :value="doc.id"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>

          <div class="w-1/2 sm:w-1/3">
            <h3 class="font-medium text-gray-900 truncate" :title="doc.original_file?.file_name || `Document #${doc.id}`">
              {{ doc.original_file?.file_name || `Document #${doc.id}` }}
            </h3>
            <p class="mt-1 text-xs text-gray-500 line-clamp-2">
              {{ truncateText(doc.text) }}
            </p>
          </div>

          <div class="hidden sm:block w-1/4 text-sm text-gray-500">
            {{ doc.preprocessing_method || 'N/A' }}
          </div>

          <div class="w-1/2 sm:w-1/3 text-sm text-gray-500 text-right sm:text-left">
            {{ formatDate(doc.created_at) }}
            <div class="mt-1 flex items-center justify-end sm:justify-start space-x-2">
              <button
                @click="viewDocument(doc)"
                class="text-xs text-blue-600 hover:text-blue-800 flex items-center"
              >
                <svg class="h-3 w-3 mr-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                </svg>
                View
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Document View Modal -->
    <Teleport to="body">
      <div v-if="showDocumentModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg max-w-4xl w-full h-[80vh] flex flex-col">
          <div class="flex justify-between items-center p-4 border-b">
            <h3 class="text-lg font-medium text-gray-900">
              {{ viewingDocument?.original_file?.file_name || `Document #${viewingDocument?.id}` }}
            </h3>
            <button @click="showDocumentModal = false" class="text-gray-400 hover:text-gray-500">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="flex-1 overflow-auto p-4 bg-gray-50">
            <div v-if="viewingDocument?.preprocessed_file?.id" class="flex justify-end mb-4">
              <a
                :href="`/project/${projectId}/file/${viewingDocument.preprocessed_file.id}/content`"
                target="_blank"
                class="text-sm text-blue-600 hover:text-blue-800 flex items-center"
              >
                <svg class="h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
                Open PDF with text layer
              </a>
            </div>
            <div class="bg-white p-4 rounded-md border whitespace-pre-wrap">
              {{ viewingDocument?.text || 'No text content available' }}
            </div>
            <div v-if="viewingDocument?.meta_data" class="mt-4">
              <h4 class="font-medium text-gray-700 mb-2">Metadata</h4>
              <div class="bg-white p-4 rounded-md border overflow-auto">
                <pre>{{ JSON.stringify(viewingDocument.meta_data, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '@/services/api';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const documents = ref([]);
const preprocessingTasks = ref([]);
const isLoading = ref(true);
const error = ref('');
const currentFilter = ref('all');
const selectedDocuments = ref([]);

// Document viewing
const showDocumentModal = ref(false);
const viewingDocument = ref(null);

// Computed properties
const filteredDocuments = computed(() => {
  if (currentFilter.value === 'all') {
    return documents.value;
  }
  return documents.value.filter(doc => doc.preprocessing_task_id === parseInt(currentFilter.value));
});

const areAllDocumentsInViewSelected = computed(() => {
  return filteredDocuments.value.length > 0 &&
    filteredDocuments.value.every(doc => selectedDocuments.value.includes(doc.id));
});

// Methods
const toggleSelectAllDocumentsInView = () => {
  if (areAllDocumentsInViewSelected.value) {
    // Remove all visible documents from selection
    selectedDocuments.value = selectedDocuments.value.filter(
      id => !filteredDocuments.value.some(doc => doc.id === id)
    );
  } else {
    // Add all visible documents to selection
    const visibleDocIds = filteredDocuments.value.map(doc => doc.id);
    const newSelection = [...new Set([...selectedDocuments.value, ...visibleDocIds])];
    selectedDocuments.value = newSelection;
  }
};

const truncateText = (text) => {
  if (!text) return 'No text content';
  return text.length > 150 ? text.substring(0, 150) + '...' : text;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const viewDocument = (document) => {
  viewingDocument.value = document;
  showDocumentModal.value = true;
};

// Fetch documents and preprocessing tasks
const fetchData = async () => {
  isLoading.value = true;
  try {
    // Fetch documents
    const documentsResponse = await api.get(`/project/${props.projectId}/document`);
    documents.value = documentsResponse.data;

    // Extract preprocessing tasks from documents
    const taskMap = {};
    for (const doc of documents.value) {
      if (doc.preprocessing_task_id) {
        if (!taskMap[doc.preprocessing_task_id]) {
          taskMap[doc.preprocessing_task_id] = {
            id: doc.preprocessing_task_id,
            documentCount: 1,
            date: doc.created_at
          };
        } else {
          taskMap[doc.preprocessing_task_id].documentCount++;
        }
      }
    }

    preprocessingTasks.value = Object.values(taskMap).sort((a, b) =>
      new Date(b.date) - new Date(a.date)
    );
  } catch (err) {
    error.value = 'Failed to load documents';
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>
