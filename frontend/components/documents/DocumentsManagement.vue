<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-start">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Documents</h2>
        <p class="mt-1 text-sm text-gray-500">
          View and manage processed documents
        </p>
      </div>

      <!-- Quick Stats -->
      <div class="flex items-center space-x-6">
        <div class="text-center">
          <p class="text-2xl font-semibold text-gray-900">{{ totalDocuments }}</p>
          <p class="text-xs text-gray-500">Total Documents</p>
        </div>
        <div class="text-center">
          <p class="text-2xl font-semibold text-blue-600">{{ recentDocuments }}</p>
          <p class="text-xs text-gray-500">Last 7 days</p>
        </div>
      </div>
    </div>

    <div class="border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'documents'"
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm',
            activeTab === 'documents'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          ]"
        >
          All Documents
          <span class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
            {{ totalDocuments }}
          </span>
        </button>
        <button
          @click="activeTab = 'groups'"
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm',
            activeTab === 'groups'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          ]"
        >
          Document Groups
          <span class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
            {{ documentSets.length }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div v-if="activeTab === 'documents'">
      <!-- Filters and Search -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <!-- Search -->
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <div class="relative">
              <input
                v-model="filters.search"
                type="text"
                placeholder="Search in documents..."
                class="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <svg class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          <!-- Preprocessing Task Filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Preprocessing Task</label>
            <select
              v-model="filters.taskId"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Tasks</option>
              <option
                v-for="task in preprocessingTasks"
                :key="task.id"
                :value="task.id"
              >
                Task #{{ task.id }} ({{ task.documentCount }} docs)
              </option>
            </select>
          </div>

          <!-- Configuration Filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Configuration</label>
            <select
              v-model="filters.configId"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Configurations</option>
              <option
                v-for="config in configurations"
                :key="config.id"
                :value="config.id"
              >
                {{ config.name }}
              </option>
            </select>
          </div>

          <!-- Date Range -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
            <select
              v-model="filters.dateRange"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Time</option>
              <option value="today">Today</option>
              <option value="week">Last 7 days</option>
              <option value="month">Last 30 days</option>
            </select>
          </div>

          <!-- OCR Language Filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">OCR Language</label>
            <select
              v-model="filters.ocrLanguage"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Languages</option>
              <option value="eng">English</option>
              <option value="spa">Spanish</option>
              <option value="fra">French</option>
              <option value="deu">German</option>
            </select>
          </div>

          <!-- Status Filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Processing Status</label>
            <select
              v-model="filters.status"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="partial">Partial Success</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <!-- Clear Filters -->
          <div class="flex items-end">
            <button
              @click="clearFilters"
              class="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      <!-- View Toggle and Actions -->
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center space-x-2">
          <button
            @click="viewMode = 'grid'"
            :class="[
              'p-2 rounded-lg transition-colors',
              viewMode === 'grid'
                ? 'bg-blue-100 text-blue-600'
                : 'text-gray-400 hover:text-gray-600'
            ]"
          >
            <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            @click="viewMode = 'list'"
            :class="[
              'p-2 rounded-lg transition-colors',
              viewMode === 'list'
                ? 'bg-blue-100 text-blue-600'
                : 'text-gray-400 hover:text-gray-600'
            ]"
          >
            <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        <div class="flex items-center space-x-3">
          <span class="text-sm text-gray-500">
            {{ filteredDocuments.length }} document{{ filteredDocuments.length !== 1 ? 's' : '' }}
          </span>

          <div v-if="selectedDocuments.length > 0" class="flex items-center space-x-2">
            <span class="text-sm text-gray-700">
              {{ selectedDocuments.length }} selected
            </span>
            <button
              @click="performBatchAction('reprocess')"
              class="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Reprocess
            </button>
            <button
              @click="performBatchAction('export')"
              class="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Export
            </button>
            <button
              @click="performBatchAction('delete')"
              class="text-sm text-red-600 hover:text-red-800 font-medium"
            >
              Delete
            </button>
            <button
              @click="selectedDocuments = []"
              class="text-sm text-gray-600 hover:text-gray-800"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <!-- Documents Grid/List -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>

      <div v-else-if="filteredDocuments.length === 0" class="bg-gray-50 rounded-lg p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No documents found</h3>
        <p class="mt-1 text-sm text-gray-500">
          {{ filters.search ? 'Try adjusting your search or filters' : 'Process some files to see documents here' }}
        </p>
      </div>

      <!-- Grid View -->
      <div v-else-if="viewMode === 'grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <DocumentCard
          v-for="doc in paginatedDocuments"
          :key="doc.id"
          :document="doc"
          :selected="selectedDocuments.includes(doc.id)"
          @toggle-selection="toggleDocumentSelection"
          @view="viewDocument"
          @download="downloadDocument"
        />
      </div>

      <!-- List View -->
      <div v-else class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  :checked="areAllDocumentsSelected"
                  @change="toggleSelectAll"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Document
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Configuration
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Processing
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th class="relative px-6 py-3">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="doc in paginatedDocuments"
              :key="doc.id"
              class="hover:bg-gray-50 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <input
                  type="checkbox"
                  :checked="selectedDocuments.includes(doc.id)"
                  @change="toggleDocumentSelection(doc.id)"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center">
                  <FileIcon :fileType="doc.original_file?.file_type" :size="40" />
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-900 truncate max-w-xs">
                      {{ doc.original_file?.file_name || `Document #${doc.id}` }}
                    </p>
                    <p class="text-xs text-gray-500">
                      {{ formatFileSize(doc.original_file?.file_size) }}
                    </p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">
                  {{ doc.preprocessing_config?.name || 'Custom Config' }}
                </div>
                <div class="text-xs text-gray-500">
                  OCR: {{ doc.preprocessing_config?.use_ocr ? 'Yes' : 'No' }}
                  <span v-if="doc.preprocessing_config?.ocr_languages">
                    ({{ doc.preprocessing_config.ocr_languages.join(', ') }})
                  </span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    getStatusClass(doc.preprocessing_status)
                  ]"
                >
                  {{ doc.preprocessing_status || 'Processed' }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(doc.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end space-x-2">
                  <button
                    @click="viewDocument(doc)"
                    class="text-blue-600 hover:text-blue-900"
                    title="View"
                  >
                    <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  <button
                    @click="downloadDocument(doc)"
                    class="text-gray-600 hover:text-gray-900"
                    title="Download"
                  >
                    <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
        <div class="flex-1 flex justify-between sm:hidden">
          <button
            @click="currentPage--"
            :disabled="currentPage === 1"
            class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            @click="currentPage++"
            :disabled="currentPage === totalPages"
            class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700">
              Showing
              <span class="font-medium">{{ (currentPage - 1) * itemsPerPage + 1 }}</span>
              to
              <span class="font-medium">{{ Math.min(currentPage * itemsPerPage, filteredDocuments.length) }}</span>
              of
              <span class="font-medium">{{ filteredDocuments.length }}</span>
              results
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
              <button
                @click="currentPage = 1"
                :disabled="currentPage === 1"
                class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span class="sr-only">First</span>
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="currentPage = page"
                :class="[
                  'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                  page === currentPage
                    ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                    : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                ]"
              >
                {{ page }}
              </button>
              <button
                @click="currentPage = totalPages"
                :disabled="currentPage === totalPages"
                class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span class="sr-only">Last</span>
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
              </button>
            </nav>
          </div>
        </div>
      </div>

      <!-- Document Viewer Modal -->
      <DocumentViewer
        v-if="viewingDocument"
        :document="viewingDocument"
        :project-id="projectId"
        @close="viewingDocument = null"
        @reprocess="reprocessDocument"
      />


      <!-- Batch Actions Modal -->
      <BatchActionsModal
        v-if="showBatchActions"
        :action="batchAction"
        :documents="selectedDocuments"
        :project-id="projectId"
        @close="showBatchActions = false"
        @complete="handleBatchComplete"
      />
    </div>

    <div v-else-if="activeTab === 'groups'">
      <DocumentGroups
        :project-id="projectId"
        :documents="documents"
        :document-sets="documentSets"
        @refresh="fetchDocumentSets"
      />
    </div>


  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { api } from '@/services/api.js';
import { useToast } from 'vue-toastification';
import { debounce } from 'perfect-debounce';
import FileIcon from '../common/FileIcon.vue';
import LoadingSpinner from '../common/LoadingSpinner.vue';
import DocumentViewer from './DocumentViewer.vue';
import DocumentCard from './DocumentCard.vue';
import BatchActionsModal from './BatchActionsModal.vue';
import DocumentGroups from './DocumentsGroups.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const toast = useToast();

// State
const documents = ref([]);
const preprocessingTasks = ref([]);
const configurations = ref([]);
const isLoading = ref(true);
const selectedDocuments = ref([]);
const viewingDocument = ref(null);
const showBatchActions = ref(false);
const batchAction = ref('');
const viewMode = ref('grid');
const currentPage = ref(1);
const itemsPerPage = ref(20);
const activeTab = ref('documents');
const documentSets = ref([]);

// Filters
const filters = ref({
  search: '',
  taskId: '',
  configId: '',
  dateRange: '',
  ocrLanguage: '',
  status: ''
});

// Stats
const totalDocuments = computed(() => documents.value.length);
const recentDocuments = computed(() => {
  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);
  return documents.value.filter(doc => new Date(doc.created_at) > weekAgo).length;
});

// Filtered documents
const filteredDocuments = computed(() => {
  let result = [...documents.value];

  // Search filter
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase();
    result = result.filter(doc =>
      doc.original_file?.file_name?.toLowerCase().includes(search) ||
      doc.text?.toLowerCase().includes(search)
    );
  }

  // Task filter
  if (filters.value.taskId) {
    result = result.filter(doc => doc.preprocessing_task_id === parseInt(filters.value.taskId));
  }

  // Config filter
  if (filters.value.configId) {
    result = result.filter(doc => doc.preprocessing_config?.id === parseInt(filters.value.configId));
  }

  // Date range filter
  if (filters.value.dateRange) {
    const now = new Date();
    let startDate;

    switch (filters.value.dateRange) {
      case 'today':
        startDate = new Date(now.setHours(0, 0, 0, 0));
        break;
      case 'week':
        startDate = new Date(now.setDate(now.getDate() - 7));
        break;
      case 'month':
        startDate = new Date(now.setDate(now.getDate() - 30));
        break;
    }

    if (startDate) {
      result = result.filter(doc => new Date(doc.created_at) >= startDate);
    }
  }

  // OCR language filter
  if (filters.value.ocrLanguage) {
    result = result.filter(doc =>
      doc.preprocessing_config?.ocr_languages?.includes(filters.value.ocrLanguage)
    );
  }

  // Status filter
  if (filters.value.status) {
    result = result.filter(doc => doc.preprocessing_status === filters.value.status);
  }

  return result;
});

// Pagination
const totalPages = computed(() => Math.ceil(filteredDocuments.value.length / itemsPerPage.value));
const paginatedDocuments = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return filteredDocuments.value.slice(start, end);
});

const visiblePages = computed(() => {
  const pages = [];
  const total = totalPages.value;
  const current = currentPage.value;

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i);
      }
      pages.push('...');
      pages.push(total);
    } else if (current >= total - 2) {
      pages.push(1);
      pages.push('...');
      for (let i = total - 4; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      pages.push('...');
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i);
      }
      pages.push('...');
      pages.push(total);
    }
  }

  return pages.filter(p => p === '...' || (p >= 1 && p <= total));
});

// Methods
const fetchDocuments = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/document`);
    documents.value = response.data;

    // Extract unique preprocessing tasks
    const taskMap = new Map();
    documents.value.forEach(doc => {
      if (doc.preprocessing_task_id && !taskMap.has(doc.preprocessing_task_id)) {
        taskMap.set(doc.preprocessing_task_id, {
          id: doc.preprocessing_task_id,
          documentCount: 0
        });
      }
      if (doc.preprocessing_task_id) {
        taskMap.get(doc.preprocessing_task_id).documentCount++;
      }
    });
    preprocessingTasks.value = Array.from(taskMap.values());

    // Fetch configurations
    const configResponse = await api.get(`/project/${props.projectId}/preprocessing-config`);
    configurations.value = configResponse.data;
  } catch (error) {
    toast.error('Failed to load documents');
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const fetchDocumentSets = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/document-set`);
    documentSets.value = response.data;
  } catch (error) {
    console.error('Failed to fetch document sets:', error);
  }
};

const toggleDocumentSelection = (docId) => {
  const index = selectedDocuments.value.indexOf(docId);
  if (index > -1) {
    selectedDocuments.value.splice(index, 1);
  } else {
    selectedDocuments.value.push(docId);
  }
};

const toggleSelectAll = () => {
  if (areAllDocumentsSelected.value) {
    selectedDocuments.value = [];
  } else {
    selectedDocuments.value = paginatedDocuments.value.map(doc => doc.id);
  }
};

const areAllDocumentsSelected = computed(() => {
  return paginatedDocuments.value.length > 0 &&
    paginatedDocuments.value.every(doc => selectedDocuments.value.includes(doc.id));
});

const viewDocument = (doc) => {
  viewingDocument.value = doc;
};

const downloadDocument = async (doc) => {
  try {
    const fileId = doc.preprocessed_file?.id || doc.original_file?.id;
    if (!fileId) {
      toast.error('No file available for download');
      return;
    }

    const response = await api.get(`/project/${props.projectId}/file/${fileId}/content`, {
      responseType: 'blob'
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', doc.original_file?.file_name || `document_${doc.id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    toast.error('Failed to download document');
    console.error(error);
  }
};

const performBatchAction = (action) => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first');
    return;
  }

  batchAction.value = action;
  showBatchActions.value = true;
};

const handleBatchComplete = () => {
  selectedDocuments.value = [];
  showBatchActions.value = false;
  fetchDocuments();
};

const reprocessDocument = async (doc) => {
  try {
    const fileId = doc.original_file?.id;
    const configId = doc.preprocessing_config?.id;
    if (!fileId) {
      console.error('Original file id not found for this document!');
      toast.error('Original file id not found for this document!');
      return;
    }
    if (!configId) {
      console.error('Preprocessing configuration not found for this document!');
      toast.error('Preprocessing configuration not found for this document!');
      return;
    }
    const payload = {
      file_ids: [fileId],
      configuration_id: configId,
      force_reprocess: true
    };
    await api.post(`/project/${props.projectId}/preprocess`, payload);
    toast.success('Document reprocessing started!');
    fetchDocuments();
  } catch (error) {
    toast.error(
      error?.response?.data?.detail?.[0]?.msg ||
      'Failed to start reprocessing'
    );
    console.error(error);
  }
};



const clearFilters = () => {
  filters.value = {
    search: '',
    taskId: '',
    configId: '',
    dateRange: '',
    ocrLanguage: '',
    status: ''
  };
  currentPage.value = 1;
};

const getStatusClass = (status) => {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800';
    case 'partial':
      return 'bg-yellow-100 text-yellow-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
};

// Debounced search
const debouncedSearch = debounce(() => {
  currentPage.value = 1;
}, 300);

// Watchers
watch(() => filters.value.search, debouncedSearch);

watch([
  () => filters.value.taskId,
  () => filters.value.configId,
  () => filters.value.dateRange,
  () => filters.value.ocrLanguage,
  () => filters.value.status
], () => {
  currentPage.value = 1;
});

// Lifecycle
onMounted(() => {
  fetchDocuments();
  fetchDocumentSets();
});
</script>

