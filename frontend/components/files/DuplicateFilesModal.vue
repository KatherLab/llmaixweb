<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
      @click="$emit('cancel')"
    >
      <div
        class="bg-white rounded-lg shadow-xl w-full max-w-2xl"
        @click.stop
      >
        <!-- Header -->
        <div class="px-6 py-4 bg-amber-50 border-b border-amber-200">
          <div class="flex items-center">
            <svg class="h-6 w-6 text-amber-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h3 class="text-lg font-medium text-gray-900">Duplicate Files Detected</h3>
          </div>
        </div>

        <!-- Content -->
        <div class="p-6">
          <p class="text-sm text-gray-600 mb-4">
            The following files already exist in this project:
          </p>

          <div class="max-h-64 overflow-y-auto space-y-2">
            <div
              v-for="duplicate in duplicates"
              :key="duplicate.hash"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                  <FileIcon :fileType="getFileType(duplicate.filename)" :size="32" />
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ duplicate.filename }}</p>
                    <p class="text-xs text-gray-500">
                      Already exists as: {{ duplicate.existing_file.file_name }}
                    </p>
                    <p class="text-xs text-gray-400">
                      Uploaded: {{ formatDate(duplicate.existing_file.created_at) }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p class="text-sm text-blue-800">
              <strong>Tip:</strong> Files are compared using their content hash, so even renamed files will be detected as duplicates if their content is identical.
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-6 py-4 bg-gray-50 border-t flex justify-between">
          <button
            @click="$emit('cancel')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel Upload
          </button>
          <div class="space-x-3">
            <button
              @click="$emit('proceed', true)"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Skip Duplicates
            </button>
            <button
              @click="$emit('proceed', false)"
              class="px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700"
            >
              Upload All Anyway
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import FileIcon from '../common/FileIcon.vue';

defineProps({
  duplicates: {
    type: Array,
    required: true
  }
});

defineEmits(['proceed', 'cancel']);

const getFileType = (filename) => {
  const ext = filename.split('.').pop().toLowerCase();
  const typeMap = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'txt': 'text/plain',
    'csv': 'text/csv',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  };
  return typeMap[ext] || 'application/octet-stream';
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleString();
};
</script>
