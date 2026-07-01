<template>
  <BaseModal
    :open="open"
    size="full"
    panel-class="bg-white/90 dark:bg-slate-900/95 max-w-none min-h-[420px]"
    header-class="bg-gradient-to-r from-white/80 to-blue-50/70 dark:from-slate-900/80 dark:to-slate-800/70 sticky top-0 z-10 rounded-t-2xl"
    body-class="flex flex-col"
    footer-class="bg-white/90 dark:bg-slate-900/95 flex-col md:flex-row md:items-center justify-between! sticky bottom-0 z-10 rounded-b-2xl shadow text-[15px]"
    @close="close"
  >
    <template #header>
      <div>
        <h2 class="text-xl font-bold tracking-tight mb-0.5 dark:text-white">
          Configure Ground Truth Mapping
        </h2>
        <div class="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
          <span class="font-mono text-blue-700 dark:text-blue-400">Project {{ projectId }}</span>
          <span
            v-if="selectedSchemaId"
            class="inline-block px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300"
            >{{ schemaDisplayName }}</span
          >
        </div>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          For each schema field (left), pick the ground-truth column (right) that holds the matching
          value. The ID field links each document's extraction to its correct row.
        </p>
      </div>
    </template>

    <!-- TOP CONTROLS -->
    <section
      class="flex flex-wrap md:flex-nowrap items-center gap-3 px-6 py-3 border-b bg-white/90 dark:bg-slate-900/90 backdrop-blur rounded-t-none z-10 text-[15px] dark:border-slate-700"
    >
      <div>
        <label class="text-[15px] font-medium mr-2 dark:text-slate-200">Schema</label>
        <select
          v-model="selectedSchemaId"
          class="px-2 py-1.5 rounded-lg border border-blue-200 dark:border-slate-600 bg-white/70 dark:bg-slate-800 text-[15px] dark:text-slate-100 shadow focus:ring-2 focus:ring-blue-400 transition"
          @change="onSchemaChange"
        >
          <option value="" disabled>Select schema...</option>
          <option v-for="s in schemas" :key="s.id" :value="s.id">
            {{ s.schema_name }} ({{ s.id }})
          </option>
        </select>
      </div>
      <div v-if="schemaFieldPaths.length" class="text-xs text-slate-400 dark:text-slate-500">
        <span class="font-mono text-blue-600 dark:text-blue-400">{{
          schemaFieldPaths.length
        }}</span>
        fields
      </div>
      <div class="flex-1"></div>
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
      class="flex-1 flex flex-col md:flex-row min-h-0 bg-gradient-to-br from-white/95 to-blue-50/80 dark:from-slate-900/95 dark:to-slate-800/80 overflow-y-auto"
    >
      <!-- LEFT: SCHEMA FIELDS -->
      <section
        class="w-full md:w-1/3 flex flex-col border-r bg-white/80 dark:bg-slate-900/60 dark:border-slate-700 p-4 min-w-0"
      >
        <div
          class="mb-2 text-base font-semibold text-blue-800 dark:text-blue-300 flex items-center gap-2"
        >
          <span>Schema Fields</span>
          <span
            v-if="requiredFields.length"
            class="ml-2 px-2 py-0.5 rounded-full text-pink-700 dark:text-pink-300 bg-pink-50 dark:bg-pink-900/30 text-xs"
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
            node-color="text-blue-700 dark:text-blue-400"
            :mapped="mappedSchemaPaths"
            :highlight="highlightRequiredUnmapped"
            @select="onSchemaFieldSelect"
          />
        </div>
      </section>

      <!-- CENTER: MAPPING PANEL -->
      <section
        class="w-full md:w-1/3 flex flex-col border-r bg-gradient-to-b from-blue-50/80 to-blue-100/80 dark:from-slate-800/80 dark:to-slate-800/60 dark:border-slate-700 px-3 pt-6 pb-2 min-w-0"
      >
        <div class="flex flex-col gap-3 mb-3">
          <BaseButton
            :disabled="!canAddMapping"
            class="w-full py-1.5 font-semibold text-[15px] active:scale-95"
            @click="addMapping"
          >
            <span class="flex items-center justify-center gap-2">
              <ArrowUpRight class="w-5 h-5" />
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
              <Sun class="w-5 h-5" />
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
            @update-method="updateMethod"
            @update-options="updateMappingOptions"
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
      <section class="w-full md:w-1/3 flex flex-col bg-white/90 dark:bg-slate-900/60 p-4 min-w-0">
        <div
          class="mb-2 text-base font-semibold text-purple-900 dark:text-purple-300 flex items-center gap-2"
        >
          Ground Truth Fields
          <span
            v-if="groundTruthFieldPaths.length"
            class="ml-2 text-slate-400 dark:text-slate-500 text-xs"
            >{{ groundTruthFieldPaths.length }} fields</span
          >
        </div>
        <div class="flex-1 overflow-auto custom-scrollbar pr-1.5 min-w-0 text-[13px]">
          <FieldTree
            :fields="groundTruthFieldTree"
            :types="groundTruthFieldTypes"
            :selected="selectedGroundTruthField"
            :disabled="!selectedSchemaId"
            node-color="text-purple-700 dark:text-purple-400"
            :mapped="mappedGtPaths"
            @select="onGroundTruthFieldSelect"
          />
        </div>
        <div class="mt-2">
          <GroundTruthSample
            v-if="sampleDoc"
            :doc="sampleDoc"
            :format="groundTruth?.format ?? ''"
            class="w-full"
          />
        </div>
      </section>
    </div>

    <!-- Loading Overlay -->
    <div
      v-if="loading"
      class="absolute inset-0 bg-white/80 dark:bg-slate-900/80 flex flex-col items-center justify-center z-20 rounded-2xl"
    >
      <LoadingSpinner size="large" />
      <div class="mt-3 text-blue-600 dark:text-blue-400 font-bold text-lg">Loading...</div>
    </div>

    <template #footer>
      <div>
        <span v-if="!selectedSchemaId" class="text-slate-500 dark:text-slate-400">
          Please select a schema to start mapping fields.
        </span>
        <span
          v-else-if="mappings.length && !mappingComplete"
          class="text-yellow-700 dark:text-yellow-400 font-medium flex items-center gap-2"
        >
          <CircleAlert class="w-5 h-5 text-yellow-500" />
          Warning: not all required fields are mapped!
        </span>
        <span
          v-if="isTabularFormat && !idColumn"
          class="block mt-1 text-xs text-red-600 dark:text-red-400 font-semibold flex items-center gap-2"
        >
          <CircleAlert class="w-4 h-4" />
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
                ? 'bg-slate-300 text-slate-500 dark:bg-slate-700 dark:text-slate-400 cursor-not-allowed opacity-60'
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
              <Check class="w-5 h-5 text-green-300" />
              Saved!
            </span>
          </button>
          <!-- Tooltip -->
          <div
            v-if="saveDisabled && showTooltip"
            ref="tooltipRef"
            :style="floatingStyles"
            class="z-50 bg-slate-800 text-white text-xs rounded px-3 py-2 absolute shadow-lg"
          >
            {{ saveDisabledReason }}
          </div>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToast } from '@/composables/useToast'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/vue'
import { ArrowUpRight, Check, CircleAlert, Sun } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FieldTree from '@/components/groundtruth/FieldTree.vue'
import MappingList from '@/components/groundtruth/MappingList.vue'
import GroundTruthSample from '@/components/groundtruth/GroundTruthSample.vue'
import IdFieldSelector from '@/components/groundtruth/IdFieldSelector.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { schemasApi } from '@/services/schemasApi'
import { groundtruthApi } from '@/services/groundtruthApi'
import type { GroundTruth, Schema, SchemaDefinition, ComparisonMethod, FieldType } from '@/types'

/** Actual shape returned by `GET /groundtruth/{id}/preview` (richer than the
 * shared `GroundTruthPreview` type, which only models the list-view summary). */
interface GroundTruthPreviewData {
  fields?: string[]
  field_types?: Record<string, string>
  preview_data?: Record<string, unknown>
  available_columns?: string[]
  current_id_column?: string | null
}

interface MappingItem {
  schema_id: number
  schema_field: string
  ground_truth_field: string
  field_type: FieldType
  comparison_method: ComparisonMethod
  comparison_options: Record<string, unknown>
}

interface Props {
  open: boolean
  projectId?: string | number
  groundTruth?: GroundTruth | null
}

const props = withDefaults(defineProps<Props>(), {
  projectId: undefined,
  groundTruth: () => ({}) as GroundTruth,
})
const emit = defineEmits<{ close: []; configured: [] }>()
const toast = useToast()

// --- State
const schemas = ref<Schema[]>([])
const selectedSchemaId = ref('')
const schemaFieldTypes = ref<Record<string, string>>({})
const schemaFieldPaths = ref<string[]>([])
const schemaFieldTree = ref<Record<string, unknown>>({})
const requiredFields = ref<string[]>([])
const groundTruthFieldTypes = ref<Record<string, string>>({})
const groundTruthFieldPaths = ref<string[]>([])
const groundTruthFieldTree = ref<Record<string, unknown>>({})
const sampleDoc = ref<Record<string, unknown> | null>(null)
const availableColumns = ref<string[]>([])
const currentIdColumn = ref('')
const idColumn = ref('') // for all formats
const jsonIdField = ref('') // for JSON/ZIP
const selectedSchemaField = ref('')
const selectedGroundTruthField = ref('')
const mappings = ref<MappingItem[]>([])
const loading = ref(false)
const justSaved = ref(false)
const saveDisabled = computed(() => !canSave.value || justSaved.value)

const saveBtnRef = ref<HTMLElement | null>(null)
const tooltipRef = ref<HTMLElement | null>(null)
const showTooltip = ref(false)

const { floatingStyles } = useFloating(saveBtnRef, tooltipRef, {
  placement: 'top',
  middleware: [offset(10), flip(), shift()],
  whileElementsMounted: autoUpdate,
})

function normStr(v: unknown): string {
  return (v ?? '').toString().trim()
}
function mergeColumns(rawCols: string[], sample: Record<string, unknown> | null): string[] {
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
  () => schemas.value.find((s) => String(s.id) === selectedSchemaId.value)?.schema_name ?? '',
)

const isTabularFormat = computed(() => ['csv', 'xlsx'].includes(props.groundTruth?.format ?? ''))
const isJsonFormat = computed(() => ['json', 'zip'].includes(props.groundTruth?.format ?? ''))
const showIdSelector = computed(
  () =>
    isTabularFormat.value ||
    (isJsonFormat.value && (groundTruthFieldPaths.value.length > 0 || sampleDoc.value)),
)

// Load data whenever the modal opens (component stays mounted to enable the
// close transition). Immediate so the first open also loads.
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      loading.value = true
      await Promise.all([loadSchemas(), loadGroundTruthPreview()])
      loading.value = false
    } else {
      // Reset user-editable mapping state so a reopen starts fresh.
      selectedSchemaId.value = ''
      schemaFieldTypes.value = {}
      schemaFieldPaths.value = []
      schemaFieldTree.value = {}
      requiredFields.value = []
      selectedSchemaField.value = ''
      selectedGroundTruthField.value = ''
      mappings.value = []
      justSaved.value = false
    }
  },
  { immediate: true },
)

async function loadSchemas() {
  const res = await schemasApi.list(props.projectId!)
  schemas.value = res.data
}

async function loadGroundTruthPreview() {
  const previewRes = await groundtruthApi.preview(props.projectId!, props.groundTruth!.id)
  const data = previewRes.data as GroundTruthPreviewData

  groundTruthFieldPaths.value = data.fields || []
  groundTruthFieldTypes.value = data.field_types || {}
  groundTruthFieldTree.value = buildTree(groundTruthFieldPaths.value)

  // Sample doc FIRST (we'll use its keys to augment columns for CSV)
  sampleDoc.value = null
  if (data.preview_data) {
    const docs = Object.values(data.preview_data)
    sampleDoc.value = docs.length ? (docs[0] as Record<string, unknown>) : null
  }

  // Raw columns from backend
  const rawCols = Array.isArray(data.available_columns) ? data.available_columns : []

  // Merge with sample headers to catch newly uploaded CSV columns (incl. ID)
  availableColumns.value = isTabularFormat.value ? mergeColumns(rawCols, sampleDoc.value) : rawCols

  // Resolve saved/detected ID under multiple keys
  const idColRaw =
    (data.current_id_column as string | null) ??
    (props.groundTruth!.id_column_name as string | null) ??
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
  const schemaFieldRes = await schemasApi.getFieldTypes(props.projectId!, selectedSchemaId.value)
  schemaFieldTypes.value = schemaFieldRes.data || {}
  schemaFieldPaths.value = Object.keys(schemaFieldTypes.value)
  schemaFieldTree.value = buildTree(schemaFieldPaths.value)
  const schemaRes = await schemasApi.get(props.projectId!, selectedSchemaId.value)
  requiredFields.value = extractRequiredFields(schemaRes.data.schema_definition)
  await loadExistingMappings()
  selectedSchemaField.value = ''
  selectedGroundTruthField.value = ''
  loading.value = false
}

// --- Build tree structure from dot-paths
function buildTree(paths: string[]): Record<string, unknown> {
  const tree: Record<string, unknown> = {}
  for (const path of paths) {
    const parts = path.split('.')
    let node = tree
    for (const part of parts) {
      if (!node[part]) node[part] = {}
      node = node[part] as Record<string, unknown>
    }
  }
  return tree
}

// --- Extract required fields as dot-paths
function extractRequiredFields(schema: SchemaDefinition | null, prefix = ''): string[] {
  let req: string[] = []
  if (schema?.properties) {
    for (const prop in schema.properties) {
      const propDef = schema.properties[prop]
      const full = prefix ? `${prefix}.${prop}` : prop
      if ((schema.required || []).includes(prop)) req.push(full)
      if (propDef.type === 'object' && propDef.properties) {
        req = req.concat(extractRequiredFields(propDef as unknown as SchemaDefinition, full))
      }
      if (propDef.type === 'array' && propDef.items?.type === 'object') {
        req = req.concat(
          extractRequiredFields(propDef.items as unknown as SchemaDefinition, full + '[]'),
        )
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
  const fieldType = (schemaFieldTypes.value[selectedSchemaField.value] || 'string') as FieldType
  mappings.value.push({
    schema_id: Number(selectedSchemaId.value),
    schema_field: selectedSchemaField.value,
    ground_truth_field: selectedGroundTruthField.value,
    field_type: fieldType,
    comparison_method: defaultMethodFor(fieldType),
    comparison_options: {},
  })
  selectedSchemaField.value = ''
  selectedGroundTruthField.value = ''
}

function removeMapping(idx: number) {
  mappings.value.splice(idx, 1)
}

/** Pick a sensible default comparison method from the field type. */
function defaultMethodFor(fieldType: string): ComparisonMethod {
  const t = String(fieldType || '').toLowerCase()
  if (t === 'category') return 'category'
  if (t === 'number') return 'numeric'
  if (t === 'boolean') return 'boolean'
  if (t === 'date') return 'date'
  return 'exact'
}

/** Update a mapping's comparison method from the MappingList selector. */
function updateMethod({ index, method }: { index: number; method: string }) {
  if (index < 0 || index >= mappings.value.length) return
  mappings.value[index].comparison_method = method as ComparisonMethod
}

/** Update a mapping's comparison options (e.g. fuzzy threshold, numeric tolerance). */
function updateMappingOptions({
  index,
  options,
}: {
  index: number
  options: Record<string, unknown>
}) {
  if (index < 0 || index >= mappings.value.length) return
  mappings.value[index].comparison_options = options
}
function clearMappings() {
  mappings.value = []
}
function isMapped(schemaPath: string) {
  return mappings.value.some((m) => m.schema_field === schemaPath)
}
const mappingComplete = computed(() => {
  return requiredFields.value.every((f) => isMapped(f))
})
const mappedSchemaPaths = computed(() => mappings.value.map((m) => m.schema_field))
const mappedGtPaths = computed(() => mappings.value.map((m) => m.ground_truth_field))

/** mark required fields that are not yet mapped */
const highlightRequiredUnmapped = (p: string): boolean =>
  requiredFields.value.includes(p) && !mappings.value.some((m) => m.schema_field === p)

function autoMap() {
  if (!selectedSchemaId.value) return
  mappings.value = []
  for (const schemaField of schemaFieldPaths.value) {
    if (groundTruthFieldPaths.value.includes(schemaField)) {
      const fieldType = (schemaFieldTypes.value[schemaField] || 'string') as FieldType
      mappings.value.push({
        schema_id: Number(selectedSchemaId.value),
        schema_field: schemaField,
        ground_truth_field: schemaField,
        field_type: fieldType,
        comparison_method: defaultMethodFor(fieldType),
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
    props.projectId!,
    props.groundTruth!.id,
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
  const payload: Record<string, unknown> = {}
  if (isTabularFormat.value) {
    payload.id_column = idColumn.value
  } else if (isJsonFormat.value) {
    if (idColumn.value === '__field__') {
      payload.id_column = jsonIdField.value
    } else {
      payload.id_column = '' // use filename
    }
  }
  await groundtruthApi.setIdColumn(props.projectId!, props.groundTruth!.id, payload)
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
      props.projectId!,
      props.groundTruth!.id,
      selectedSchemaId.value,
    )
    mappings.value = (res.data || []).map(
      (m) =>
        ({
          ...m,
          schema_id: Number(selectedSchemaId.value),
          field_type: (m.field_type || 'string') as FieldType,
          comparison_method: (m.comparison_method || 'exact') as ComparisonMethod,
          comparison_options: m.comparison_options || {},
        }) as MappingItem,
    )
  } catch {
    mappings.value = []
  }
}
function onSchemaFieldSelect(path: string) {
  if (!selectedSchemaId.value) return
  selectedSchemaField.value = path
}
function onGroundTruthFieldSelect(path: string) {
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

function updateIdColumn(val: string) {
  idColumn.value = val
}
function updateJsonIdField(val: string) {
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
