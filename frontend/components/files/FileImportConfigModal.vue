<template>
  <BaseModal
    :open="open"
    :title="
      isEdit
        ? $t('files.import.title_edit', { name: file?.file_name || '' })
        : $t('files.import.title_new', { name: file?.file_name || '' })
    "
    size="xl"
    panel-class="sm:max-w-3xl lg:max-w-[90vw] max-h-[95vh]"
    body-class="px-8 py-6"
    @close="tryClose"
  >
    <!-- Content -->
    <!-- Preview -->
    <h3 class="font-semibold text-content text-sm mb-3">{{ $t('files.import.preview_title') }}</h3>

    <!-- Preview load error: surface the backend detail inline with a retry
         (mirrors FilePreviewModal's error handling). -->
    <ErrorBanner
      v-if="previewError"
      :message="previewError"
      :retry-text="$t('files.actions.retry')"
      :retry-loading="previewLoading"
      class="!mb-5"
      @retry="loadPreview"
    />

    <div
      v-else
      class="overflow-x-auto border border-default rounded bg-surface-muted p-2 max-h-72 mb-5"
    >
      <table v-if="headerLabels.length" class="min-w-full text-sm">
        <thead>
          <tr>
            <th
              v-for="(col, idx) in headerLabels"
              :key="col || idx"
              class="px-2 py-1 bg-surface-sunken font-normal text-content text-xs"
            >
              {{ col }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ridx) in preview.rows" :key="ridx">
            <td v-for="(cell, cidx) in row" :key="cidx" class="px-2 py-1 text-content-muted">
              <span v-if="cell === '' || cell == null" class="text-content-subtle italic">{{
                $t('files.preview.empty')
              }}</span>
              <span v-else>{{ cell }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="text-xs text-content-muted py-3 text-center">
        {{ $t('files.import.no_preview') }}
      </div>
    </div>
    <div v-if="!previewError" class="text-xs text-content-subtle mb-4">
      {{ $t('files.import.previewing_rows', { count: preview.rows.length }) }}
    </div>

    <!-- Config form -->
    <div class="space-y-6">
      <div class="flex flex-wrap gap-4">
        <div>
          <label for="import-encoding" :class="labelClass">{{ $t('files.import.encoding') }}</label>
          <select id="import-encoding" v-model="encoding" :class="selectClass">
            <option v-for="enc in detectedEncodings" :key="enc" :value="enc">
              {{ enc }}
            </option>
          </select>
        </div>

        <div v-if="isCSV">
          <label for="import-delimiter" :class="labelClass">{{
            $t('files.import.delimiter')
          }}</label>
          <select id="import-delimiter" v-model="delimiter" :class="selectClass">
            <option v-for="d in detectedDelimiters" :key="d" :value="d">
              {{ displayDelimiter(d) }}
            </option>
          </select>
        </div>

        <div v-if="isCSV || isXLSX">
          <label for="import-has-header" :class="labelClass">{{
            $t('files.import.header_row')
          }}</label>
          <input id="import-has-header" v-model="hasHeader" type="checkbox" />
          <label for="import-has-header" class="text-sm text-content-muted">{{
            $t('files.import.has_header')
          }}</label>
        </div>

        <div v-if="isXLSX && sheets.length">
          <label for="import-sheet" :class="labelClass">{{ $t('files.import.sheet') }}</label>
          <select id="import-sheet" v-model="sheet" :class="selectClass">
            <option v-for="s in sheets" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
      </div>

      <div>
        <label :class="labelClass">{{ $t('files.import.strategy') }}</label>
        <div class="flex items-center gap-4">
          <label class="text-content-muted">
            <input
              v-model="preprocessingStrategy"
              type="radio"
              value="row_by_row"
              data-testid="import-strategy-row-by-row"
            />
            <span class="ml-1 text-sm">{{ $t('files.import.strategy_row') }}</span>
          </label>
          <label class="text-content-muted">
            <input v-model="preprocessingStrategy" type="radio" value="full_document" />
            <span class="ml-1 text-sm">{{ $t('files.import.strategy_full') }}</span>
          </label>
        </div>
      </div>

      <div v-if="preprocessingStrategy === 'row_by_row' && headerLabels.length" class="space-y-3">
        <!-- Text columns (checkbox list with sample values) -->
        <div>
          <div class="flex items-center justify-between">
            <label :class="labelClass"
              >{{ $t('files.import.text_columns') }} <span class="text-red-500">*</span></label
            >
            <BaseButton
              variant="link"
              tone="blue"
              size="sm"
              class="h-auto p-0"
              :disabled="textColumns.length === headerLabels.length"
              @click="textColumns = [...headerLabels]"
            >
              {{ $t('files.import.select_all') }}
            </BaseButton>
          </div>
          <p class="text-xs text-content-muted mb-2">
            {{ $t('files.import.text_columns_help') }}
          </p>
          <div
            class="grid sm:grid-cols-2 gap-1.5 max-h-64 overflow-y-auto p-2 border border-default rounded-card bg-surface-muted"
          >
            <label
              v-for="(col, idx) in headerLabels"
              :key="idx"
              :class="[
                'flex items-start gap-2 p-2 rounded-card border cursor-pointer transition-colors',
                textColumns.includes(col)
                  ? 'border-primary bg-primary-soft'
                  : 'border-default bg-surface hover:bg-surface-sunken',
              ]"
            >
              <input
                :checked="textColumns.includes(col)"
                type="checkbox"
                class="mt-0.5 rounded border-strong text-primary focus:ring-ring"
                :data-testid="`import-text-column-${col}`"
                @change="toggleTextColumn(col)"
              />
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-content truncate">{{ col }}</div>
                <div v-if="sampleValue(idx)" class="text-xs text-content-subtle truncate">
                  {{ $t('files.import.sample_eg', { value: sampleValue(idx) }) }}
                </div>
              </div>
            </label>
          </div>
          <div v-if="textColumns.length > 0" class="flex flex-wrap gap-1 mt-2">
            <StatusBadge v-for="col in textColumns" :key="col" color="blue">
              {{ col }}
            </StatusBadge>
          </div>
          <p v-else class="text-xs text-red-600 dark:text-red-400 mt-2">
            {{ $t('files.import.text_columns_required') }}
          </p>
        </div>

        <!-- ID column -->
        <div>
          <label for="import-case-id" :class="labelClass">{{ $t('files.import.id_column') }}</label>
          <select id="import-case-id" v-model="caseIdColumn" :class="selectClass">
            <option value="">{{ $t('files.import.row_number') }}</option>
            <option v-for="(col, idx) in headerLabels" :key="idx" :value="col">
              {{ col
              }}<span v-if="isRecommendedId(col)"> {{ $t('files.import.recommended') }}</span>
            </option>
          </select>
          <div class="text-xs text-content-subtle mt-1">
            {{ $t('files.import.id_help_before') }} <code>CASE-001</code
            >{{ $t('files.import.id_help_after') }}
          </div>

          <!-- ID uniqueness validation -->
          <div
            v-if="caseIdColumn && validatingId"
            class="mt-2 text-xs text-content-muted flex items-center gap-1.5"
          >
            <LoadingSpinner inline size="small" color="current" label="" />
            {{ $t('files.import.checking_unique') }}
          </div>

          <div
            v-else-if="idColumnMissing"
            class="mt-2 rounded-card border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-300"
          >
            {{ $t('files.import.id_missing_before') }} <strong>{{ caseIdColumn }}</strong>
            {{ $t('files.import.id_missing_after') }}
          </div>

          <div
            v-else-if="idHasDuplicates"
            class="mt-2 rounded-card border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-300"
          >
            <p class="font-medium">
              {{ $t('files.import.not_unique', { rows: idValidation?.duplicate_rows }) }}
            </p>
            <ul class="mt-1.5 space-y-0.5 list-disc pl-4">
              <li v-for="dup in idValidation?.duplicates || []" :key="dup.value">
                <span v-if="dup.is_empty" class="italic">{{ $t('files.import.empty_value') }}</span>
                <code v-else>{{ dup.value }}</code>
                — {{ $t('files.import.appears', { count: dup.count }) }}
              </li>
            </ul>
            <p v-if="extraDuplicateCount > 0" class="mt-1">
              {{ $t('files.import.more_duplicates', { count: extraDuplicateCount }) }}
            </p>
            <p class="mt-1.5">
              {{ $t('files.import.pick_different_before') }}
              <strong>{{ $t('files.import.row_number') }}</strong>
              {{ $t('files.import.pick_different_after') }}
            </p>
          </div>

          <div
            v-else-if="caseIdColumn && idValidation?.is_valid"
            class="mt-2 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                fill-rule="evenodd"
                d="M16.704 5.29a1 1 0 010 1.42l-7.5 7.5a1 1 0 01-1.42 0l-3.5-3.5a1 1 0 111.42-1.42l2.79 2.79 6.79-6.79a1 1 0 011.42 0z"
                clip-rule="evenodd"
              />
            </svg>
            {{ $t('files.import.all_unique', { count: idValidation?.total_rows }) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      :title="$t('files.import.discard_title')"
      :message="$t('files.import.discard_message')"
      :confirm-text="$t('files.import.discard_confirm')"
      :cancel-text="$t('files.import.discard_cancel')"
      confirm-variant="danger"
      @confirm="confirmClose"
      @cancel="showConfirm = false"
    />

    <template #footer>
      <BaseButton variant="secondary" @click="tryClose">{{
        $t('files.actions.cancel')
      }}</BaseButton>
      <BaseButton
        :disabled="
          saving ||
          validatingId ||
          idHasDuplicates ||
          idColumnMissing ||
          (preprocessingStrategy === 'row_by_row' && textColumns.length === 0)
        "
        :loading="saving"
        data-testid="import-save"
        @click="saveConfig"
      >
        {{
          saving
            ? $t('files.import.saving')
            : isEdit
              ? $t('files.import.save_changes')
              : $t('files.import.save')
        }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { filesApi } from '@/services/filesApi'
import type { IdColumnValidation } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { selectClass, labelClass } from '@/utils/formStyles'
import { extractErrorMessage } from '@/utils/errors'
import type { File } from '@/types'

interface Props {
  open: boolean
  file: File | null
  projectId: string | number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: []
}>()

const { t } = useI18n({ useScope: 'global' })
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

interface PreviewData {
  headers: (string | null)[]
  rows: (string | number | boolean | null)[][]
  sheets?: string[]
}

const preview = ref<PreviewData>({ headers: [], rows: [] })
// Inline preview-load error (with retry) instead of a dropped toast.
const previewError = ref('')
const previewLoading = ref(false)
const detectedDelimiters = ref<string[]>([',', ';', '\t'])
const delimiter = ref(',')
const encoding = ref('utf-8')
const detectedEncodings = ref<string[]>(['utf-8', 'latin1'])
const hasHeader = ref(true)
const sheet = ref('')
const sheets = ref<string[]>([])

const preprocessingStrategy = ref('row_by_row')
const textColumns = ref<string[]>([])
const caseIdColumn = ref('')

const saving = ref(false)
const showConfirm = ref(false)
const initialConfig = ref('')

// Case-ID uniqueness validation (checked against the whole file server-side).
const idValidation = ref<IdColumnValidation | null>(null)
const validatingId = ref(false)
let idValidateTimer: ReturnType<typeof setTimeout> | null = null
let idValidateSeq = 0

const idHasDuplicates = computed(
  () =>
    idValidation.value != null && idValidation.value.column_exists && !idValidation.value.is_valid,
)
const idColumnMissing = computed(
  () => idValidation.value != null && !idValidation.value.column_exists,
)
const extraDuplicateCount = computed(() => {
  const v = idValidation.value
  if (!v) return 0
  return Math.max(0, (v.duplicate_value_count ?? v.duplicates.length) - v.duplicates.length)
})

// Derived header labels (no null/empty headers)
const headerLabels = computed(() =>
  (preview.value.headers || []).map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return t('files.preview.column', { n: idx + 1 })
    }
    return String(h)
  }),
)

function displayDelimiter(d: string): string {
  if (d === '\t') return t('files.import.delim_tab')
  if (d === ',') return t('files.import.delim_comma')
  if (d === ';') return t('files.import.delim_semicolon')
  return d
}

// Toggle a column in/out of the selected text-columns set.
function toggleTextColumn(col: string): void {
  const idx = textColumns.value.indexOf(col)
  if (idx > -1) {
    textColumns.value.splice(idx, 1)
  } else {
    textColumns.value.push(col)
  }
}

// Sample value for a column (from the first preview row that has one), shown
// under the column name to help the user recognize which column is which.
function sampleValue(colIndex: number): string {
  const rows = preview.value.rows || []
  for (const row of rows) {
    const cell = row[colIndex]
    if (cell !== '' && cell != null) {
      const s = String(cell)
      // Keep the preview compact.
      return s.length > 60 ? s.slice(0, 60) + '…' : s
    }
  }
  return ''
}

function isRecommendedId(col: string): boolean {
  if (!col) return false
  const idCandidates = ['id', 'case_id', 'patient_id', 'identifier', 'studyid', 'record_id']
  return idCandidates.some((name) => col.trim().toLowerCase().includes(name))
}

function guessIdColumn(headers: (string | null)[]): string {
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
function getConfigSnapshot(): string {
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
function resetInitialConfig(): void {
  initialConfig.value = getConfigSnapshot()
}
function hasUnsavedChanges(): boolean {
  return getConfigSnapshot() !== initialConfig.value
}

const loadPreview = async (): Promise<void> => {
  if (!props.file) return
  previewLoading.value = true
  try {
    const params = new URLSearchParams({ encoding: encoding.value })
    if (isCSV.value && delimiter.value) params.append('delimiter', delimiter.value)
    if (isXLSX.value && sheet.value) params.append('sheet', sheet.value)
    params.append('has_header', String(hasHeader.value))
    params.append('max_rows', '25')

    const { data } = await filesApi.getPreviewRows(
      props.projectId,
      props.file.id,
      params as unknown as Record<string, unknown>,
    )

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

    // Drop any previously selected text columns that no longer exist under the
    // current settings (e.g. after a header/delimiter change), but don't
    // auto-pick one — the user chooses which column(s) hold the report text.
    if (textColumns.value.some((tc) => !labels.includes(tc))) {
      textColumns.value = textColumns.value.filter((tc) => labels.includes(tc))
    }

    // XLSX sheet default
    if (isXLSX.value && !sheet.value && data.sheets && data.sheets.length) {
      const firstSheet = data.sheets[0]
      if (firstSheet) sheet.value = firstSheet
    }

    previewError.value = ''
  } catch (err) {
    previewError.value = extractErrorMessage(err, t('files.preview.load_failed'))
    preview.value = { headers: [], rows: [] }
  } finally {
    previewLoading.value = false
  }
}

// (Re)initialize config from the current file's metadata + load preview whenever
// the modal opens. Component stays mounted to enable the close transition.
async function initFromMeta(): Promise<void> {
  if (!props.file) return
  const file = props.file
  isEdit.value = !!file.preprocessing_strategy
  idValidation.value = null
  validatingId.value = false

  // Reset transient config to defaults before pre-filling from metadata.
  delimiter.value = ','
  encoding.value = 'utf-8'
  hasHeader.value = true
  sheet.value = ''
  textColumns.value = []
  caseIdColumn.value = ''
  preprocessingStrategy.value = 'row_by_row'

  const meta = file.file_metadata || {}
  if (meta.delimiter) delimiter.value = meta.delimiter
  if (meta.has_header !== undefined) hasHeader.value = meta.has_header
  if (meta.encoding) encoding.value = meta.encoding
  if (meta.sheet) sheet.value = meta.sheet
  if (meta.text_columns) textColumns.value = meta.text_columns.map(String).filter(Boolean)
  if (meta.case_id_column !== undefined) caseIdColumn.value = String(meta.case_id_column || '')

  if (file.preprocessing_strategy) preprocessingStrategy.value = file.preprocessing_strategy

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

// Validate the case-ID column's uniqueness across the whole file. Debounced,
// with a sequence guard so stale responses can't overwrite newer results.
async function runIdValidation(): Promise<void> {
  if (!props.file) return
  if (preprocessingStrategy.value !== 'row_by_row' || !caseIdColumn.value) {
    idValidation.value = null
    validatingId.value = false
    return
  }
  const seq = ++idValidateSeq
  validatingId.value = true
  try {
    const { data } = await filesApi.validateIdColumn(props.projectId, props.file.id, {
      case_id_column: String(caseIdColumn.value),
      delimiter: isCSV.value ? delimiter.value : undefined,
      encoding: encoding.value,
      has_header: hasHeader.value,
      sheet: isXLSX.value ? sheet.value : undefined,
    })
    if (seq === idValidateSeq) idValidation.value = data
  } catch {
    // On a transient validation error don't block the user — the configure
    // endpoint re-validates server-side as a safety net.
    if (seq === idValidateSeq) idValidation.value = null
  } finally {
    if (seq === idValidateSeq) validatingId.value = false
  }
}

function scheduleIdValidation(): void {
  if (idValidateTimer) clearTimeout(idValidateTimer)
  // Show the spinner immediately when a column is selected so the Save button
  // is disabled while we wait (prevents saving before the check completes).
  if (preprocessingStrategy.value === 'row_by_row' && caseIdColumn.value) {
    validatingId.value = true
  } else {
    idValidation.value = null
    validatingId.value = false
  }
  idValidateTimer = setTimeout(runIdValidation, 400)
}

watch([caseIdColumn, preprocessingStrategy, sheet, delimiter, encoding, hasHeader], () => {
  scheduleIdValidation()
})

const saveConfig = async (): Promise<void> => {
  if (!props.file) return
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
    toast.success(t('files.import.saved'))
    emit('saved')
    doClose()
  } catch (err: unknown) {
    // Safety net: the configure endpoint re-validates the ID column and rejects
    // duplicates with 422 + the structured result. Surface it inline.
    const resp = (err as { response?: { status?: number; data?: { detail?: IdColumnValidation } } })
      ?.response
    if (resp?.status === 422 && resp.data?.detail?.duplicates) {
      idValidation.value = resp.data.detail
      toast.error(t('files.import.not_unique_toast'))
    } else {
      toast.error(t('files.import.save_failed'))
    }
  } finally {
    saving.value = false
  }
}

function tryClose(): void {
  if (hasUnsavedChanges()) {
    showConfirm.value = true
  } else {
    doClose()
  }
}
function confirmClose(): void {
  showConfirm.value = false
  doClose()
}
function doClose(): void {
  emit('close')
}
</script>
