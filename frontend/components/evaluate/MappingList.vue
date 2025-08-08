<template>
  <div class="w-full">
    <div v-if="mappings.length === 0" class="text-xs text-gray-400 text-center py-4">
      No mappings yet.<br/>Select a schema field and a GT field and click <b>Map</b>.
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
          <span v-if="schemaFieldTypes?.[m.schema_field]" class="text-gray-400">({{ schemaFieldTypes[m.schema_field] }})</span>
          <!-- Tooltip (shows on hover) -->
          <span
            v-if="hoverIdx === i"
            class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white text-blue-900 rounded-xl px-4 py-2 border border-blue-200 shadow-xl font-mono text-xs pointer-events-none"
            style="white-space: pre-line;"
          >
            <strong>Schema field:</strong><br/>
            {{ m.schema_field }}
            <template v-if="schemaFieldTypes?.[m.schema_field]">
              <span class="text-gray-400">({{ schemaFieldTypes[m.schema_field] }})</span>
            </template>
          </span>
        </span>
        <!-- Arrow Icon -->
        <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h8M14 8l4 4-4 4"/>
        </svg>
        <!-- Ground Truth Field -->
        <span
          class="bg-purple-100 px-2 py-0.5 rounded font-mono text-xs font-semibold text-purple-800 overflow-hidden text-ellipsis whitespace-nowrap max-w-[45%] inline-block cursor-pointer"
          @mouseenter="hoverIdx2 = i"
          @mouseleave="hoverIdx2 = -1"
        >
          {{ m.ground_truth_field }}
          <span v-if="groundTruthFieldTypes?.[m.ground_truth_field]" class="text-gray-400">({{ groundTruthFieldTypes[m.ground_truth_field] }})</span>
          <!-- Tooltip (shows on hover) -->
          <span
            v-if="hoverIdx2 === i"
            class="absolute z-40 left-2 top-9 w-max max-w-[300px] bg-white text-purple-900 rounded-xl px-4 py-2 border border-purple-200 shadow-xl font-mono text-xs pointer-events-none"
            style="white-space: pre-line;"
          >
            <strong>GT field:</strong><br/>
            {{ m.ground_truth_field }}
            <template v-if="groundTruthFieldTypes?.[m.ground_truth_field]">
              <span class="text-gray-400">({{ groundTruthFieldTypes[m.ground_truth_field] }})</span>
            </template>
          </span>
        </span>
        <!-- Remove -->
        <button
          @click="$emit('remove', i)"
          class="ml-2 text-red-300 hover:text-red-700"
          title="Remove mapping"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref } from "vue";
const props = defineProps({
  mappings: Array,
  schemaFieldTypes: Object,
  groundTruthFieldTypes: Object
});
const hoverIdx = ref(-1);    // For schema
const hoverIdx2 = ref(-1);   // For GT
</script>
