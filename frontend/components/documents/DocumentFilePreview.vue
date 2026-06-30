<template>
  <!-- PDF View -->
  <div v-if="viewMode === 'pdf' && originalPdfUrl" class="h-full">
    <iframe
      :src="originalPdfUrl"
      class="w-full h-full"
      frameborder="0"
      title="Original PDF"
    ></iframe>
  </div>
  <!-- Image View (for original image files) -->
  <div
    v-else-if="viewMode === 'image' && originalImageUrl"
    class="h-full p-4 bg-slate-100 dark:bg-slate-800"
  >
    <div class="flex items-center justify-center h-full">
      <img
        :src="originalImageUrl"
        alt="Original document"
        class="max-w-full max-h-full object-contain shadow-lg rounded-lg"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  viewMode: { type: String, required: true },
  originalPdfUrl: { type: String, default: '' },
  originalImageUrl: { type: String, default: '' },
})
</script>
