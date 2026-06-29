<template>
  <BaseModal
    :open="open"
    :title="`${isEdit ? 'Edit Import Settings' : 'Configure Import'}: ${file?.file_name || ''}`"
    size="xl"
    panel-class="sm:max-w-3xl lg:max-w-[90vw] max-h-[95vh]"
    body-class="px-8 py-6"
    @close="tryClose"
  >
    <!-- Content -->
    <!-- Preview -->
    <h3 class="font-semibold text-slate-800 dark:text-slate-200 text-sm mb-3">
      Preview (first 10 rows)
    </h3>
    <div
      class="overflow-x-auto border border-slate-200 dark:border-slate-700 rounded bg-slate-50 dark:bg-slate-800/60 p-2 max-h-72 mb-5"
    >
      <table v-if="headerLabels.length" class="min-w-full text-sm">
        <thead>
          <tr>
            <th
              v-for="(col, idx) in headerLabels"
              :key="col || idx"
              class="px-2 py-1 bg-slate-200 dark:bg-slate-700 font-normal text-slate-700 dark:text-slate-200 text-xs"
            >
              {{ col }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ridx) in preview.rows" :key="ridx">
            <td
              v-for="(cell, cidx) in row"
              :key="cidx"
              class="px-2 py-1 text-slate-700 dark:text-slate-300"
            >
              <span
                v-if="cell === '' || cell == null"
                class="text-slate-300 dark:text-slate-600 italic"
                >empty</span
              >
              <span v-else>{{ cell }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
        No preview data available.
      </div>
    </div>
    <div class="text-xs text-slate-400 dark:text-slate-500 mb-4">
      Previewing first {{ preview.rows.length }} rows
    </div>

    <!-- Config form -->
    <div class="space-y-6">
      <div class="flex flex-wrap gap-4">
        <div>
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Encoding</label
          >
          <select
            v-model="encoding"
            class="w-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded px-2 py-1"
          >
            <option v-for="enc in detectedEncodings" :key="enc" :value="enc">
              {{ enc }}
            </option>
          </select>
        </div>

        <div v-if="isCSV">
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Delimiter</label
          >
          <select
            v-model="delimiter"
            class="w-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded px-2 py-1"
          >
            <option v-for="d in detectedDelimiters" :key="d" :value="d">
              {{ displayDelimiter(d) }}
            </option>
          </select>
        </div>

        <div v-if="isCSV || isXLSX">
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Header Row</label
          >
          <input v-model="hasHeader" type="checkbox" />
          <span class="text-sm text-slate-700 dark:text-slate-300">File contains header row</span>
        </div>

        <div v-if="isXLSX && sheets.length">
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Sheet</label
          >
          <select
            v-model="sheet"
            class="w-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded px-2 py-1"
          >
            <option v-for="s in sheets" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
          >Import Strategy</label
        >
        <div class="flex items-center gap-4">
          <label class="text-slate-700 dark:text-slate-300">
            <input v-model="preprocessingStrategy" type="radio" value="row_by_row" />
            <span class="ml-1 text-sm">One document per row</span>
          </label>
          <label class="text-slate-700 dark:text-slate-300">
            <input v-model="preprocessingStrategy" type="radio" value="full_document" />
            <span class="ml-1 text-sm">Treat whole file as one document</span>
          </label>
        </div>
      </div>

      <div v-if="preprocessingStrategy === 'row_by_row' && headerLabels.length" class="space-y-3">
        <!-- Text columns -->
        <div>
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Text Columns <span class="text-red-500">*</span></label
          >
          <select
            v-model="textColumns"
            multiple
            class="w-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent py-2"
          >
            <option v-for="(col, idx) in headerLabels" :key="idx" :value="col">
              {{ col }}
            </option>
          </select>
          <div class="flex flex-wrap gap-1 mt-2">
            <StatusBadge v-for="col in textColumns" :key="col" color="blue">
              {{ col }}
            </StatusBadge>
          </div>
        </div>

        <!-- ID column -->
        <div>
          <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1"
            >Case/Document ID Column</label
          >
          <select
            v-model="caseIdColumn"
            class="w-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded py-2"
          >
            <option value="">(Row number)</option>
            <option v-for="(col, idx) in headerLabels" :key="idx" :value="col">
              {{ col }}<span v-if="isRecommendedId(col)"> (Recommended)</span>
            </option>
          </select>
          <div class="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Optional: Used for document naming
          </div>
        </div>
      </div>
    </div>

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      title="Discard unsaved changes?"
      message="Your changes to import configuration will be lost."
      confirm-text="Discard"
      cancel-text="Keep editing"
      confirm-variant="danger"
      @confirm="confirmClose"
      @cancel="showConfirm = false"
    />

    <template #footer>
      <BaseButton variant="secondary" @click="tryClose">Cancel</BaseButton>
      <BaseButton
        :disabled="saving || (preprocessingStrategy === 'row_by_row' && textColumns.length === 0)"
        :loading="saving"
        @click="saveConfig"
      >
        {{ saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Save' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { filesApi } from '@/services/filesApi'
import { useToast } from 'vue-toastification'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const props = defineProps({
  open: { type: Boolean, required: true },
  file: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
})
const emit = defineEmits(['close', 'saved'])

const toast = useToast()

const isEdit = ref(false)

// Robust format checks (extension + MIME). Null-safe: the component stays
// mounted (to enable the close transition), so `file` may be null while closed.
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

const preview = ref({ headers: [], rows: [] })
const detectedDelimiters = ref([',', ';', '\t'])
const delimiter = ref(',')
const encoding = ref('utf-8')
const detectedEncodings = ref(['utf-8', 'latin1'])
const hasHeader = ref(true)
const sheet = ref('')
const sheets = ref([])

const preprocessingStrategy = ref('row_by_row')
const textColumns = ref([])
const caseIdColumn = ref('')

const saving = ref(false)
const showConfirm = ref(false)
const initialConfig = ref({})

// Derived header labels (no null/empty headers)
const headerLabels = computed(() =>
  (preview.value.headers || []).map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return `Column ${idx + 1}`
    }
    return String(h)
  }),
)

function displayDelimiter(d) {
  if (d === '\t') return 'Tab'
  if (d === ',') return 'Comma (,)'
  if (d === ';') return 'Semicolon (;)'
  return d
}

function isRecommendedId(col) {
  if (!col) return false
  const idCandidates = ['id', 'case_id', 'patient_id', 'identifier', 'studyid', 'record_id']
  return idCandidates.some((name) => col.trim().toLowerCase().includes(name))
}

function guessIdColumn(headers) {
  if (!headers) return ''
  const idCandidates = ['id', 'case_id', 'patient_id', 'identifier', 'studyid', 'record_id']
  for (const candidate of idCandidates) {
    const match = headers.find(
      (h) => h && typeof h === 'string' && h.trim().toLowerCase() === candidate,
    )
    if (match) return match
  }
  for (const candidate of idCandidates) {
    const match = headers.find(
      (h) => h && typeof h === 'string' && h.toLowerCase().includes(candidate),
    )
    if (match) return match
  }
  return ''
}

// Unsaved change detection
function getConfigSnapshot() {
  return JSON.stringify({
    delimiter: delimiter.value,
    encoding: encoding.value,
    hasHeader: hasHeader.value,
    sheet: sheet.value,
    preprocessingStrategy: preprocessingStrategy.value,
    textColumns: [...textColumns.value],
    caseIdColumn: caseIdColumn.value,
  })
}
function resetInitialConfig() {
  initialConfig.value = getConfigSnapshot()
}
function hasUnsavedChanges() {
  return getConfigSnapshot() !== initialConfig.value
}

const loadPreview = async () => {
  try {
    let params = new URLSearchParams({ encoding: encoding.value })
    if (isCSV.value && delimiter.value) params.append('delimiter', delimiter.value)
    if (isXLSX.value && sheet.value) params.append('sheet', sheet.value)
    params.append('has_header', hasHeader.value)
    params.append('max_rows', 10)

    const { data } = await filesApi.getPreviewRows(props.projectId, props.file.id, params)

    preview.value = data
    if (data.sheets) sheets.value = data.sheets

    const labels = headerLabels.value

    // Case ID
    let guessed = guessIdColumn(data.headers || [])
    if (!guessed || !labels.includes(guessed)) {
      guessed = guessIdColumn(labels) || ''
    }
    if (!caseIdColumn.value || !labels.includes(caseIdColumn.value)) {
      caseIdColumn.value = guessed || ''
    }

    // Text columns default
    if (
      (!textColumns.value.length || textColumns.value.some((tc) => !labels.includes(tc))) &&
      labels.length
    ) {
      textColumns.value = [labels[0]]
    }

    // XLSX sheet default
    if (isXLSX.value && !sheet.value && data.sheets && data.sheets.length)
      sheet.value = data.sheets[0]
  } catch (err) {
    toast.error('Failed to load preview')
    preview.value = { headers: [], rows: [] }
  }
}

// (Re)initialize config from the current file's metadata + load preview whenever
// the modal opens. Component stays mounted to enable the close transition.
async function initFromMeta() {
  isEdit.value = !!props.file.preprocessing_strategy

  // Reset transient config to defaults before pre-filling from metadata.
  delimiter.value = ','
  encoding.value = 'utf-8'
  hasHeader.value = true
  sheet.value = ''
  textColumns.value = []
  caseIdColumn.value = ''
  preprocessingStrategy.value = 'row_by_row'

  const meta = props.file.file_metadata || {}
  if (meta.delimiter) delimiter.value = meta.delimiter
  if (meta.has_header !== undefined) hasHeader.value = meta.has_header
  if (meta.encoding) encoding.value = meta.encoding
  if (meta.sheet) sheet.value = meta.sheet
  if (meta.text_columns) textColumns.value = meta.text_columns.map(String).filter(Boolean)
  if (meta.case_id_column !== undefined) caseIdColumn.value = String(meta.case_id_column || '')

  if (props.file.preprocessing_strategy)
    preprocessingStrategy.value = props.file.preprocessing_strategy

  await loadPreview()

  resetInitialConfig()
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      showConfirm.value = false
      await initFromMeta()
    } else {
      showConfirm.value = false
    }
  },
  { immediate: true },
)

// Re-load preview when these change
watch([delimiter, encoding, sheet, hasHeader], async () => {
  await loadPreview()
})

const saveConfig = async () => {
  saving.value = true
  try {
    const cleanTextCols =
      preprocessingStrategy.value === 'row_by_row'
        ? (textColumns.value || []).map(String).filter(Boolean)
        : []

    const payload = {
      preprocessing_strategy: preprocessingStrategy.value,
      file_metadata: {
        delimiter: isCSV.value ? delimiter.value : undefined,
        encoding: encoding.value,
        has_header: hasHeader.value,
        sheet: isXLSX.value ? sheet.value : undefined,
        text_columns: cleanTextCols,
        case_id_column:
          preprocessingStrategy.value === 'row_by_row' && caseIdColumn.value
            ? String(caseIdColumn.value)
            : undefined,
      },
    }

    await filesApi.configure(props.projectId, props.file.id, payload)
    toast.success('Import configuration saved!')
    emit('saved')
    doClose()
  } catch (err) {
    toast.error('Failed to save import configuration')
  } finally {
    saving.value = false
  }
}

function tryClose() {
  if (hasUnsavedChanges()) {
    showConfirm.value = true
  } else {
    doClose()
  }
}
function confirmClose() {
  showConfirm.value = false
  doClose()
}
function doClose() {
  emit('close')
}
</script>
