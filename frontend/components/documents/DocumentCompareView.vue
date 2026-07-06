<template>
  <div class="flex h-full">
    <!-- Show split view only if displayable original file exists -->
    <template v-if="hasDisplayableOriginalFile">
      <!-- Left: Original File (PDF or Image) -->
      <div class="w-1/2 border-r overflow-auto p-4 flex flex-col">
        <h4 class="font-medium text-content-muted mb-2">Original File</h4>
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
          v-else-if="originalImageUrl && ['image'].includes(originalFileType ?? '')"
          class="flex-1 flex items-center justify-center bg-surface-sunken rounded-card p-4"
        >
          <img
            :src="originalImageUrl"
            alt="Original document"
            class="max-w-full max-h-full object-contain"
          />
        </div>
        <div v-else class="text-content-subtle flex items-center justify-center flex-1">
          No original file available
        </div>
      </div>
      <!-- Right: Extracted Text -->
      <div class="w-1/2 overflow-auto p-4 flex flex-col">
        <h4 class="font-medium text-content-muted mb-2">Extracted Text</h4>
        <div
          class="markdown-content max-w-none bg-surface-muted p-2 rounded-card flex-1"
          v-html="safeMarkdown"
        />
      </div>
    </template>
    <!-- No displayable original file: show only extracted text (full width) -->
    <div v-else class="w-full overflow-auto p-4 flex flex-col">
      <h4 class="font-medium text-content-muted mb-2">Extracted Text</h4>
      <div
        class="markdown-content max-w-none bg-surface-muted p-4 rounded-card"
        v-html="safeMarkdown"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  hasDisplayableOriginalFile?: boolean
  originalPdfUrl?: string
  originalImageUrl?: string
  // Parent (DocumentViewer) computes 'pdf' | 'image' | 'other' | null; typed as
  // string here so template `includes(...)` checks pass (runtime null is harmless).
  originalFileType?: string
  safeMarkdown?: string
}

withDefaults(defineProps<Props>(), {
  hasDisplayableOriginalFile: false,
  originalPdfUrl: '',
  originalImageUrl: '',
  originalFileType: '',
  safeMarkdown: '',
})
</script>
