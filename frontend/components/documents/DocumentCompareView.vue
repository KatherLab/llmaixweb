<template>
  <div class="flex h-full">
    <!-- Show split view only if displayable original file exists -->
    <template v-if="hasDisplayableOriginalFile">
      <!-- Left: Original File (PDF or Image) -->
      <div class="w-1/2 border-r overflow-auto p-4 flex flex-col">
        <h4 class="font-medium text-gray-700 mb-2">Original File</h4>
        <!-- PDF Viewer -->
        <iframe
          v-if="originalPdfUrl && originalFileType === 'pdf'"
          :src="originalPdfUrl"
          class="w-full flex-1"
          frameborder="0"
          title="Original PDF"
        ></iframe>
        <!-- Image Viewer -->
        <div
          v-else-if="originalImageUrl && ['image'].includes(originalFileType)"
          class="flex-1 flex items-center justify-center bg-gray-100 rounded-lg p-4"
        >
          <img
            :src="originalImageUrl"
            alt="Original document"
            class="max-w-full max-h-full object-contain"
          />
        </div>
        <div v-else class="text-gray-400 flex items-center justify-center flex-1">
          No original file available
        </div>
      </div>
      <!-- Right: Extracted Text -->
      <div class="w-1/2 overflow-auto p-4 flex flex-col">
        <h4 class="font-medium text-gray-700 mb-2">Extracted Text</h4>
        <div class="prose max-w-none bg-gray-50 p-2 rounded-lg flex-1" v-html="safeMarkdown" />
      </div>
    </template>
    <!-- No displayable original file: show only extracted text (full width) -->
    <div v-else class="w-full overflow-auto p-4 flex flex-col">
      <h4 class="font-medium text-gray-700 mb-2">Extracted Text</h4>
      <div class="prose max-w-none bg-gray-50 p-4 rounded-lg" v-html="safeMarkdown" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  hasDisplayableOriginalFile: { type: Boolean, default: false },
  originalPdfUrl: { type: String, default: '' },
  originalImageUrl: { type: String, default: '' },
  originalFileType: { type: String, default: null },
  safeMarkdown: { type: String, default: '' },
})
</script>
