<template>
  <div class="w-full">
    <div v-if="(mappings ?? []).length === 0" class="text-xs text-content-subtle text-center py-4">
      {{ $t('groundtruth.mapping_list.empty_line1') }}<br />{{
        $t('groundtruth.mapping_list.empty_line2')
      }}
      <b>{{ $t('groundtruth.mapping_list.map') }}</b
      >.
    </div>
    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="(m, i) in mappings ?? []"
        :key="i"
        class="bg-surface-muted border border-default px-2 py-1.5 rounded-card shadow-sm group relative"
      >
        <div class="flex items-center gap-2">
          <!-- Schema Field -->
          <Tooltip
            :text="schemaFieldTooltip(m)"
            :title="$t('groundtruth.mapping_list.schema_field')"
            class="max-w-[45%] min-w-0"
          >
            <span
              class="bg-primary-soft px-2 py-0.5 rounded-card font-mono text-xs font-semibold text-primary overflow-hidden text-ellipsis whitespace-nowrap max-w-full inline-block cursor-default"
            >
              {{ m.schema_field }}
              <span v-if="schemaFieldTypes?.[m.schema_field]" class="text-content-subtle"
                >({{ schemaFieldTypes[m.schema_field] }})</span
              >
            </span>
          </Tooltip>
          <!-- Arrow Icon -->
          <ArrowRight class="w-4 h-4 text-content-subtle flex-shrink-0" />
          <!-- Ground Truth Field -->
          <Tooltip
            :text="gtFieldTooltip(m)"
            :title="$t('groundtruth.mapping_list.gt_field')"
            class="max-w-[45%] min-w-0"
          >
            <span
              class="bg-purple-100 dark:bg-purple-900/40 px-2 py-0.5 rounded-card font-mono text-xs font-semibold text-purple-800 dark:text-purple-300 overflow-hidden text-ellipsis whitespace-nowrap max-w-full inline-block cursor-default"
            >
              {{ m.ground_truth_field }}
              <span v-if="groundTruthFieldTypes?.[m.ground_truth_field]" class="text-content-subtle"
                >({{ groundTruthFieldTypes[m.ground_truth_field] }})</span
              >
            </span>
          </Tooltip>
          <!-- Comparison method selector -->
          <select
            :value="m.comparison_method || 'exact'"
            :class="[selectClass, 'ml-auto text-[11px] px-1 py-0.5']"
            :title="getComparisonMethodDescription(m.comparison_method || 'exact')"
            @change="
              $emit('update-method', {
                index: i,
                method: ($event.target as HTMLSelectElement).value,
              })
            "
          >
            <option value="exact">exact</option>
            <option value="fuzzy">fuzzy</option>
            <option value="numeric">numeric</option>
            <option value="category">category</option>
            <option value="date">date</option>
            <option value="boolean">boolean</option>
          </select>
          <!-- Options toggle (only for methods with tunable options) -->
          <button
            v-if="hasOptions(m.comparison_method)"
            class="text-content-subtle hover:text-primary"
            :class="{ 'text-primary': optionsOpen[i] }"
            :title="$t('groundtruth.mapping_list.options_for', { field: m.schema_field })"
            type="button"
            @click="toggleOptions(i)"
          >
            <SlidersHorizontal class="w-3.5 h-3.5" />
          </button>
          <!-- Remove -->
          <button
            class="ml-1 text-red-300 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            :title="$t('groundtruth.mapping_list.remove_mapping')"
            @click="$emit('remove', i)"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
        <!-- Method description -->
        <p
          class="mt-1 text-[10px] text-content-muted leading-snug"
          :title="getComparisonMethodDescription(m.comparison_method || 'exact')"
        >
          {{ getComparisonMethodDescription(m.comparison_method || 'exact') }}
        </p>
        <!-- Type / method mismatch hints -->
        <p
          v-if="mappingHints(m).length"
          class="mt-1 text-[10px] text-amber-600 dark:text-amber-400 leading-snug flex items-start gap-1"
        >
          <AlertTriangle class="w-3 h-3 shrink-0 mt-px" />
          <span>{{ mappingHints(m).join(' · ') }}</span>
        </p>
        <!-- Tunable options for fuzzy / numeric -->
        <div
          v-if="hasOptions(m.comparison_method) && optionsOpen[i]"
          class="mt-1.5 pt-1.5 border-t border-default flex flex-wrap items-center gap-3 text-[11px] text-content-muted"
        >
          <template v-if="m.comparison_method === 'fuzzy'">
            <label class="flex items-center gap-1">
              {{ $t('groundtruth.mapping_list.threshold') }}
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                :class="[inputClass, 'w-16 px-1 py-0.5']"
                :value="getOption(m, 'threshold', 85)"
                @input="
                  setOption(i, 'threshold', Number(($event.target as HTMLInputElement).value))
                "
              />
            </label>
            <span class="text-content-subtle">{{
              $t('groundtruth.mapping_list.higher_stricter')
            }}</span>
            <label
              class="flex items-center gap-1"
              :title="$t('groundtruth.mapping_list.partial_match_hint')"
            >
              <input
                type="checkbox"
                :checked="!!getOption(m, 'allow_partial_match', false)"
                @change="
                  setOption(i, 'allow_partial_match', ($event.target as HTMLInputElement).checked)
                "
              />
              {{ $t('groundtruth.mapping_list.allow_partial') }}
            </label>
          </template>
          <template v-else-if="m.comparison_method === 'numeric'">
            <label class="flex items-center gap-1">
              {{ $t('groundtruth.mapping_list.tolerance') }}
              <input
                type="number"
                min="0"
                step="0.001"
                :class="[inputClass, 'w-16 px-1 py-0.5']"
                :value="getOption(m, 'tolerance', 0.001)"
                @input="
                  setOption(i, 'tolerance', Number(($event.target as HTMLInputElement).value))
                "
              />
            </label>
            <label class="flex items-center gap-1">
              <input
                type="checkbox"
                :checked="!!getOption(m, 'relative', false)"
                @change="setOption(i, 'relative', ($event.target as HTMLInputElement).checked)"
              />
              {{ $t('groundtruth.mapping_list.relative') }}
            </label>
          </template>
        </div>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, ArrowRight, SlidersHorizontal, X } from '@lucide/vue'
import Tooltip from '@/components/common/Tooltip.vue'
import { getComparisonMethodDescription } from '@/utils/metricsDefinitions'
import { selectClass, inputClass } from '@/utils/formStyles'
import type { ComparisonMethod } from '@/types'

interface MappingItem {
  schema_id: number
  schema_field: string
  ground_truth_field: string
  field_type: string
  comparison_method: ComparisonMethod | string
  comparison_options?: Record<string, unknown> | null
}

interface Props {
  mappings?: MappingItem[]
  schemaFieldTypes?: Record<string, string>
  groundTruthFieldTypes?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  mappings: () => [],
  schemaFieldTypes: () => ({}),
  groundTruthFieldTypes: () => ({}),
})

const emit = defineEmits<{
  remove: [index: number]
  'update-method': [payload: { index: number; method: string }]
  'update-options': [payload: { index: number; options: Record<string, unknown> }]
}>()

const { t } = useI18n({ useScope: 'global' })

const optionsOpen = ref<Record<number, boolean>>({}) // { [index]: true }

// ---- Tooltips (common Tooltip component) ----
function schemaFieldTooltip(m: MappingItem): string {
  const type = props.schemaFieldTypes?.[m.schema_field]
  return `${m.schema_field}${type ? ` (${type})` : ''}`
}
function gtFieldTooltip(m: MappingItem): string {
  const type = props.groundTruthFieldTypes?.[m.ground_truth_field]
  return `${m.ground_truth_field}${type ? ` (${type})` : ''}`
}

// ---- Type / method mismatch hints ----
/** Collapse type aliases so e.g. integer/float compare as "number". */
function baseType(t: string | null | undefined): string {
  const v = String(t || '').toLowerCase()
  if (v === 'integer' || v === 'float') return 'number'
  if (v === 'bool') return 'boolean'
  if (v === 'str' || v === 'text') return 'string'
  return v
}

/** Types considered interchangeable for the mismatch hint (category is a string). */
function comparableType(t: string | null | undefined): string {
  const v = baseType(t)
  return v === 'category' ? 'string' : v
}

/** Comparison methods that make sense per schema field type. */
const SUITABLE_METHODS: Record<string, string[]> = {
  string: ['exact', 'fuzzy', 'category', 'date'],
  number: ['numeric', 'exact'],
  boolean: ['boolean', 'exact'],
  date: ['date', 'exact', 'fuzzy'],
  category: ['category', 'exact', 'fuzzy'],
  array: ['exact'],
  object: ['exact'],
}

/** Amber warnings for a mapping row (empty array = no issues). */
function mappingHints(m: MappingItem): string[] {
  const hints: string[] = []
  const schemaType = props.schemaFieldTypes?.[m.schema_field]
  const gtType = props.groundTruthFieldTypes?.[m.ground_truth_field]
  if (schemaType && gtType && comparableType(schemaType) !== comparableType(gtType)) {
    hints.push(
      t('groundtruth.mapping_list.hint_type_mismatch', {
        schemaType,
        gtType,
      }),
    )
  }
  const fieldType = baseType(schemaType ?? m.field_type)
  const method = String(m.comparison_method || 'exact')
  const suitable = SUITABLE_METHODS[fieldType]
  if (suitable && !suitable.includes(method)) {
    hints.push(t('groundtruth.mapping_list.hint_unusual_method', { method, fieldType }))
  }
  return hints
}

function toggleOptions(i: number) {
  optionsOpen.value = { ...optionsOpen.value, [i]: !optionsOpen.value[i] }
}

function hasOptions(method: string | undefined): boolean {
  return method === 'fuzzy' || method === 'numeric'
}

function getOption(mapping: MappingItem, key: string, fallback: unknown): unknown {
  const opts = mapping.comparison_options || {}
  const v = opts[key]
  return v === undefined || v === null || v === '' ? fallback : v
}

function setOption(index: number, key: string, value: unknown) {
  const mapping = props.mappings[index]
  if (!mapping) return
  const options = { ...(mapping.comparison_options || {}) }
  options[key] = value
  emit('update-options', { index, options })
}
</script>
