<template>
  <div class="w-full">
    <div
      v-if="(mappings ?? []).length === 0"
      class="text-xs text-slate-400 dark:text-slate-500 text-center py-4"
    >
      No mappings yet.<br />Select a schema field and a GT field and click <b>Map</b>.
    </div>
    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="(m, i) in mappings ?? []"
        :key="i"
        class="bg-gradient-to-r from-blue-50/70 to-purple-50/60 dark:from-slate-800 dark:to-slate-700/80 px-2 py-1.5 rounded-lg shadow-sm border border-blue-100 dark:border-slate-600 group relative"
      >
        <div class="flex items-center gap-2">
          <!-- Schema Field -->
          <span
            class="bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 rounded font-mono text-xs font-semibold text-blue-800 dark:text-blue-300 overflow-hidden text-ellipsis whitespace-nowrap max-w-[45%] inline-block cursor-pointer"
            @mouseenter="hoverIdx = i"
            @mouseleave="hoverIdx = -1"
          >
            {{ m.schema_field }}
            <span v-if="schemaFieldTypes?.[m.schema_field]" class="text-slate-400"
              >({{ schemaFieldTypes[m.schema_field] }})</span
            >
            <!-- Tooltip (shows on hover) -->
            <span
              v-if="hoverIdx === i"
              class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white dark:bg-slate-800 text-blue-900 dark:text-blue-200 rounded-xl px-4 py-2 border border-blue-200 dark:border-slate-600 shadow-xl font-mono text-xs pointer-events-none"
              style="white-space: pre-line"
            >
              <strong>Schema field:</strong><br />
              {{ m.schema_field }}
              <template v-if="schemaFieldTypes?.[m.schema_field]">
                <span class="text-slate-400">({{ schemaFieldTypes[m.schema_field] }})</span>
              </template>
            </span>
          </span>
          <!-- Arrow Icon -->
          <ArrowRight class="w-4 h-4 text-slate-400 flex-shrink-0" />
          <!-- Ground Truth Field -->
          <span
            class="bg-purple-100 dark:bg-purple-900/40 px-2 py-0.5 rounded font-mono text-xs font-semibold text-purple-800 dark:text-purple-300 overflow-hidden text-ellipsis whitespace-nowrap max-w-[45%] inline-block cursor-pointer"
            @mouseenter="hoverIdx2 = i"
            @mouseleave="hoverIdx2 = -1"
          >
            {{ m.ground_truth_field }}
            <span v-if="groundTruthFieldTypes?.[m.ground_truth_field]" class="text-slate-400"
              >({{ groundTruthFieldTypes[m.ground_truth_field] }})</span
            >
            <!-- Tooltip (shows on hover) -->
            <span
              v-if="hoverIdx2 === i"
              class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white dark:bg-slate-800 text-purple-900 dark:text-purple-200 rounded-xl px-4 py-2 border border-purple-200 dark:border-slate-600 shadow-xl font-mono text-xs pointer-events-none"
              style="white-space: pre-line"
            >
              <strong>GT field:</strong><br />
              {{ m.ground_truth_field }}
              <template v-if="groundTruthFieldTypes?.[m.ground_truth_field]">
                <span class="text-slate-400"
                  >({{ groundTruthFieldTypes[m.ground_truth_field] }})</span
                >
              </template>
            </span>
          </span>
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
            class="text-slate-400 hover:text-blue-600 dark:hover:text-blue-400"
            :class="{ 'text-blue-600 dark:text-blue-400': optionsOpen[i] }"
            :title="`Comparison options for ${m.schema_field}`"
            type="button"
            @click="toggleOptions(i)"
          >
            <SlidersHorizontal class="w-3.5 h-3.5" />
          </button>
          <!-- Remove -->
          <button
            class="ml-1 text-red-300 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
            title="Remove mapping"
            @click="$emit('remove', i)"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
        <!-- Method description -->
        <p
          class="mt-1 text-[10px] text-slate-500 dark:text-slate-400 leading-snug"
          :title="getComparisonMethodDescription(m.comparison_method || 'exact')"
        >
          {{ getComparisonMethodDescription(m.comparison_method || 'exact') }}
        </p>
        <!-- Tunable options for fuzzy / numeric -->
        <div
          v-if="hasOptions(m.comparison_method) && optionsOpen[i]"
          class="mt-1.5 pt-1.5 border-t border-slate-200 dark:border-slate-600 flex flex-wrap items-center gap-3 text-[11px] text-slate-600 dark:text-slate-300"
        >
          <template v-if="m.comparison_method === 'fuzzy'">
            <label class="flex items-center gap-1">
              Threshold
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
            <span class="text-slate-400 dark:text-slate-500">higher = stricter match</span>
            <label
              class="flex items-center gap-1"
              title="Off by default. Substring matching can invert meaning in medical text (e.g. 'cancer' vs 'non-cancer'), so it is opt-in."
            >
              <input
                type="checkbox"
                :checked="!!getOption(m, 'allow_partial_match', false)"
                @change="
                  setOption(i, 'allow_partial_match', ($event.target as HTMLInputElement).checked)
                "
              />
              allow partial / substring match
            </label>
          </template>
          <template v-else-if="m.comparison_method === 'numeric'">
            <label class="flex items-center gap-1">
              Tolerance
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
              relative (±%)
            </label>
          </template>
        </div>
      </li>
    </ul>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ArrowRight, SlidersHorizontal, X } from '@lucide/vue'
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

const hoverIdx = ref(-1) // For schema
const hoverIdx2 = ref(-1) // For GT
const optionsOpen = ref<Record<number, boolean>>({}) // { [index]: true }

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
