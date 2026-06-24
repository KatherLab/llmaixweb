<template>
  <BaseModal
    :open="true"
    size="full"
    panel-class="bg-white/90 max-w-none min-h-[420px]"
    header-class="bg-gradient-to-r from-white/80 to-blue-50/70 sticky top-0 z-10 rounded-t-2xl"
    body-class="flex flex-col"
    footer-class="bg-white/90 flex-col md:flex-row md:items-center justify-between! sticky bottom-0 z-10 rounded-b-2xl shadow text-[15px]"
    @close="close"
  >
    <template #header>
      <div>
        <h2 class="text-xl font-bold tracking-tight mb-0.5">Configure Ground Truth Mapping</h2>
        <div class="flex items-center gap-2 text-[11px] text-gray-500">
          <span class="font-mono text-blue-700">Project {{ projectId }}</span>
          <span
            v-if="selectedSchemaId"
            class="inline-block px-2 py-0.5 rounded bg-blue-100 text-blue-800"
            >{{ schemaDisplayName }}</span
          >
        </div>
      </div>
    </template>

    <!-- TOP CONTROLS -->
    <section
      class="flex flex-wrap md:flex-nowrap items-center gap-3 px-6 py-3 border-b bg-white/90 backdrop-blur rounded-t-none z-10 text-[15px]"
    >
      <div>
        <label class="text-[15px] font-medium mr-2">Schema</label>
        <select
          v-model="selectedSchemaId"
          class="px-2 py-1.5 rounded-lg border border-blue-200 bg-white/70 text-[15px] shadow focus:ring-2 focus:ring-blue-400 transition"
          @change="onSchemaChange"
        >
          <option value="" disabled>Select schema...</option>
          <option v-for="s in schemas" :key="s.id" :value="s.id">
            {{ s.schema_name }} ({{ s.id }})
          </option>
        </select>
      </div>
      <div v-if="schemaFieldPaths.length" class="text-xs text-gray-400">
        <span class="font-mono text-blue-600">{{ schemaFieldPaths.length }}</span> fields
      </div>
      <div class="flex-1"></div>
      <ValidationBanner :status="validationStatus" class="mr-3" />
      <div>
        <IdFieldSelector
          v-if="showIdSelector"
          :is-json="isJsonFormat"
          :is-tabular="isTabularFormat"
          :id-column="idColumn"
          :json-id-field="jsonIdField"
          :available-columns="displayedColumns"
          :id-candidates="idCandidates"
          :current-id-column="currentIdColumn"
          class="ml-2"
          @update:id-column="updateIdColumn"
          @update:json-id-field="updateJsonIdField"
        />
      </div>
    </section>

    <!-- MAIN CONTENT: EVEN 3 COLUMNS, SCROLLS IF NEEDED -->
    <div
      class="flex-1 flex flex-col md:flex-row min-h-0 bg-gradient-to-br from-white/95 to-blue-50/80 overflow-y-auto"
    >
      <!-- LEFT: SCHEMA FIELDS -->
      <section class="w-full md:w-1/3 flex flex-col border-r bg-white/80 p-4 min-w-0">
        <div class="mb-2 text-base font-semibold text-blue-800 flex items-center gap-2">
          <span>Schema Fields</span>
          <span
            v-if="requiredFields.length"
            class="ml-2 px-2 py-0.5 rounded-full text-pink-700 bg-pink-50 text-xs"
            >required: {{ requiredFields.length }}</span
          >
        </div>
        <div class="flex-1 overflow-auto custom-scrollbar pr-1.5 min-w-0 text-[13px]">
          <FieldTree
            :fields="schemaFieldTree"
            :types="schemaFieldTypes"
            :required="requiredFields"
            :selected="selectedSchemaField"
            :disabled="!selectedSchemaId"
            node-color="text-blue-700"
            :mapped="mappedSchemaPaths"
            :highlight="highlightRequiredUnmapped"
            @select="onSchemaFieldSelect"
          />
        </div>
      </section>

      <!-- CENTER: MAPPING PANEL -->
      <section
        class="w-full md:w-1/3 flex flex-col border-r bg-gradient-to-b from-blue-50/80 to-blue-100/80 px-3 pt-6 pb-2 min-w-0"
      >
        <div class="flex flex-col gap-3 mb-3">
          <BaseButton
            :disabled="!canAddMapping"
            class="w-full py-1.5 font-semibold text-[15px] active:scale-95"
            @click="addMapping"
          >
            <span class="flex items-center justify-center gap-2">
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M10 14L21 3M21 3v7.5M21 3h-7.5"
                />
              </svg>
              Map
            </span>
          </BaseButton>
          <BaseButton
            variant="secondary"
            :disabled="!selectedSchemaId"
            class="w-full py-1.5 text-xs font-bold"
            @click="autoMap"
          >
            <span class="flex items-center justify-center gap-2">
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 3v3m0 12v3m9-9h-3M6 12H3m15.364-6.364l-2.121 2.121M7.757 16.243l-2.121 2.121M16.243 16.243l2.121 2.121M7.757 7.757L5.636 5.636"
                />
              </svg>
              Auto-map all fields
            </span>
          </BaseButton>
        </div>
        <div class="flex-1 overflow-auto px-0.5 min-w-0 text-[13px]">
          <MappingList
            :mappings="mappings"
            :schema-field-types="schemaFieldTypes"
            :ground-truth-field-types="groundTruthFieldTypes"
            :schema-selected="!!selectedSchemaId"
            @remove="removeMapping"
          />
        </div>
        <BaseButton
          v-if="mappings.length"
          variant="ghost"
          size="sm"
          class="mt-2 text-xs text-red-600 font-semibold hover:underline hover:text-red-700"
          @click="clearMappings"
        >
          Clear all mappings
        </BaseButton>
      </section>

      <!-- RIGHT: GT FIELDS + SAMPLE (SAMPLE ALWAYS AT BOTTOM) -->
      <section class="w-full md:w-1/3 flex flex-col bg-white/90 p-4 min-w-0">
        <div class="mb-2 text-base font-semibold text-purple-900 flex items-center gap-2">
          Ground Truth Fields
          <span v-if="groundTruthFieldPaths.length" class="ml-2 text-gray-400 text-xs"
            >{{ groundTruthFieldPaths.length }} fields</span
          >
        </div>
        <div class="flex-1 overflow-auto custom-scrollbar pr-1.5 min-w-0 text-[13px]">
          <FieldTree
            :fields="groundTruthFieldTree"
            :types="groundTruthFieldTypes"
            :selected="selectedGroundTruthField"
            :disabled="!selectedSchemaId"
            node-color="text-purple-700"
            :mapped="mappedGtPaths"
            @select="onGroundTruthFieldSelect"
          />
        </div>
        <div class="mt-2">
          <GroundTruthSample
            v-if="sampleDoc"
            :doc="sampleDoc"
            :format="groundTruth.format"
            class="w-full"
          />
        </div>
      </section>
    </div>

    <!-- Loading Overlay -->
    <div
      v-if="loading"
      class="absolute inset-0 bg-white/80 flex flex-col items-center justify-center z-20 rounded-2xl"
    >
      <LoadingSpinner size="large" />
      <div class="mt-3 text-blue-600 font-bold text-lg">Loading...</div>
    </div>

    <template #footer>
      <div>
        <span v-if="!selectedSchemaId" class="text-gray-500">
          Please select a schema to start mapping fields.
        </span>
        <span
          v-else-if="mappings.length && !mappingComplete"
          class="text-yellow-700 font-medium flex items-center gap-2"
        >
          <svg
            class="w-5 h-5 text-yellow-500"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <circle cx="12" cy="16" r="1" />
          </svg>
          Warning: not all required fields are mapped!
        </span>
        <span
          v-if="isTabularFormat && !idColumn"
          class="block mt-1 text-xs text-red-600 font-semibold flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" />
            <line x1="12" y1="8" x2="12" y2="12" stroke="currentColor" stroke-width="2" />
            <circle cx="12" cy="16" r="1" fill="currentColor" />
          </svg>
          Please select the ID column before saving.
        </span>
      </div>
      <div class="flex items-center gap-5">
        <BaseButton
          variant="secondary"
          class="px-5 py-2 rounded-full font-semibold text-sm"
          @click="close"
        >
          Cancel
        </BaseButton>

        <!-- Tooltip-Enabled Save Button -->
        <div class="relative">
          <button
            ref="saveBtnRef"
            :disabled="saveDisabled"
            :class="[
              'ml-2 px-7 py-2 rounded-full font-bold text-base transition shadow-xl',
              saveDisabled
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed opacity-60'
                : 'bg-gradient-to-r from-blue-600 via-purple-500 to-pink-400 text-white hover:scale-105 hover:shadow-2xl',
            ]"
            style="pointer-events: auto !important"
            @mouseenter="showTooltip = saveDisabled"
            @mouseleave="showTooltip = false"
            @focus="showTooltip = saveDisabled"
            @blur="showTooltip = false"
            @click="!saveDisabled && saveMappings()"
          >
            <span v-if="!justSaved">Save Mappings</span>
            <span v-else class="flex items-center gap-2">
              <svg
                class="w-5 h-5 text-green-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="3"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Saved!
            </span>
          </button>
          <!-- Tooltip -->
          <div
            v-if="saveDisabled && showTooltip"
            ref="tooltipRef"
            :style="floatingStyles"
            class="z-50 bg-gray-800 text-white text-xs rounded px-3 py-2 absolute shadow-lg"
          >
            {{ saveDisabledReason }}
          </div>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FieldTree from '@/components/groundtruth/FieldTree.vue'
import MappingList from '@/components/groundtruth/MappingList.vue'
import ValidationBanner from '@/components/groundtruth/ValidationBanner.vue'
import GroundTruthSample from '@/components/groundtruth/GroundTruthSample.vue'
import IdFieldSelector from '@/components/groundtruth/IdFieldSelector.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { schemasApi } from '@/services/schemasApi'
import { groundtruthApi } from '@/services/groundtruthApi'

const props = defineProps({
  projectId: { type: [String, Number], default: undefined },
  groundTruth: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'configured'])
const toast = useToast()

// --- State
const schemas = ref([])
const selectedSchemaId = ref('')
const schemaFieldTypes = ref({})
const schemaFieldPaths = ref([])
const schemaFieldTree = ref({})
const requiredFields = ref([])
const groundTruthFieldTypes = ref({})
const groundTruthFieldPaths = ref([])
const groundTruthFieldTree = ref({})
const sampleDoc = ref(null)
const availableColumns = ref([])
const currentIdColumn = ref('')
const idColumn = ref('') // for all formats
const jsonIdField = ref('') // for JSON/ZIP
const selectedSchemaField = ref('')
const selectedGroundTruthField = ref('')
const mappings = ref([])
const validationStatus = ref(null)
const loading = ref(false)
const justSaved = ref(false)
const saveDisabled = computed(() => !canSave.value || justSaved.value)

const saveBtnRef = ref(null)
const tooltipRef = ref(null)
const showTooltip = ref(false)

const { floatingStyles } = useFloating(saveBtnRef, tooltipRef, {
  placement: 'top',
  middleware: [offset(10), flip(), shift()],
  whileElementsMounted: autoUpdate,
})

function normStr(v) {
  return (v ?? '').toString().trim()
}
function mergeColumns(rawCols, sample) {
  const merged = Array.isArray(rawCols) ? [...rawCols] : []
  const seen = new Set(merged.map((c) => normStr(c).toLowerCase()).filter(Boolean))
  if (sample && typeof sample === 'object' && !Array.isArray(sample)) {
    for (const k of Object.keys(sample)) {
      const nk = normStr(k)
      if (nk && !seen.has(nk.toLowerCase())) {
        merged.push(k) // keep original casing from sample
        seen.add(nk.toLowerCase())
      }
    }
  }
  return merged
}

const saveDisabledReason = computed(() => {
  if (!selectedSchemaId.value) {
    return 'Please select a schema.'
  }
  if (!mappings.value.length) {
    return 'At least one field mapping is required.'
  }
  if (isTabularFormat.value && !idColumn.value) {
    return 'You must select an ID column for CSV/XLSX files.'
  }
  if (isJsonFormat.value && idColumn.value === '__field__' && !jsonIdField.value) {
    return 'You must select an ID field for JSON data.'
  }
  return 'Cannot save right now.'
})

const schemaDisplayName = computed(
  () => schemas.value.find((s) => s.id == selectedSchemaId.value)?.schema_name ?? '',
)

const isTabularFormat = computed(() => ['csv', 'xlsx'].includes(props.groundTruth.format))
const isJsonFormat = computed(() => ['json', 'zip'].includes(props.groundTruth.format))
const showIdSelector = computed(
  () =>
    isTabularFormat.value ||
    (isJsonFormat.value && (groundTruthFieldPaths.value.length > 0 || sampleDoc.value)),
)

onMounted(async () => {
  loading.value = true
  await Promise.all([loadSchemas(), loadGroundTruthPreview()])
  loading.value = false
})

async function loadSchemas() {
  const res = await schemasApi.list(props.projectId)
  schemas.value = res.data
}

async function loadGroundTruthPreview() {
  const previewRes = await groundtruthApi.preview(props.projectId, props.groundTruth.id)

  groundTruthFieldPaths.value = previewRes.data.fields || []
  groundTruthFieldTypes.value = previewRes.data.field_types || {}
  groundTruthFieldTree.value = buildTree(groundTruthFieldPaths.value)

  // Sample doc FIRST (we'll use its keys to augment columns for CSV)
  sampleDoc.value = null
  if (previewRes.data.preview_data) {
    const docs = Object.values(previewRes.data.preview_data)
    sampleDoc.value = docs.length ? docs[0] : null
  }

  // Raw columns from backend
  const rawCols = Array.isArray(previewRes.data.available_columns)
    ? previewRes.data.available_columns
    : []

  // Merge with sample headers to catch newly uploaded CSV columns (incl. ID)
  availableColumns.value = isTabularFormat.value ? mergeColumns(rawCols, sampleDoc.value) : rawCols

  // Resolve saved/detected ID under multiple keys
  const idColRaw =
    previewRes.data.current_id_column ??
    previewRes.data.id_column_name ??
    previewRes.data.detected_id_column ??
    previewRes.data.id_column ??
    ''
  const idCol = normStr(idColRaw)
  currentIdColumn.value = idCol

  // Setup UI by format
  if (isTabularFormat.value) {
    idColumn.value = idCol || ''
    jsonIdField.value = ''
  } else if (isJsonFormat.value) {
    if (idCol) {
      idColumn.value = '__field__'
      jsonIdField.value = idCol
    } else {
      idColumn.value = '' // filename
      jsonIdField.value = ''
    }
  }

  // Ensure detected/saved ID appears even if backend omitted it
  if (isTabularFormat.value && idCol) {
    const hasId = availableColumns.value.some(
      (c) => normStr(c).toLowerCase() === idCol.toLowerCase(),
    )
    if (!hasId) {
      availableColumns.value = [idColRaw || idCol, ...availableColumns.value]
    }
  }
}

async function onSchemaChange() {
  if (!selectedSchemaId.value) return
  loading.value = true
  const schemaFieldRes = await schemasApi.getFieldTypes(props.projectId, selectedSchemaId.value)
  schemaFieldTypes.value = schemaFieldRes.data || {}
  schemaFieldPaths.value = Object.keys(schemaFieldTypes.value)
  schemaFieldTree.value = buildTree(schemaFieldPaths.value)
  const schemaRes = await schemasApi.get(props.projectId, selectedSchemaId.value)
  requiredFields.value = extractRequiredFields(schemaRes.data.schema_definition)
  await loadExistingMappings()
  selectedSchemaField.value = ''
  selectedGroundTruthField.value = ''
  validationStatus.value = null
  loading.value = false
}

// --- Build tree structure from dot-paths
function buildTree(paths) {
  const tree = {}
  for (const path of paths) {
    const parts = path.split('.')
    let node = tree
    for (const part of parts) {
      if (!node[part]) node[part] = {}
      node = node[part]
    }
  }
  return tree
}

// --- Extract required fields as dot-paths
function extractRequiredFields(schema, prefix = '') {
  let req = []
  if (schema.properties) {
    for (const prop in schema.properties) {
      const propDef = schema.properties[prop]
      const full = prefix ? `${prefix}.${prop}` : prop
      if ((schema.required || []).includes(prop)) req.push(full)
      if (propDef.type === 'object' && propDef.properties) {
        req = req.concat(extractRequiredFields(propDef, full))
      }
      if (propDef.type === 'array' && propDef.items?.type === 'object') {
        req = req.concat(extractRequiredFields(propDef.items, full + '[]'))
      }
    }
  }
  return req
}

const canAddMapping = computed(
  () =>
    !!selectedSchemaId.value &&
    !!selectedSchemaField.value &&
    !!selectedGroundTruthField.value &&
    !mappings.value.some((m) => m.schema_field === selectedSchemaField.value),
)

function addMapping() {
  if (!canAddMapping.value) return
  mappings.value.push({
    schema_id: Number(selectedSchemaId.value),
    schema_field: selectedSchemaField.value,
    ground_truth_field: selectedGroundTruthField.value,
    field_type: schemaFieldTypes.value[selectedSchemaField.value] || 'string',
    comparison_method: 'exact',
    comparison_options: {},
  })
  selectedSchemaField.value = ''
  selectedGroundTruthField.value = ''
}

function removeMapping(idx) {
  mappings.value.splice(idx, 1)
}
function clearMappings() {
  mappings.value = []
}
function isMapped(schemaPath) {
  return mappings.value.some((m) => m.schema_field === schemaPath)
}
const mappingComplete = computed(() => {
  return requiredFields.value.every((f) => isMapped(f))
})
const mappedSchemaPaths = computed(() => mappings.value.map((m) => m.schema_field))
const mappedGtPaths = computed(() => mappings.value.map((m) => m.ground_truth_field))

/** mark required fields that are not yet mapped */
const highlightRequiredUnmapped = (p) =>
  requiredFields.value.includes(p) && !mappings.value.some((m) => m.schema_field === p)

function autoMap() {
  if (!selectedSchemaId.value) return
  mappings.value = []
  for (const schemaField of schemaFieldPaths.value) {
    if (groundTruthFieldPaths.value.includes(schemaField)) {
      mappings.value.push({
        schema_id: Number(selectedSchemaId.value),
        schema_field: schemaField,
        ground_truth_field: schemaField,
        field_type: schemaFieldTypes.value[schemaField] || 'string',
        comparison_method: 'exact',
        comparison_options: {},
      })
    }
  }
}
const canSave = computed(() => {
  if (!selectedSchemaId.value) return false
  if (mappings.value.length === 0) return false
  // If CSV/XLSX, must select an id column
  if (isTabularFormat.value && !idColumn.value) return false
  // If JSON and user picked "use field", require jsonIdField
  if (isJsonFormat.value && idColumn.value === '__field__' && !jsonIdField.value) return false
  return true
})
async function saveMappings() {
  // Always update idColumn before mappings, if changed
  if (isTabularFormat.value) {
    if (idColumn.value && idColumn.value !== currentIdColumn.value) {
      await saveIdColumn()
    }
  } else if (isJsonFormat.value) {
    if (idColumn.value === '__field__' && jsonIdField.value !== currentIdColumn.value) {
      await saveIdColumn()
    } else if (!idColumn.value && currentIdColumn.value) {
      // User switched to "filename"
      await saveIdColumn()
    }
  }
  // Save mappings
  await groundtruthApi.setMappings(
    props.projectId,
    props.groundTruth.id,
    selectedSchemaId.value,
    mappings.value,
  )
  toast.success('Mappings saved successfully!')
  justSaved.value = true
  setTimeout(() => {
    justSaved.value = false
    emit('configured')
    emit('close')
  }, 1500)
}

async function saveIdColumn() {
  let payload = {}
  if (isTabularFormat.value) {
    payload.id_column = idColumn.value
  } else if (isJsonFormat.value) {
    if (idColumn.value === '__field__') {
      payload.id_column = jsonIdField.value
    } else {
      payload.id_column = '' // use filename
    }
  }
  await groundtruthApi.setIdColumn(props.projectId, props.groundTruth.id, payload)
  currentIdColumn.value =
    isJsonFormat.value && idColumn.value === '__field__'
      ? jsonIdField.value
      : isTabularFormat.value
        ? idColumn.value
        : ''
}

async function loadExistingMappings() {
  try {
    const res = await groundtruthApi.getMappings(
      props.projectId,
      props.groundTruth.id,
      selectedSchemaId.value,
    )
    mappings.value = (res.data || []).map((m) => ({
      ...m,
      schema_id: Number(selectedSchemaId.value),
      field_type: m.field_type || 'string',
      comparison_method: m.comparison_method || 'exact',
      comparison_options: m.comparison_options || {},
    }))
  } catch {
    mappings.value = []
  }
}
function onSchemaFieldSelect(path) {
  if (!selectedSchemaId.value) return
  selectedSchemaField.value = path
}
function onGroundTruthFieldSelect(path) {
  if (!selectedSchemaId.value) return
  selectedGroundTruthField.value = path
}
const idCandidates = computed(() => {
  if (!sampleDoc.value) return []
  const allFields = Object.keys(sampleDoc.value)
  const idLike = allFields.filter((k) => /id|name|number/i.test(k))
  return idLike.length ? idLike : allFields
})
const displayedColumns = computed(() => {
  const cols = availableColumns.value || []
  const idCol = currentIdColumn.value
  const hasId = cols.some((c) => (c ?? '').toString().trim() === (idCol ?? '').toString().trim())
  return idCol && !hasId ? [idCol, ...cols] : cols
})

function updateIdColumn(val) {
  idColumn.value = val
}
function updateJsonIdField(val) {
  jsonIdField.value = val
}
watch(idColumn, (val) => {
  if (isTabularFormat.value && val && val !== currentIdColumn.value) {
    saveIdColumn()
  }
})
function close() {
  emit('close')
}
</script>

<style scoped>
.bg-gray-800 {
  background-color: #262626;
}
</style>
