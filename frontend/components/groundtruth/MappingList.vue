<template>
  <div class="w-full">
    <div v-if="mappings.length === 0" class="text-xs text-slate-400 text-center py-4">
      No mappings yet.<br />Select a schema field and a GT field and click <b>Map</b>.
    </div>
    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="(m, i) in mappings"
        :key="i"
        class="flex items-center gap-2 bg-gradient-to-r from-blue-50/70 to-purple-50/60 px-2 py-1.5 rounded-lg shadow-sm border border-blue-100 group relative"
      >
        <!-- Schema Field -->
        <span
          class="bg-blue-100 px-2 py-0.5 rounded font-mono text-xs font-semibold text-blue-800 overflow-hidden text-ellipsis whitespace-nowrap max-w-[45%] inline-block cursor-pointer"
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
            class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white text-blue-900 rounded-xl px-4 py-2 border border-blue-200 shadow-xl font-mono text-xs pointer-events-none"
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
          class="bg-purple-100 px-2 py-0.5 rounded font-mono text-xs font-semibold text-purple-800 overflow-hidden text-ellipsis whitespace-nowrap max-w-[45%] inline-block cursor-pointer"
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
            class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white text-purple-900 rounded-xl px-4 py-2 border border-purple-200 shadow-xl font-mono text-xs pointer-events-none"
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
          class="ml-auto text-[11px] border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5 focus:ring-1 focus:ring-blue-400"
          :title="`How to compare ${m.schema_field}`"
          @change="$emit('update-method', { index: i, method: $event.target.value })"
        >
          <option value="exact">exact</option>
          <option value="fuzzy">fuzzy</option>
          <option value="numeric">numeric</option>
          <option value="category">category</option>
          <option value="date">date</option>
          <option value="boolean">boolean</option>
        </select>
        <!-- Remove -->
        <button
          class="ml-2 text-red-300 hover:text-red-700"
          title="Remove mapping"
          @click="$emit('remove', i)"
        >
          <X class="h-4 w-4" />
        </button>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { ArrowRight, X } from '@lucide/vue'
const props = defineProps({
  mappings: { type: Array, default: () => [] },
  schemaFieldTypes: { type: Object, default: () => ({}) },
  groundTruthFieldTypes: { type: Object, default: () => ({}) },
})
defineEmits(['remove', 'update-method'])
const hoverIdx = ref(-1) // For schema
const hoverIdx2 = ref(-1) // For GT
</script>
