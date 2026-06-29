<template>
  <span
    v-if="extractionMethodInfo"
    :class="['inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', pillClass]"
    :title="extractionMethodInfo.description"
  >
    <component
      :is="extractionMethodInfo.icon"
      v-if="extractionMethodInfo.icon"
      class="w-3.5 h-3.5 mr-1.5"
    />
    {{ extractionMethodInfo.label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { FileText, Globe, Zap } from '@lucide/vue'
import { getPillClass } from '@/utils/statusStyles'

const props = defineProps({
  document: { type: Object, required: true },
})

// Extraction method info for display badges. `color` keys into the shared
// getPillClass map (dark-mode aware) instead of hard-coded bg/text classes.
// `icon` is a Lucide component (FileText = embedded text, Zap = local OCR,
// Globe = remote API OCR).
const extractionMethodInfo = computed(() => {
  const metaData = props.document.meta_data || {}
  const extractionMethod = metaData.extraction_method
  const ocrEngine = metaData.ocr_engine
  const engineUsed = metaData.engine_used
  const ocrApplied = metaData.ocr_applied
  // embeddedText is available if needed for future logic

  // Determine extraction method label and styling
  if (
    extractionMethod === 'docling_serve_no_ocr' ||
    (engineUsed === 'docling_serve' && !ocrApplied)
  ) {
    return {
      label: 'Text Extraction',
      color: 'blue',
      description: 'Extracted from embedded PDF text (no OCR)',
      icon: FileText,
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
      icon: Zap,
    }
  }

  if (extractionMethod === 'docling_serve_tesseract_force_ocr') {
    return {
      label: 'Force OCR',
      color: 'yellow',
      description: 'Full-page OCR forced (even if embedded text exists)',
      icon: Zap,
    }
  }

  if (ocrEngine === 'mistral_ocr' || engineUsed === 'mistral_ocr') {
    return {
      label: 'Mistral OCR',
      color: 'purple',
      description: 'Processed with Mistral AI OCR API',
      icon: Globe,
    }
  }

  if (ocrEngine === 'llm_vision' || engineUsed === 'llm_vision') {
    return {
      label: 'Vision LLM',
      color: 'blue',
      description: 'Processed with Vision LLM API',
      icon: Globe,
    }
  }

  // Fallback for legacy methods
  if (extractionMethod?.includes('no_ocr')) {
    return {
      label: 'Text Extraction',
      color: 'blue',
      description: 'Extracted from embedded PDF text',
      icon: FileText,
    }
  }

  if (extractionMethod?.includes('tesseract') || extractionMethod?.includes('ocr')) {
    return {
      label: 'OCR',
      color: 'green',
      description: 'Processed with OCR',
      icon: Zap,
    }
  }

  return null
})

const pillClass = computed(() =>
  extractionMethodInfo.value ? getPillClass(extractionMethodInfo.value.color) : '',
)
</script>
