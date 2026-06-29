<template>
  <DataTable
    :columns="columns"
    :items="documents"
    row-key="id"
    selectable
    :selected-keys="selectedDocuments"
    :all-selected="areAllSelected"
    :pagination="pagination"
    :show-page-size-selector="false"
    item-label="documents"
    empty-title="No documents found"
    @toggle-selection="$emit('toggle-selection', $event)"
    @toggle-all="$emit('toggle-select-all')"
    @page-change="$emit('page-change', $event)"
    @page-size-change="$emit('page-size-change', $event)"
  >
    <template #cell-document="{ row: doc }">
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
    </template>

    <template #cell-configuration="{ row: doc }">
      <div class="text-sm text-slate-900 dark:text-white">
        {{ doc.preprocessing_config?.name || 'Custom Config' }}
      </div>
      <div v-if="getOcrDisplay(doc)" class="text-xs text-slate-500 dark:text-slate-400">
        {{ getOcrDisplay(doc) }}
      </div>
    </template>

    <template #cell-model="{ row: doc }">
      <div class="text-sm text-slate-900 dark:text-white">
        {{ getModelName(doc) }}
      </div>
    </template>

    <template #cell-created_at="{ row: doc }">
      <span class="text-sm text-slate-500 dark:text-slate-400">
        {{ formatDate(doc.created_at) }}
      </span>
    </template>

    <template #row-actions="{ row: doc }">
      <BaseButton
        variant="icon"
        tone="blue"
        title="View"
        aria-label="View"
        @click.stop="$emit('view', doc)"
      >
        <Eye class="w-5 h-5" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="gray"
        title="Download"
        aria-label="Download"
        @click.stop="$emit('download', doc)"
      >
        <CloudDownload class="w-5 h-5" aria-hidden="true" />
      </BaseButton>
    </template>
  </DataTable>
</template>

<script setup>
import { CloudDownload, Eye } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import DataTable from '@/components/common/DataTable.vue'
import { formatFileSize, formatDate } from '@/utils/formatters'

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
  pagination: {
    type: Object,
    default: null,
  },
})

defineEmits([
  'toggle-select-all',
  'toggle-selection',
  'view',
  'download',
  'page-change',
  'page-size-change',
])

const columns = [
  { key: 'document', label: 'Document' },
  { key: 'configuration', label: 'Configuration' },
  { key: 'model', label: 'Model' },
  { key: 'created_at', label: 'Created' },
]

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
