<template>
  <DataTable
    :columns="columns"
    :items="documents ?? []"
    row-key="id"
    selectable
    :selected-keys="selectedDocuments"
    :all-selected="areAllSelected"
    :total-selected="selectedDocuments?.length ?? 0"
    :select-all-busy="selectAllBusy"
    :sort-by="sortBy"
    :sort-order="sortOrder"
    :pagination="pagination"
    :item-label="$t('documents.filters.item_label')"
    :empty-title="$t('documents.table.empty_title')"
    @toggle-selection="$emit('toggle-selection', $event as number)"
    @toggle-all="$emit('toggle-select-all')"
    @select-all="$emit('select-all-documents')"
    @clear-selection="$emit('clear-selection')"
    @sort="$emit('sort', $event)"
    @page-change="$emit('page-change', $event)"
    @page-size-change="$emit('page-size-change', $event)"
  >
    <template #cell-document="{ row: doc }">
      <div class="flex items-center">
        <FileIcon :file-type="doc.original_file?.file_type" :size="40" />
        <div class="ml-3">
          <p class="text-sm font-medium text-content truncate max-w-xs">
            {{
              doc.document_name ||
              doc.original_file?.file_name ||
              $t('documents.common.document_number', { id: doc.id })
            }}
          </p>
          <p
            v-if="
              doc.document_name &&
              doc.original_file?.file_name &&
              doc.document_name !== doc.original_file?.file_name
            "
            class="text-xs text-content-muted truncate max-w-xs"
          >
            {{ doc.original_file?.file_name }}
          </p>
          <p v-else class="text-xs text-content-muted">
            {{ formatFileSize(doc.original_file?.file_size) }}
          </p>
        </div>
      </div>
    </template>

    <template #cell-configuration="{ row: doc }">
      <div class="text-sm text-content">
        {{ doc.preprocessing_config?.name || $t('documents.table.custom_config') }}
      </div>
      <div v-if="getOcrDisplay(doc as DocumentListItem)" class="text-xs text-content-muted">
        {{ getOcrDisplay(doc as DocumentListItem) }}
      </div>
    </template>

    <template #cell-model="{ row: doc }">
      <div class="text-sm text-content">
        {{ getModelName(doc as DocumentListItem) }}
      </div>
    </template>

    <template #cell-created_at="{ row: doc }">
      <span class="text-sm text-content-muted">
        {{ formatDate(doc.created_at) }}
      </span>
    </template>

    <template #row-actions="{ row: doc }">
      <BaseButton
        variant="icon"
        tone="blue"
        :title="$t('documents.actions.view')"
        :aria-label="$t('documents.actions.view')"
        @click.stop="$emit('view', doc as DocumentListItem)"
      >
        <Eye class="w-5 h-5" aria-hidden="true" />
      </BaseButton>
      <BaseButton
        variant="icon"
        tone="gray"
        :title="$t('documents.actions.download')"
        :aria-label="$t('documents.actions.download')"
        @click.stop="$emit('download', doc as DocumentListItem)"
      >
        <CloudDownload class="w-5 h-5" aria-hidden="true" />
      </BaseButton>
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CloudDownload, Eye } from '@lucide/vue'
import FileIcon from '@/components/common/FileIcon.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import DataTable from '@/components/common/DataTable.vue'
import { formatFileSize, formatDate } from '@/utils/formatters'
import type { DocumentListItem, DocumentMetaData } from '@/types'

interface TablePagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

interface Props {
  documents?: DocumentListItem[]
  selectedDocuments?: number[]
  areAllSelected?: boolean
  pagination?: TablePagination | null
  // Busy state while the cross-page "select all" id fetch runs.
  selectAllBusy?: boolean
  // Server-side sort state (only created_at is orderable server-side).
  sortBy?: string
  sortOrder?: string
}

withDefaults(defineProps<Props>(), {
  documents: () => [],
  selectedDocuments: () => [],
  areAllSelected: false,
  pagination: null,
  selectAllBusy: false,
  sortBy: 'created_at',
  sortOrder: 'desc',
})

const { t } = useI18n({ useScope: 'global' })

defineEmits<{
  'toggle-select-all': []
  'toggle-selection': [id: number]
  'select-all-documents': []
  'clear-selection': []
  sort: [key: string]
  view: [doc: DocumentListItem]
  download: [doc: DocumentListItem]
  'page-change': [page: number]
  'page-size-change': [size: number]
}>()

// Only `created_at` is sortable: the documents list endpoint supports ordering
// solely by creation time (sort=created_asc|created_desc).
const columns = computed(() => [
  { key: 'document', label: t('documents.table.col_document') },
  { key: 'configuration', label: t('documents.table.col_configuration') },
  { key: 'model', label: t('documents.table.col_model') },
  { key: 'created_at', label: t('documents.table.col_created'), sortable: true },
])

const getModelName = (doc: DocumentListItem): string => {
  const metaData = doc.meta_data || ({} as DocumentMetaData)
  // Check for specific model fields first
  if (metaData.mistral_model) return String(metaData.mistral_model)
  if (metaData.vision_model) return String(metaData.vision_model)
  // Fallback to generic model field
  if (metaData.model) return String(metaData.model)
  // No model for local OCR
  return '—'
}

/**
 * Returns OCR display string only if OCR was actually used.
 * Checks meta_data.ocr_engine to determine if OCR was applied.
 * Returns null if no OCR was used (e.g., embedded text extraction, plain text files, CSV).
 */
const getOcrDisplay = (doc: DocumentListItem): string | null => {
  const metaData = doc.meta_data || ({} as DocumentMetaData)
  const ocrEngine = metaData.ocr_engine as string | undefined
  const extractionMethod = metaData.extraction_method
  const file_type = metaData.file_type as string | undefined

  // If ocr_engine is explicitly set, show the appropriate label
  if (ocrEngine) {
    // Map internal engine names to display names
    const engineLabels: Record<string, string> = {
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
      const engineLabels: Record<string, string> = {
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
      return t('documents.table.ocr_applied')
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
