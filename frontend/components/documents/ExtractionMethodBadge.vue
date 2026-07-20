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

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { FileText, Globe, Zap } from '@lucide/vue'
import { getPillClass } from '@/utils/statusStyles'
import type { DocumentListItem } from '@/types'

interface Props {
  document: DocumentListItem
}

const props = defineProps<Props>()
const { t } = useI18n({ useScope: 'global' })

interface ExtractionMethodInfo {
  label: string
  color: string
  description: string
  icon: Component
}

// Extraction method info for display badges. `color` keys into the shared
// getPillClass map (dark-mode aware) instead of hard-coded bg/text classes.
// `icon` is a Lucide component (FileText = embedded text, Zap = local OCR,
// Globe = remote API OCR).
const extractionMethodInfo = computed<ExtractionMethodInfo | null>(() => {
  const metaData = props.document.meta_data || {}
  const extractionMethod = metaData.extraction_method
  const ocrEngine = metaData.ocr_engine
  const engineUsed = metaData.engine_used as string | undefined
  const ocrApplied = metaData.ocr_applied as boolean | undefined
  // embeddedText is available if needed for future logic

  // Determine extraction method label and styling
  if (
    extractionMethod === 'docling_serve_no_ocr' ||
    (engineUsed === 'docling_serve' && !ocrApplied)
  ) {
    return {
      label: t('documents.extraction.text_extraction'),
      color: 'blue',
      description: t('documents.extraction.desc_text_no_ocr'),
      icon: FileText,
    }
  }

  if (
    extractionMethod === 'docling_serve_tesseract_ocr' ||
    extractionMethod === 'docling_serve_tesseract_image_ocr'
  ) {
    return {
      label: t('documents.extraction.local_ocr'),
      color: 'green',
      description: t('documents.extraction.desc_local_ocr'),
      icon: Zap,
    }
  }

  if (extractionMethod === 'docling_serve_tesseract_force_ocr') {
    return {
      label: t('documents.extraction.force_ocr'),
      color: 'yellow',
      description: t('documents.extraction.desc_force_ocr'),
      icon: Zap,
    }
  }

  if (ocrEngine === 'mistral_ocr' || engineUsed === 'mistral_ocr') {
    return {
      label: 'Mistral OCR',
      color: 'purple',
      description: t('documents.extraction.desc_mistral'),
      icon: Globe,
    }
  }

  if (ocrEngine === 'llm_vision' || engineUsed === 'llm_vision') {
    return {
      label: 'Vision LLM',
      color: 'blue',
      description: t('documents.extraction.desc_vision'),
      icon: Globe,
    }
  }

  // Fallback for legacy methods
  if (extractionMethod?.includes('no_ocr')) {
    return {
      label: t('documents.extraction.text_extraction'),
      color: 'blue',
      description: t('documents.extraction.desc_text_embedded'),
      icon: FileText,
    }
  }

  if (extractionMethod?.includes('tesseract') || extractionMethod?.includes('ocr')) {
    return {
      label: 'OCR',
      color: 'green',
      description: t('documents.extraction.desc_ocr_generic'),
      icon: Zap,
    }
  }

  return null
})

const pillClass = computed(() =>
  extractionMethodInfo.value ? getPillClass(extractionMethodInfo.value.color) : '',
)
</script>
