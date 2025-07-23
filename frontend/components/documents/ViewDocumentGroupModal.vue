<!-- ViewDocumentGroupModal.vue -->
<template>
  <div class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50" @click="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col" @click.stop>
      <div class="px-6 py-4 border-b flex justify-between items-center">
        <h3 class="text-xl font-semibold">{{ group.name }}</h3>
        <div class="flex items-center gap-2">
          <button
            @click="$emit('edit', group)"
            class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Edit Group
          </button>
          <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div class="p-6 overflow-y-auto flex-1">
        <!-- Group Info -->
        <div class="mb-6 space-y-4">
          <div>
            <h4 class="text-sm font-medium text-gray-700">Description</h4>
            <p class="mt-1 text-gray-900">{{ group.description || 'No description provided' }}</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <h4 class="text-sm font-medium text-gray-700">Created</h4>
              <p class="mt-1 text-gray-900">{{ formatDate(group.created_at) }}</p>
            </div>
            <div>
              <h4 class="text-sm font-medium text-gray-700">Last Updated</h4>
              <p class="mt-1 text-gray-900">{{ formatDate(group.updated_at) }}</p>
            </div>
          </div>

          <div v-if="group.tags && group.tags.length > 0">
            <h4 class="text-sm font-medium text-gray-700 mb-2">Tags</h4>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="tag in group.tags"
                :key="tag"
                class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
              >
                {{ tag }}
              </span>
            </div>
          </div>

          <div v-if="group.preprocessing_config">
            <h4 class="text-sm font-medium text-gray-700">Preprocessing Configuration</h4>
            <p class="mt-1 text-gray-900">{{ group.preprocessing_config.name }}</p>
          </div>

          <div v-if="group.trial_id">
            <h4 class="text-sm font-medium text-gray-700">Source Trial</h4>
            <p class="mt-1 text-gray-900">Trial #{{ group.trial_id }}</p>
          </div>
        </div>

        <!-- Documents List -->
        <div>
          <div class="flex justify-between items-center mb-4">
            <h4 class="font-medium text-gray-900">
              Documents ({{ group.documents.length }})
            </h4>
            <div class="flex items-center gap-2">
              <button
                @click="exportDocumentList"
                class="text-sm text-blue-600 hover:text-blue-800"
              >
                Export List
              </button>
              <button
                @click="downloadAllDocuments"
                class="text-sm text-blue-600 hover:text-blue-800"
              >
                Download All
              </button>
            </div>
          </div>

          <div class="border rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Document
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Configuration
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
                <tr v-for="doc in group.documents" :key="doc.id" class="hover:bg-gray-50">
                  <td class="px-6 py-4">
                    <div class="flex items-center">
                      <FileIcon :fileType="doc.original_file?.file_type" :size="32" />
                      <div class="ml-3">
                        <p class="text-sm font-medium text-gray-900">
                          {{ doc.original_file?.file_name || `Document #${doc.id}` }}
                        </p>
                        <p class="text-xs text-gray-500">
                          {{ formatFileSize(doc.original_file?.file_size) }}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {{ doc.preprocessing_config?.name || 'N/A' }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ formatDate(doc.created_at) }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      @click="viewDocument(doc)"
                      class="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Usage Statistics -->
        <div class="mt-6 bg-gray-50 rounded-lg p-4">
          <h4 class="font-medium text-gray-900 mb-3">Usage Statistics</h4>
          <div class="grid grid-cols-3 gap-4">
            <div>
              <p class="text-sm text-gray-600">Used in Trials</p>
              <p class="text-2xl font-semibold text-gray-900">{{ usageStats.trialsCount }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Total Extractions</p>
              <p class="text-2xl font-semibold text-gray-900">{{ usageStats.extractionsCount }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Last Used</p>
              <p class="text-sm font-medium text-gray-900">
                {{ usageStats.lastUsed ? formatDate(usageStats.lastUsed) : 'Never' }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import { formatDate, formatFileSize } from '@/utils/formatters';
import FileIcon from '../common/FileIcon.vue';

const props = defineProps({
  group: {
    type: Object,
    required: true
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'edit']);

const toast = useToast();
const usageStats = ref({
  trialsCount: 0,
  extractionsCount: 0,
  lastUsed: null
});

// Load usage statistics
onMounted(async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/document-set/${props.group.id}/stats`);
    usageStats.value = response.data;
  } catch (error) {
    console.error('Failed to load usage stats:', error);
  }
});

const viewDocument = (doc) => {
  // Implement document viewer
  window.open(`/project/${props.projectId}/document/${doc.id}`, '_blank');
};

const exportDocumentList = () => {
  const data = props.group.documents.map(doc => ({
    id: doc.id,
    filename: doc.original_file?.file_name || `Document #${doc.id}`,
    configuration: doc.preprocessing_config?.name || 'N/A',
    created: formatDate(doc.created_at)
  }));

  const csv = [
    ['ID', 'Filename', 'Configuration', 'Created'],
    ...data.map(row => [row.id, row.filename, row.configuration, row.created])
  ].map(row => row.join(',')).join('\n');

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${props.group.name.replace(/[^a-z0-9]/gi, '_')}_documents.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);

  toast.success('Document list exported');
};

const downloadAllDocuments = async () => {
  if (!confirm(`Download all ${props.group.documents.length} documents?`)) {
    return;
  }

  try {
    const response = await api.post(
      `/project/${props.projectId}/document-set/${props.group.id}/download-all`,
      {},
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${props.group.name.replace(/[^a-z0-9]/gi, '_')}_documents.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    toast.success('Download started');
  } catch (error) {
    toast.error('Failed to download documents');
    console.error(error);
  }
};
</script>
