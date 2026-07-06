<template>
  <BaseModal
    :open="open"
    size="2xl"
    panel-class="h-[85vh]"
    body-class="!p-0 overflow-hidden"
    @close="$emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between flex-1">
        <div class="flex items-center gap-4">
          <FileIcon :file-type="file?.file_type" :size="32" />
          <div>
            <h3 class="text-xl font-bold text-slate-900 dark:text-white">{{ file?.file_name }}</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">
              {{ formatFileSize(file?.file_size, 'Unknown') }} &middot; {{ file?.file_type }}
            </p>
          </div>
        </div>
        <button
          class="p-2 text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-modal transition"
          title="Download"
          @click="downloadFile"
        >
          <CloudDownload class="h-5 w-5" />
        </button>
      </div>
    </template>

    <!-- Preview Content -->
    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center h-full">
      <LoadingSpinner size="large" />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex items-center justify-center h-full">
      <div class="text-center max-w-sm mx-auto">
        <AlertTriangle class="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600" />
        <p class="mt-3 text-base text-slate-500 dark:text-slate-400">{{ error }}</p>
        <BaseButton variant="ghost" size="sm" class="mt-5" @click="loadPreview">
          Try Again
        </BaseButton>
      </div>
    </div>

    <!-- PDF Preview -->
    <iframe
      v-else-if="previewUrl && file?.file_type === 'application/pdf'"
      :src="previewUrl"
      class="w-full h-full rounded-b-2xl border-none"
      title="PDF preview"
    ></iframe>

    <!-- Image Preview -->
    <div
      v-else-if="previewUrl && file?.file_type?.startsWith('image/')"
      class="flex items-center justify-center h-full p-10 bg-white dark:bg-slate-900 rounded-b-2xl"
    >
      <img
        :src="previewUrl"
        :alt="file?.file_name || ''"
        class="max-w-full max-h-[70vh] object-contain rounded-modal border"
      />
    </div>

    <!-- CSV/XLSX Table Preview -->
    <div v-else-if="tabularData && headerLabels.length" class="h-full overflow-auto p-6">
      <div
        class="bg-white dark:bg-slate-900 rounded-modal shadow border border-slate-100 dark:border-slate-700 overflow-x-auto"
      >
        <table
          class="min-w-full divide-y divide-slate-100 dark:divide-slate-700 rounded-modal text-sm table-auto"
        >
          <thead class="bg-slate-50 dark:bg-slate-800 sticky top-0 z-10">
            <tr>
              <th
                v-for="(header, idx) in normalizedHeaders"
                :key="header || idx"
                class="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider border-b border-slate-100 dark:border-slate-700 whitespace-nowrap sticky top-0 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                :class="cellClasses(header)"
              >
                {{ headerLabel(header) }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50 dark:divide-slate-800">
            <tr
              v-for="(row, ridx) in tabularData.rows"
              :key="ridx"
              class="hover:bg-blue-50 dark:hover:bg-slate-800 transition"
            >
              <td
                v-for="(cell, cidx) in row"
                :key="cidx"
                class="px-4 py-2 border-b border-slate-50 dark:border-slate-800 max-w-[260px] align-top text-slate-700 dark:text-slate-300"
                :class="cellClasses(normalizedHeaders[cidx] ?? null)"
              >
                <span
                  v-if="cell === '' || cell == null"
                  class="text-slate-300 dark:text-slate-600 italic"
                  >empty</span
                >
                <template
                  v-else-if="
                    isTextColumn(normalizedHeaders[cidx] ?? null) && String(cell).length > 80
                  "
                >
                  <span
                    class="truncate cursor-pointer text-green-900 dark:text-green-300"
                    :title="String(cell)"
                    @click="showFullCell(String(cell), headerLabels[cidx] ?? null)"
                    >{{ String(cell).slice(0, 80)
                    }}<span class="font-semibold text-blue-600 dark:text-blue-400 ml-1"
                      >…more</span
                    ></span
                  >
                </template>
                <template v-else>
                  {{ cell }}
                </template>
              </td>
            </tr>
          </tbody>
        </table>
        <div
          v-if="truncated"
          class="px-4 py-2 bg-slate-50 dark:bg-slate-800 text-xs text-slate-500 dark:text-slate-400 rounded-b-2xl text-center"
        >
          Showing first {{ tabularData.rows.length }} of {{ totalRows }} rows
        </div>
      </div>
      <div class="flex flex-wrap gap-2 mt-4">
        <span
          v-if="idColumn"
          class="inline-flex items-center px-3 py-1 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium"
        >
          <span class="mr-1 font-bold">ID column:</span> {{ idColumn }}
        </span>
        <span
          v-if="textColumns && textColumns.length"
          class="inline-flex items-center px-3 py-1 rounded bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs font-medium"
        >
          <span class="mr-1 font-bold">Text columns:</span> {{ textColumns.join(', ') }}
        </span>
      </div>
    </div>

    <!-- Text File Preview -->
    <div
      v-else-if="previewContent && file?.file_type === 'text/plain'"
      class="h-full overflow-auto p-8"
    >
      <pre
        class="text-sm font-mono whitespace-pre-wrap bg-white dark:bg-slate-900 rounded-card shadow p-6 border border-slate-100 dark:border-slate-700"
        >{{ previewContent }}</pre>
    </div>

    <!-- Fallback -->
    <div v-else class="flex items-center justify-center h-full">
      <div class="text-center">
        <FileIcon :file-type="file?.file_type" :size="64" />
        <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Preview not available for this file type.
        </p>
        <BaseButton class="mt-4" @click="downloadFile">
          <CloudDownload class="mr-2 h-4 w-4" />
          Download File
        </BaseButton>
      </div>
    </div>

    <!-- Modal for full text cell -->
    <BaseModal
      :open="showModal"
      size="lg"
      :title="modalHeader"
      body-class="!p-6"
      @close="closeModal"
    >
      <pre
        class="whitespace-pre-wrap text-sm text-slate-900 dark:text-slate-100 bg-slate-50 dark:bg-slate-900 rounded p-4 max-h-[60vh] overflow-auto"
        >{{ modalContent }}</pre>
      <div class="mt-4 flex items-center gap-2">
        <BaseButton variant="link" tone="blue" class="text-xs underline" @click="copyToClipboard">
          Copy
        </BaseButton>
        <span v-if="copied" class="text-green-700 dark:text-green-400 text-xs">Copied!</span>
      </div>
    </BaseModal>

    <template #footer>
      <div class="flex items-center justify-between text-xs w-full">
        <div class="flex items-center gap-6 text-slate-500 dark:text-slate-400">
          <span>Created: {{ formatDateFull(file?.created_at) }}</span>
          <span v-if="file?.file_hash" class="font-mono text-xs">
            Hash: {{ file.file_hash.substring(0, 8) }}...
          </span>
        </div>
        <div v-if="file?.description" class="text-slate-600 dark:text-slate-300 truncate">
          {{ file.description }}
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import { AlertTriangle, CloudDownload } from '@lucide/vue'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import FileIcon from '@/components/common/FileIcon.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { formatFileSize, formatDateFull } from '@/utils/formatters'
import type { File } from '@/types'

interface Props {
  open: boolean
  file: File | null
  projectId: string | number
}

const props = defineProps<Props>()
const toast = useToast()
defineEmits<{
  close: []
}>()

interface TabularData {
  headers: (string | null)[]
  rows: (string | number | boolean | null)[][]
}

const isLoading = ref(true)
const error = ref('')
const previewUrl = ref('')
const previewContent = ref('')

const tabularData = ref<TabularData | null>(null)
const truncated = ref(false)
const totalRows = ref(0)

const idColumn = ref('')
const textColumns = ref<string[]>([])

// ⬇️ ADD: use settings saved by FileImportConfigModal (from file.file_metadata)
const delimiter = ref(',')
const encoding = ref('utf-8')
const hasHeader = ref(true)
const sheetFromMeta = ref('')

// (Re)initialize CSV/XLSX parse settings from the current file's saved metadata.
// Called on each open since the component stays mounted to enable the close transition.
function syncConfigFromMeta(): void {
  const meta = props.file?.file_metadata || {}
  delimiter.value = meta.delimiter || ','
  encoding.value = meta.encoding || 'utf-8'
  hasHeader.value = meta.has_header !== undefined ? !!meta.has_header : true
  sheetFromMeta.value = meta.sheet || ''
}
syncConfigFromMeta()

// Robust format checks (extension + MIME)
const isCSV = computed(() => {
  if (!props.file) return false
  const t = (props.file.file_type || '').toLowerCase()
  const n = (props.file.file_name || '').toLowerCase()
  return (
    t === 'text/csv' ||
    (t === 'application/vnd.ms-excel' && n.endsWith('.csv')) ||
    n.endsWith('.csv')
  )
})
const isXLSX = computed(() => {
  if (!props.file) return false
  const t = (props.file.file_type || '').toLowerCase()
  const n = (props.file.file_name || '').toLowerCase()
  return (
    t === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || n.endsWith('.xlsx')
  )
})

// Modal for showing full text content
const showModal = ref(false)
const modalContent = ref('')
const modalHeader = ref('')
const copied = ref(false)

// Header labels (no null/empty headers)
const headerLabels = computed(() =>
  (tabularData.value?.headers || []).map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return `Column ${idx + 1}`
    }
    return String(h)
  }),
)

function showFullCell(cell: string, header: string | null): void {
  modalContent.value = cell
  modalHeader.value = header ? `${header}` : ''
  showModal.value = true
  copied.value = false
}
function closeModal(): void {
  showModal.value = false
  modalContent.value = ''
  modalHeader.value = ''
  copied.value = false
}
function copyToClipboard(): void {
  navigator.clipboard.writeText(modalContent.value || '').then(() => {
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  })
}

const normalizedHeaders = computed(() => {
  const headers: (string | null)[] = [...(tabularData.value?.headers || [])]
  const rows = tabularData.value?.rows || []
  const maxLen = Math.max(headers.length, ...rows.map((r) => r.length))
  while (headers.length < maxLen) {
    headers.push(`Column ${headers.length + 1}`)
  }
  return headers.map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return `Column ${idx + 1}`
    }
    return String(h)
  })
})

const loadPreview = async (): Promise<void> => {
  if (!props.file) return
  const file = props.file
  isLoading.value = true
  error.value = ''
  previewUrl.value = ''
  previewContent.value = ''
  tabularData.value = null
  truncated.value = false
  totalRows.value = 0

  try {
    if (isCSV.value || isXLSX.value) {
      const params = new URLSearchParams({ max_rows: '50' })

      // ⬇️ NEW: pass saved parse hints (identical to the second modal's behavior)
      params.append('encoding', encoding.value)
      params.append('has_header', String(hasHeader.value))
      if (isCSV.value && delimiter.value) params.append('delimiter', delimiter.value)
      if (isXLSX.value && sheetFromMeta.value) params.append('sheet', sheetFromMeta.value)

      const { data } = await filesApi.getPreviewRows(
        props.projectId,
        file.id,
        params as unknown as Record<string, unknown>,
      )

      tabularData.value = {
        headers: data.headers || [],
        rows: data.rows || [],
      }
      truncated.value = !!data.truncated
      totalRows.value = data.total_rows || 0

      // ID / text columns are sourced from the file import config, not the
      // preview-rows response.
      idColumn.value = file.file_metadata?.case_id_column || ''
      textColumns.value = file.file_metadata?.text_columns || []
    } else if (file.file_type === 'text/plain') {
      const response = await filesApi.getContent(props.projectId, file.id, {
        preview: true,
      })
      previewContent.value = await response.data.text()
    } else if (file.file_type?.startsWith('image/')) {
      const response = await filesApi.getContent(props.projectId, file.id, {
        preview: true,
      })
      previewUrl.value = URL.createObjectURL(response.data)
    } else if (file.file_type === 'application/pdf') {
      const response = await filesApi.getContent(props.projectId, file.id, {
        preview: true,
      })
      previewUrl.value = URL.createObjectURL(response.data)
    } else {
      error.value = 'Preview not available for this file type.'
    }
  } catch (err) {
    error.value = 'Failed to load preview'
    console.error('Preview error:', err)
  } finally {
    isLoading.value = false
  }
}

const downloadFile = async (): Promise<void> => {
  if (!props.file) return
  const file = props.file
  try {
    const response = await filesApi.getContent(props.projectId, file.id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', file.file_name || 'download')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    toast.success('File downloaded successfully')
  } catch (err) {
    toast.error('Failed to download file')
    console.error(err)
  }
}

// Load preview whenever the modal opens (component stays mounted to enable the
// close transition). Immediate so the first open also loads.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      syncConfigFromMeta()
      loadPreview()
    } else if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
    }
  },
  { immediate: true },
)
onUnmounted(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
})

function cellClasses(headerLabel: string | null): string {
  if (headerLabel === idColumn.value && idColumn.value) {
    return 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 font-semibold border-blue-200 dark:border-blue-800 shadow-sm'
  }
  if (headerLabel != null && textColumns.value && textColumns.value.includes(headerLabel)) {
    return 'bg-green-50 dark:bg-green-900/30 text-green-900 dark:text-green-300 font-medium border-green-200 dark:border-green-800'
  }
  return ''
}
function headerLabel(headerLabel: string | null): string {
  if (!headerLabel) return ''
  if (headerLabel === idColumn.value) return `${headerLabel} (ID)`
  if (textColumns.value && textColumns.value.includes(headerLabel)) return `${headerLabel} (Text)`
  return headerLabel
}
function isTextColumn(headerLabel: string | null): boolean {
  return headerLabel != null && !!textColumns.value && textColumns.value.includes(headerLabel)
}
</script>
