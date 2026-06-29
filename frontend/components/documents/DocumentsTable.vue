<template>
  <div :class="t.wrapper">
    <table :class="t.table">
      <thead :class="t.thead">
        <tr>
          <th :class="[t.th, 'text-left']">
            <input
              type="checkbox"
              :checked="areAllSelected"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 rounded"
              @change="emit('toggle-select-all')"
            />
          </th>
          <th :class="t.th">Document</th>
          <th :class="t.th">Configuration</th>
          <th :class="t.th">Model</th>
          <th :class="t.th">Created</th>
          <th :class="[t.th, 'relative']">
            <span class="sr-only">Actions</span>
          </th>
        </tr>
      </thead>
      <tbody :class="t.tbody">
        <tr v-for="doc in documents" :key="doc.id" :class="t.tr">
          <td class="px-4 py-3 whitespace-nowrap">
            <input
              type="checkbox"
              :checked="selectedDocuments.includes(doc.id)"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 rounded"
              @change="emit('toggle-selection', doc.id)"
            />
          </td>
          <td :class="t.td">
            <div class="flex items-center">
              <FileIcon :file-type="doc.original_file?.file_type" :size="40" />
              <div class="ml-3">
                <p class="text-sm font-medium text-slate-900 dark:text-white truncate max-w-xs">
                  {{ doc.document_name || doc.original_file?.file_name || `Document #${doc.id}` }}
                </p>
                <p
                  v-if="
                    doc.document_name &&
                    doc.original_file?.file_name &&
                    doc.document_name !== doc.original_file?.file_name
                  "
                  class="text-xs text-slate-500 dark:text-slate-400 truncate max-w-xs"
                >
                  {{ doc.original_file?.file_name }}
                </p>
                <p v-else class="text-xs text-slate-500 dark:text-slate-400">
                  {{ formatFileSize(doc.original_file?.file_size) }}
                </p>
              </div>
            </div>
          </td>
          <td class="px-4 py-3 whitespace-nowrap">
            <div class="text-sm text-slate-900 dark:text-white">
              {{ doc.preprocessing_config?.name || 'Custom Config' }}
            </div>
            <div v-if="getOcrDisplay(doc)" class="text-xs text-slate-500 dark:text-slate-400">
              {{ getOcrDisplay(doc) }}
            </div>
          </td>
          <td class="px-4 py-3 whitespace-nowrap">
            <div class="text-sm text-slate-900 dark:text-white">
              {{ getModelName(doc) }}
            </div>
          </td>
          <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
            {{ formatDate(doc.created_at) }}
          </td>
          <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
            <div class="flex items-center justify-end space-x-2">
              <button
                class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                title="View"
                @click="emit('view', doc)"
              >
                <Eye class="h-5 w-5" />
              </button>
              <button
                class="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-300"
                title="Download"
                @click="emit('download', doc)"
              >
                <CloudDownload class="h-5 w-5" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { CloudDownload, Eye } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import { formatFileSize, formatDate } from '@/utils/formatters'
import { useTableClasses } from '@/composables/useTableClasses'

const t = useTableClasses()

defineProps({
  documents: {
    type: Array,
    default: () => [],
  },
  selectedDocuments: {
    type: Array,
    default: () => [],
  },
  areAllSelected: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle-select-all', 'toggle-selection', 'view', 'download'])

const getModelName = (doc) => {
  const metaData = doc.meta_data || {}
  // Check for specific model fields first
  if (metaData.mistral_model) return metaData.mistral_model
  if (metaData.vision_model) return metaData.vision_model
  // Fallback to generic model field
  if (metaData.model) return metaData.model
  // No model for local OCR
  return '—'
}

/**
 * Returns OCR display string only if OCR was actually used.
 * Checks meta_data.ocr_engine to determine if OCR was applied.
 * Returns null if no OCR was used (e.g., embedded text extraction, plain text files, CSV).
 */
const getOcrDisplay = (doc) => {
  const metaData = doc.meta_data || {}
  const ocrEngine = metaData.ocr_engine
  const extractionMethod = metaData.extraction_method
  const file_type = metaData.file_type

  // If ocr_engine is explicitly set, show the appropriate label
  if (ocrEngine) {
    // Map internal engine names to display names
    const engineLabels = {
      tesseract: 'Tesseract OCR',
      docling_tesseract: 'Tesseract OCR',
      mistral_ocr: 'Mistral OCR',
      llm_vision: 'Vision LLM OCR',
    }

    // Special case: pypdf is not OCR, it's embedded text extraction
    if (ocrEngine === 'pypdf') {
      return null
    }

    const label = engineLabels[ocrEngine]
    if (label) {
      return label
    }
  }

  // No ocr_engine set - check extraction_method as fallback
  if (extractionMethod) {
    // Known non-OCR methods - return null
    const nonOcrMethods = [
      'docling_serve_no_ocr',
      'pypdf_embedded_text',
      'text_file_extraction',
      'csv_full_document',
      'csv_row_by_row',
      'xlsx_full_document',
      'xlsx_row_by_row',
    ]
    if (nonOcrMethods.includes(extractionMethod)) {
      return null
    }

    // OCR methods
    const ocrMethods = [
      'docling_serve_tesseract_ocr',
      'docling_serve_tesseract_force_ocr',
      'docling_serve_tesseract_image_ocr',
      'mistral_ocr',
      'llm_vision_ocr',
    ]
    if (ocrMethods.includes(extractionMethod)) {
      const engineLabels = {
        tesseract: 'Tesseract OCR',
        mistral_ocr: 'Mistral OCR',
        llm_vision: 'Vision LLM OCR',
      }
      // Extract engine from method name
      for (const [engine, label] of Object.entries(engineLabels)) {
        if (extractionMethod.includes(engine)) {
          return label
        }
      }
      return 'OCR Applied'
    }
  }

  // Check file_type - table and text files never need OCR
  if (file_type === 'table' || file_type === 'text') {
    return null
  }

  // Default: show nothing if we can't determine OCR was used
  return null
}
</script>
