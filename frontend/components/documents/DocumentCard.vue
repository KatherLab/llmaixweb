<template>
  <div
    :class="[
      'relative group bg-white rounded-lg border-2 p-4 transition-all cursor-pointer',
      selected
        ? 'border-blue-500 shadow-md'
        : 'border-gray-200 hover:border-gray-300 hover:shadow-sm',
    ]"
    @click="$emit('toggle-selection', document.id)"
  >
    <!-- Selection Checkbox -->
    <div class="absolute top-2 right-2">
      <input
        type="checkbox"
        :checked="selected"
        class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        @click.stop
        @change="$emit('toggle-selection', document.id)"
      />
    </div>

    <!-- Document Icon -->
    <div class="flex items-start space-x-3 mb-3">
      <div class="flex-shrink-0">
        <FileIcon :file-type="document.original_file?.file_type" :size="48" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-medium text-gray-900 truncate" :title="documentTitle">
          {{ documentTitle }}
        </h3>
        <p class="text-xs text-gray-500 mt-1">
          {{ formatDate(document.created_at) }}
        </p>
      </div>
    </div>

    <!-- Text Preview -->
    <div class="mb-3">
      <p class="text-xs text-gray-600 line-clamp-3">
        {{ document.text || 'No text content available' }}
      </p>
    </div>

    <!-- Preprocessing Info -->
    <div class="flex items-center justify-between text-xs">
      <div class="flex items-center space-x-2">
        <span
          :class="[
            'inline-flex items-center px-2 py-0.5 rounded-full font-medium',
            getStatusClass(document.preprocessing_status),
          ]"
        >
          {{ document.preprocessing_status || 'Processed' }}
        </span>
        <span
          v-if="document.preprocessing_config?.name"
          class="text-gray-500 truncate max-w-[120px]"
        >
          {{ document.preprocessing_config.name }}
        </span>
      </div>
    </div>

    <!-- Extraction Method Badge -->
    <div v-if="extractionMethodInfo" class="mt-2">
      <span
        :class="[
          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
          extractionMethodInfo.bgClass,
          extractionMethodInfo.textClass,
        ]"
        :title="extractionMethodInfo.description"
      >
        <svg
          v-if="extractionMethodInfo.icon"
          class="w-3 h-3 mr-1"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            :d="extractionMethodInfo.iconPath"
          />
        </svg>
        {{ extractionMethodInfo.label }}
      </span>
    </div>

    <!-- Actions -->
    <div
      class="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-2"
    >
      <button
        class="p-1 text-blue-600 hover:text-blue-800"
        title="View"
        @click.stop="$emit('view', document)"
      >
        <svg
          class="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
          />
        </svg>
      </button>
      <button
        class="p-1 text-gray-600 hover:text-gray-800"
        title="Download"
        @click.stop="$emit('download', document)"
      >
        <svg
          class="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import FileIcon from '../common/FileIcon.vue'

const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

// emit is available but not used since we use direct event handlers

const documentTitle = computed(() => {
  return (
    props.document.document_name ||
    props.document.original_file?.file_name ||
    `Document #${props.document.id}`
  )
})

// Extract metadata to determine extraction method
const extractionMethodInfo = computed(() => {
  const metaData = props.document.meta_data || {}
  const extractionMethod = metaData.extraction_method
  const ocrEngine = metaData.ocr_engine
  const engineUsed = metaData.engine_used
  const ocrApplied = metaData.ocr_applied
  // embeddedText is available if needed for future logic

  // Icon paths
  const textIconPath =
    'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  const ocrIconPath = 'M13 10V3L4 14h7v7l9-11h-7z'
  const remoteIconPath =
    'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9'

  // Determine extraction method label and styling
  if (
    extractionMethod === 'docling_serve_no_ocr' ||
    (engineUsed === 'docling_serve' && !ocrApplied)
  ) {
    return {
      label: 'Text Extraction',
      bgClass: 'bg-blue-100',
      textClass: 'text-blue-800',
      description: 'Extracted from embedded PDF text (no OCR)',
      icon: true,
      iconPath: textIconPath,
    }
  }

  if (
    extractionMethod === 'docling_serve_tesseract_ocr' ||
    extractionMethod === 'docling_serve_tesseract_image_ocr'
  ) {
    return {
      label: 'Local OCR',
      bgClass: 'bg-green-100',
      textClass: 'text-green-800',
      description: 'Processed with local Tesseract OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (extractionMethod === 'docling_serve_tesseract_force_ocr') {
    return {
      label: 'Force OCR',
      bgClass: 'bg-amber-100',
      textClass: 'text-amber-800',
      description: 'Full-page OCR forced (even if embedded text exists)',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (ocrEngine === 'mistral_ocr' || engineUsed === 'mistral_ocr') {
    return {
      label: 'Mistral OCR',
      bgClass: 'bg-purple-100',
      textClass: 'text-purple-800',
      description: 'Processed with Mistral AI OCR API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  if (ocrEngine === 'llm_vision' || engineUsed === 'llm_vision') {
    return {
      label: 'Vision LLM',
      bgClass: 'bg-indigo-100',
      textClass: 'text-indigo-800',
      description: 'Processed with Vision LLM API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  // Fallback for legacy methods
  if (extractionMethod?.includes('no_ocr')) {
    return {
      label: 'Text Extraction',
      bgClass: 'bg-blue-100',
      textClass: 'text-blue-800',
      description: 'Extracted from embedded PDF text',
      icon: true,
      iconPath: textIconPath,
    }
  }

  if (extractionMethod?.includes('tesseract') || extractionMethod?.includes('ocr')) {
    return {
      label: 'OCR',
      bgClass: 'bg-green-100',
      textClass: 'text-green-800',
      description: 'Processed with OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  return null
})

const getStatusClass = (status) => {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800'
    case 'partial':
      return 'bg-yellow-100 text-yellow-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString()
}
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
