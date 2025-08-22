<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="tryClose"
      style="backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); background: rgba(25,30,40,0.30);"
    >
      <div
        class="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl sm:max-w-3xl md:max-w-4xl lg:max-w-[90vw] flex flex-col max-h-[95vh] border border-gray-200"
        tabindex="0"
        ref="modalRef"
        @keydown.esc="tryClose"
      >
        <!-- Header -->
        <div class="px-8 py-6 bg-gray-50 border-b rounded-t-2xl flex items-center justify-between">
          <h2 class="text-xl font-bold text-gray-900 tracking-tight">
            {{ isEdit ? 'Edit Import Settings' : 'Configure Import' }}: {{ file.file_name }}
          </h2>
          <button
            @click="tryClose"
            class="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto px-8 py-6">
          <!-- Preview -->
          <h3 class="font-semibold text-gray-800 text-sm mb-3">Preview (first 10 rows)</h3>
          <div class="overflow-x-auto border rounded bg-gray-50 p-2 max-h-72 mb-5">
            <table v-if="headerLabels.length" class="min-w-full text-sm">
              <thead>
                <tr>
                  <th v-for="(col, idx) in headerLabels" :key="col || idx" class="px-2 py-1 bg-gray-200 font-normal text-gray-700 text-xs">
                    {{ col }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ridx) in preview.rows" :key="ridx">
                  <td v-for="(cell, cidx) in row" :key="cidx" class="px-2 py-1">
                    <span v-if="cell === '' || cell == null" class="text-gray-300 italic">empty</span>
                    <span v-else>{{ cell }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="text-xs text-gray-500 py-3 text-center">
              No preview data available.
            </div>
          </div>
          <div class="text-xs text-gray-400 mb-4">Previewing first {{ preview.rows.length }} rows</div>

          <!-- Config form -->
          <div class="space-y-6">
            <div class="flex flex-wrap gap-4">
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Encoding</label>
                <select v-model="encoding" class="w-full border rounded px-2 py-1">
                  <option v-for="enc in detectedEncodings" :key="enc" :value="enc">{{ enc }}</option>
                </select>
              </div>

              <div v-if="isCSV">
                <label class="block text-xs font-medium text-gray-600 mb-1">Delimiter</label>
                <select v-model="delimiter" class="w-full border rounded px-2 py-1">
                  <option v-for="d in detectedDelimiters" :key="d" :value="d">{{ displayDelimiter(d) }}</option>
                </select>
              </div>

              <div v-if="isCSV || isXLSX">
                <label class="block text-xs font-medium text-gray-600 mb-1">Header Row</label>
                <input type="checkbox" v-model="hasHeader" /> <span class="text-sm">File contains header row</span>
              </div>

              <div v-if="isXLSX && sheets.length">
                <label class="block text-xs font-medium text-gray-600 mb-1">Sheet</label>
                <select v-model="sheet" class="w-full border rounded px-2 py-1">
                  <option v-for="s in sheets" :key="s" :value="s">{{ s }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-600 mb-1">Import Strategy</label>
              <div class="flex items-center gap-4">
                <label>
                  <input type="radio" value="row_by_row" v-model="preprocessingStrategy" />
                  <span class="ml-1 text-sm">One document per row</span>
                </label>
                <label>
                  <input type="radio" value="full_document" v-model="preprocessingStrategy" />
                  <span class="ml-1 text-sm">Treat whole file as one document</span>
                </label>
              </div>
            </div>

            <div v-if="preprocessingStrategy === 'row_by_row' && headerLabels.length" class="space-y-3">
              <!-- Text columns -->
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Text Columns <span class="text-red-500">*</span></label>
                <select v-model="textColumns" multiple class="w-full border rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent py-2">
                  <option
                    v-for="(col, idx) in headerLabels"
                    :key="idx"
                    :value="col"
                  >
                    {{ col }}
                  </option>
                </select>
                <div class="flex flex-wrap gap-1 mt-2">
                  <span
                    v-for="col in textColumns"
                    :key="col"
                    class="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs"
                  >
                    {{ col }}
                  </span>
                </div>
              </div>

              <!-- ID column -->
              <div>
                <label class="block text-xs font-medium text-gray-600 mb-1">Case/Document ID Column</label>
                <select v-model="caseIdColumn" class="w-full border rounded py-2">
                  <option value="">(Row number)</option>
                  <option
                    v-for="(col, idx) in headerLabels"
                    :key="idx"
                    :value="col"
                  >
                    {{ col }}<span v-if="isRecommendedId(col)"> (Recommended)</span>
                  </option>
                </select>
                <div class="text-xs text-gray-400 mt-1">Optional: Used for document naming</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-8 py-6 border-t flex justify-end gap-3 bg-gray-50 rounded-b-2xl">
          <button @click="tryClose" class="px-4 py-2 rounded text-gray-600 bg-white border border-gray-200 hover:bg-gray-100">
            Cancel
          </button>
          <button
            :disabled="saving || (preprocessingStrategy==='row_by_row' && textColumns.length === 0)"
            @click="saveConfig"
            class="px-6 py-2 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700 transition disabled:opacity-50"
          >
            {{ saving ? "Saving..." : (isEdit ? "Save Changes" : "Save") }}
          </button>
        </div>

        <!-- Confirm unsaved changes -->
        <div
          v-if="showConfirm"
          class="fixed inset-0 flex items-center justify-center bg-black/20 z-60"
        >
          <div class="bg-white rounded-lg shadow-lg p-6 w-full max-w-md border text-center">
            <div class="mb-3 text-gray-900 font-semibold text-lg">Discard unsaved changes?</div>
            <div class="text-gray-600 mb-6">Your changes to import configuration will be lost.</div>
            <div class="flex justify-center gap-4">
              <button @click="confirmClose" class="px-4 py-2 rounded bg-gray-100 hover:bg-gray-200 text-gray-700">Discard</button>
              <button @click="showConfirm = false" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">Keep editing</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, computed, onUnmounted } from 'vue'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'

const props = defineProps({
  file: { type: Object, required: true },
  projectId: { type: [String, Number], required: true },
});
const emit = defineEmits(['close', 'saved']);

const toast = useToast();

const isEdit = ref(!!props.file.preprocessing_strategy);

// Robust format checks (extension + MIME)
const isCSV = computed(() => {
  const t = (props.file.file_type || '').toLowerCase();
  const n = (props.file.file_name || '').toLowerCase();
  return t === 'text/csv' || (t === 'application/vnd.ms-excel' && n.endsWith('.csv')) || n.endsWith('.csv');
});
const isXLSX = computed(() => {
  const t = (props.file.file_type || '').toLowerCase();
  const n = (props.file.file_name || '').toLowerCase();
  return t === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || n.endsWith('.xlsx');
});

const preview = ref({ headers: [], rows: [] });
const detectedDelimiters = ref([',', ';', '\t']);
const delimiter = ref(',');
const encoding = ref('utf-8');
const detectedEncodings = ref(['utf-8', 'latin1']);
const hasHeader = ref(true);
const sheet = ref('');
const sheets = ref([]);

const preprocessingStrategy = ref('row_by_row');
const textColumns = ref([]);
const caseIdColumn = ref('');

const saving = ref(false);
const modalRef = ref(null);
const showConfirm = ref(false);
const initialConfig = ref({});

// Derived header labels (no null/empty headers)
const headerLabels = computed(() =>
  (preview.value.headers || []).map((h, idx) => {
    if (h == null || (typeof h === 'string' && h.trim() === '')) {
      return `Column ${idx + 1}`;
    }
    return String(h);
  })
);

function displayDelimiter(d) {
  if (d === '\t') return 'Tab';
  if (d === ',') return 'Comma (,)';
  if (d === ';') return 'Semicolon (;)';
  return d;
}

function isRecommendedId(col) {
  if (!col) return false;
  const idCandidates = ['id', 'case_id', 'patient_id', 'identifier', 'studyid', 'record_id'];
  return idCandidates.some(name => col.trim().toLowerCase().includes(name));
}

function guessIdColumn(headers) {
  if (!headers) return '';
  const idCandidates = ['id', 'case_id', 'patient_id', 'identifier', 'studyid', 'record_id'];
  for (const candidate of idCandidates) {
    const match = headers.find(
      h => h && typeof h === 'string' && h.trim().toLowerCase() === candidate
    );
    if (match) return match;
  }
  for (const candidate of idCandidates) {
    const match = headers.find(
      h => h && typeof h === 'string' && h.toLowerCase().includes(candidate)
    );
    if (match) return match;
  }
  return '';
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
  });
}
function resetInitialConfig() {
  initialConfig.value = getConfigSnapshot();
}
function hasUnsavedChanges() {
  return getConfigSnapshot() !== initialConfig.value;
}

const loadPreview = async () => {
  try {
    let params = new URLSearchParams({ encoding: encoding.value });
    if (isCSV.value && delimiter.value) params.append('delimiter', delimiter.value);
    if (isXLSX.value && sheet.value) params.append('sheet', sheet.value);
    params.append('has_header', hasHeader.value);
    params.append('max_rows', 10);

    const { data } = await api.get(
      `/project/${props.projectId}/file/${props.file.id}/preview-rows?${params}`
    );

    preview.value = data;
    if (data.sheets) sheets.value = data.sheets;

    const labels = headerLabels.value;

    // Case ID
    let guessed = guessIdColumn(data.headers || []);
    if (!guessed || !labels.includes(guessed)) {
      guessed = guessIdColumn(labels) || '';
    }
    if (!caseIdColumn.value || !labels.includes(caseIdColumn.value)) {
      caseIdColumn.value = guessed || '';
    }

    // Text columns default
    if ((!textColumns.value.length || textColumns.value.some(tc => !labels.includes(tc))) && labels.length) {
      textColumns.value = [labels[0]];
    }

    // XLSX sheet default
    if (isXLSX.value && !sheet.value && data.sheets && data.sheets.length) sheet.value = data.sheets[0];

  } catch (err) {
    toast.error('Failed to load preview');
    preview.value = { headers: [], rows: [] };
  }
};

onMounted(async () => {
  // Pre-fill from metadata if available
  const meta = props.file.file_metadata || {};
  if (meta.delimiter) delimiter.value = meta.delimiter;
  if (meta.has_header !== undefined) hasHeader.value = meta.has_header;
  if (meta.encoding) encoding.value = meta.encoding;
  if (meta.sheet) sheet.value = meta.sheet;
  if (meta.text_columns) textColumns.value = meta.text_columns.map(String).filter(Boolean);
  if (meta.case_id_column !== undefined) caseIdColumn.value = String(meta.case_id_column || '');

  if (props.file.preprocessing_strategy) preprocessingStrategy.value = props.file.preprocessing_strategy;

  await loadPreview();

  nextTick(() => {
    if (modalRef.value) modalRef.value.focus();
    document.body.style.overflow = 'hidden';
  });
  resetInitialConfig();
});

// Re-load preview when these change
watch([delimiter, encoding, sheet, hasHeader], async () => {
  await loadPreview();
});

onUnmounted(() => {
  document.body.style.overflow = '';
});

const saveConfig = async () => {
  saving.value = true;
  try {
    const cleanTextCols = (preprocessingStrategy.value === 'row_by_row')
      ? (textColumns.value || []).map(String).filter(Boolean)
      : [];

    const payload = {
      preprocessing_strategy: preprocessingStrategy.value,
      file_metadata: {
        delimiter: isCSV.value ? delimiter.value : undefined,
        encoding: encoding.value,
        has_header: hasHeader.value,
        sheet: isXLSX.value ? sheet.value : undefined,
        text_columns: cleanTextCols,
        case_id_column: (preprocessingStrategy.value === 'row_by_row' && caseIdColumn.value) ? String(caseIdColumn.value) : undefined
      }
    };

    await api.post(
      `/project/${props.projectId}/file/${props.file.id}/configure`,
      payload
    );
    toast.success('Import configuration saved!');
    emit('saved');
    doClose();
  } catch (err) {
    toast.error('Failed to save import configuration');
  } finally {
    saving.value = false;
  }
};

function tryClose() {
  if (hasUnsavedChanges()) {
    showConfirm.value = true;
  } else {
    doClose();
  }
}
function confirmClose() {
  showConfirm.value = false;
  doClose();
}
function doClose() {
  document.body.style.overflow = '';
  emit('close');
}
</script>
