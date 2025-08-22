<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('close')"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col border border-gray-200"
        @click.stop
      >
        <!-- Header -->
        <div class="flex justify-between items-center p-6 border-b bg-gray-50 rounded-t-2xl">
          <div class="flex items-center gap-4">
            <FileIcon :fileType="file.file_type" :size="32" />
            <div>
              <h3 class="text-xl font-bold text-gray-900">{{ file.file_name }}</h3>
              <p class="text-xs text-gray-500">
                {{ formatFileSize(file.file_size) }} &middot; {{ file.file_type }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="downloadFile"
              class="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-xl transition"
              title="Download"
            >
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
              </svg>
            </button>
            <button
              @click="$emit('close')"
              class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition"
            >
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Preview Content -->
        <div class="flex-1 overflow-hidden bg-gray-50">
          <!-- Loading State -->
          <div v-if="isLoading" class="flex items-center justify-center h-full">
            <LoadingSpinner size="large" />
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="flex items-center justify-center h-full">
            <div class="text-center max-w-sm mx-auto">
              <svg class="mx-auto h-12 w-12 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p class="mt-3 text-base text-gray-500">{{ error }}</p>
              <button
                @click="loadPreview"
                class="mt-5 text-sm text-blue-600 hover:text-blue-800"
              >
                Try Again
              </button>
            </div>
          </div>

          <!-- PDF Preview -->
          <iframe
            v-else-if="previewUrl && file.file_type === 'application/pdf'"
            :src="previewUrl"
            class="w-full h-full rounded-b-2xl border-none"
            title="PDF preview"
          ></iframe>

          <!-- Image Preview -->
          <div
            v-else-if="previewUrl && file.file_type?.startsWith('image/')"
            class="flex items-center justify-center h-full p-10 bg-white rounded-b-2xl"
          >
            <img
              :src="previewUrl"
              :alt="file.file_name"
              class="max-w-full max-h-[70vh] object-contain rounded-xl border"
            />
          </div>

          <!-- CSV/XLSX Table Preview -->
          <div
            v-else-if="tabularData && headerLabels.length"
            class="h-full overflow-auto p-6"
          >
            <div class="bg-white rounded-2xl shadow border border-gray-100 overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-100 rounded-xl text-sm table-auto">
                <thead class="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th
                      v-for="(header, idx) in headerLabels"
                      :key="header || idx"
                      class="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider border-b border-gray-100 whitespace-nowrap sticky top-0 bg-gray-50"
                      :class="cellClasses(header)"
                    >
                      {{ headerLabel(header) }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="(row, ridx) in tabularData.rows" :key="ridx" class="hover:bg-blue-50 transition">
                    <td
                      v-for="(cell, cidx) in row"
                      :key="cidx"
                      class="px-4 py-2 border-b border-gray-50 max-w-[260px] align-top"
                      :class="cellClasses(headerLabels[cidx])"
                    >
                      <span v-if="cell === '' || cell == null" class="text-gray-300 italic">empty</span>
                      <template v-else-if="isTextColumn(headerLabels[cidx]) && String(cell).length > 80">
                        <span
                          class="truncate cursor-pointer text-green-900"
                          :title="String(cell)"
                          @click="showFullCell(String(cell), headerLabels[cidx])"
                        >{{ String(cell).slice(0, 80) }}<span class="font-semibold text-blue-600 ml-1">…more</span></span>
                      </template>
                      <template v-else>
                        {{ cell }}
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="truncated" class="px-4 py-2 bg-gray-50 text-xs text-gray-500 rounded-b-2xl text-center">
                Showing first {{ tabularData.rows.length }} of {{ totalRows }} rows
              </div>
            </div>
            <div class="flex flex-wrap gap-2 mt-4">
              <span v-if="idColumn" class="inline-flex items-center px-3 py-1 rounded bg-blue-100 text-blue-800 text-xs font-medium">
                <span class="mr-1 font-bold">ID column:</span> {{ idColumn }}
              </span>
              <span v-if="textColumns && textColumns.length" class="inline-flex items-center px-3 py-1 rounded bg-green-50 text-green-800 text-xs font-medium">
                <span class="mr-1 font-bold">Text columns:</span> {{ textColumns.join(', ') }}
              </span>
            </div>
          </div>

          <!-- Text File Preview -->
          <div
            v-else-if="previewContent && file.file_type === 'text/plain'"
            class="h-full overflow-auto p-8"
          >
            <pre class="text-sm font-mono whitespace-pre-wrap bg-white rounded-lg shadow p-6 border border-gray-100">{{ previewContent }}</pre>
          </div>

          <!-- Fallback / Unsupported File Type -->
          <div v-else class="flex items-center justify-center h-full">
            <div class="text-center">
              <FileIcon :fileType="file.file_type" :size="64" />
              <p class="mt-4 text-sm text-gray-500">
                Preview not available for this file type.
              </p>
              <button
                @click="downloadFile"
                class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition"
              >
                <svg class="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                </svg>
                Download File
              </button>
            </div>
          </div>
        </div>

        <!-- File Info Footer -->
        <div class="border-t bg-gray-50 px-6 py-3 rounded-b-2xl">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center gap-6 text-gray-500">
              <span>Created: {{ formatDate(file.created_at) }}</span>
              <span v-if="file.file_hash" class="font-mono text-xs">
                Hash: {{ file.file_hash.substring(0, 8) }}...
              </span>
            </div>
            <div v-if="file.description" class="text-gray-600 truncate">
              {{ file.description }}
            </div>
          </div>
        </div>
      </div>

      <!-- Modal for full text cell -->
      <div v-if="showModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click="closeModal">
        <div class="bg-white rounded-xl shadow-xl max-w-xl w-full mx-4 p-6 border border-gray-100 relative" @click.stop>
          <button
            @click="closeModal"
            class="absolute top-2 right-2 text-gray-400 hover:text-gray-700 p-1 rounded transition"
            title="Close"
          >
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div class="mb-2 font-semibold text-gray-700" v-if="modalHeader">
            {{ modalHeader }}
          </div>
          <pre class="whitespace-pre-wrap text-sm text-gray-900 bg-gray-50 rounded p-4 max-h-[60vh] overflow-auto">{{ modalContent }}</pre>
          <button
            class="mt-4 text-xs text-blue-600 hover:text-blue-800 underline"
            @click="copyToClipboard"
          >
            Copy
          </button>
          <span v-if="copied" class="ml-2 text-green-700 text-xs">Copied!</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import FileIcon from '@/components/common/FileIcon.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const props = defineProps({
  file: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
});
const emit = defineEmits(['close']);
const toast = useToast();

const isLoading = ref(true);
const error = ref('');
const previewUrl = ref('');
const previewContent = ref('');

const tabularData = ref(null);
const truncated = ref(false);
const totalRows = ref(0);

// Metadata from backend / file metadata
const idColumn = ref('');
const textColumns = ref([]);

// Modal for showing full text content
const showModal = ref(false);
const modalContent = ref('');
const modalHeader = ref('');
const copied = ref(false);

// Derive header labels (no null/empty headers)
const headerLabels = computed(() =>
  (tabularData.value?.headers || []).map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return `Column ${idx + 1}`;
    }
    return String(h);
  })
);

function showFullCell(cell, header) {
  modalContent.value = cell;
  modalHeader.value = header ? `${header}` : '';
  showModal.value = true;
  copied.value = false;
}
function closeModal() {
  showModal.value = false;
  modalContent.value = '';
  modalHeader.value = '';
  copied.value = false;
}
function copyToClipboard() {
  navigator.clipboard.writeText(modalContent.value || '').then(() => {
    copied.value = true;
    setTimeout(() => (copied.value = false), 1500);
  });
}

const isCSV = computed(() => props.file.file_type === 'text/csv');
const isXLSX = computed(() =>
  ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'].includes(props.file.file_type)
);

const loadPreview = async () => {
  isLoading.value = true;
  error.value = '';
  previewUrl.value = '';
  previewContent.value = '';
  tabularData.value = null;
  truncated.value = false;
  totalRows.value = 0;

  try {
    if (isCSV.value || isXLSX.value) {
      const params = new URLSearchParams({ max_rows: 50 });
      const { data } = await api.get(
        `/project/${props.projectId}/file/${props.file.id}/preview-rows?${params}`
      );
      tabularData.value = {
        headers: data.headers || [],
        rows: data.rows || []
      };
      truncated.value = !!(data.truncated);
      totalRows.value = data.total_rows || data.totalRows || 0;
      idColumn.value = data.idColumn || data.id_column || props.file.file_metadata?.case_id_column || '';
      textColumns.value = data.textColumns || data.text_columns || props.file.file_metadata?.text_columns || [];
    } else if (props.file.file_type === 'text/plain') {
      const response = await api.get(
        `/project/${props.projectId}/file/${props.file.id}/content?preview=true`,
        { responseType: 'blob' }
      );
      previewContent.value = await response.data.text();
    } else if (props.file.file_type === 'application/pdf') {
      const response = await api.get(
        `/project/${props.projectId}/file/${props.file.id}/content?preview=true`,
        { responseType: 'blob' }
      );
      previewUrl.value = URL.createObjectURL(response.data);
    } else if (props.file.file_type.startsWith('image/')) {
      const response = await api.get(
        `/project/${props.projectId}/file/${props.file.id}/content?preview=true`,
        { responseType: 'blob' }
      );
      previewUrl.value = URL.createObjectURL(response.data);
    } else {
      error.value = 'Preview not available for this file type.';
    }
  } catch (err) {
    error.value = 'Failed to load preview';
    console.error('Preview error:', err);
  } finally {
    isLoading.value = false;
  }
};

const downloadFile = async () => {
  try {
    const response = await api.get(
      `/project/${props.projectId}/file/${props.file.id}/content`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', props.file.file_name);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    toast.success('File downloaded successfully');
  } catch (err) {
    toast.error('Failed to download file');
    console.error(err);
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
  return new Date(dateString).toLocaleString();
};

onMounted(() => {
  loadPreview();
  document.body.style.overflow = 'hidden';
});
onUnmounted(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
  document.body.style.overflow = '';
});

function cellClasses(headerLabel) {
  if (headerLabel === idColumn.value && idColumn.value) {
    return 'bg-blue-100 text-blue-700 font-semibold border-blue-200 shadow-sm';
  }
  if (textColumns.value && textColumns.value.includes(headerLabel)) {
    return 'bg-green-50 text-green-900 font-medium border-green-200';
  }
  return '';
}
function headerLabel(headerLabel) {
  if (!headerLabel) return '';
  if (headerLabel === idColumn.value) return `${headerLabel} (ID)`;
  if (textColumns.value && textColumns.value.includes(headerLabel)) return `${headerLabel} (Text)`;
  return headerLabel;
}
function isTextColumn(headerLabel) {
  return textColumns.value && textColumns.value.includes(headerLabel);
}
</script>
