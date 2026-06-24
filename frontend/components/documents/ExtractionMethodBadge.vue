<template>
  <span
    v-if="extractionMethodInfo"
    :class="['inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', pillClass]"
    :title="extractionMethodInfo.description"
  >
    <svg
      v-if="extractionMethodInfo.icon"
      class="w-3.5 h-3.5 mr-1.5"
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
</template>

<script setup>
import { computed } from 'vue'
import { getPillClass } from '@/utils/statusStyles'

const props = defineProps({
  document: { type: Object, required: true },
})

// Extraction method info for display badges. `color` keys into the shared
// getPillClass map (dark-mode aware) instead of hard-coded bg/text classes.
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
      color: 'blue',
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
      color: 'green',
      description: 'Processed with local Tesseract OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (extractionMethod === 'docling_serve_tesseract_force_ocr') {
    return {
      label: 'Force OCR',
      color: 'yellow',
      description: 'Full-page OCR forced (even if embedded text exists)',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  if (ocrEngine === 'mistral_ocr' || engineUsed === 'mistral_ocr') {
    return {
      label: 'Mistral OCR',
      color: 'purple',
      description: 'Processed with Mistral AI OCR API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  if (ocrEngine === 'llm_vision' || engineUsed === 'llm_vision') {
    return {
      label: 'Vision LLM',
      color: 'indigo',
      description: 'Processed with Vision LLM API',
      icon: true,
      iconPath: remoteIconPath,
    }
  }

  // Fallback for legacy methods
  if (extractionMethod?.includes('no_ocr')) {
    return {
      label: 'Text Extraction',
      color: 'blue',
      description: 'Extracted from embedded PDF text',
      icon: true,
      iconPath: textIconPath,
    }
  }

  if (extractionMethod?.includes('tesseract') || extractionMethod?.includes('ocr')) {
    return {
      label: 'OCR',
      color: 'green',
      description: 'Processed with OCR',
      icon: true,
      iconPath: ocrIconPath,
    }
  }

  return null
})

const pillClass = computed(() =>
  extractionMethodInfo.value ? getPillClass(extractionMethodInfo.value.color) : '',
)
</script>
