<template>
  <div class="flex flex-col gap-1 min-w-[220px]">
    <div class="font-semibold text-blue-900 mb-0.5 text-base flex items-center gap-2">
      <span class="text-xs text-blue-500">
        <!-- File SVG -->
        <svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M9 7h6M9 12h6M9 17h2"/>
        </svg>
      </span>
      Document ID
      <span v-if="isTabular" class="text-red-500 text-lg leading-none ml-1">*</span>
    </div>
    <!-- CSV/XLSX: column dropdown -->
    <template v-if="isTabular">
      <select
        v-model="innerIdColumn"
        @change="updateId"
        :class="[
          'px-3 py-1.5 rounded-lg border bg-white/80 text-base shadow focus:ring-2 focus:ring-blue-400 transition min-w-[140px]',
          !innerIdColumn ? 'border-red-300 focus:border-red-400' : 'border-blue-200'
        ]"
        required
      >
        <option value="" disabled>Select ID column...</option>
        <option v-for="c in availableColumns" :key="c" :value="c">{{ c }}</option>
      </select>
      <div v-if="!innerIdColumn" class="text-xs text-red-500 mt-1 flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <circle cx="12" cy="16" r="1" />
        </svg>
        Please select an ID column to enable evaluation.
      </div>
    </template>
    <!-- JSON/ZIP: radio chip choice -->
    <template v-else-if="isJson">
      <div class="flex flex-wrap gap-3 items-center mt-1">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            class="accent-purple-500"
            value=""
            v-model="innerIdColumn"
            @change="updateId"
          />
          <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold border border-blue-100">
            Use document filename
          </span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            class="accent-purple-500"
            value="__field__"
            v-model="innerIdColumn"
            @change="updateId"
          />
          <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold border border-blue-100">
            Use field:
          </span>
          <select
            v-if="innerIdColumn === '__field__'"
            v-model="innerJsonIdField"
            @change="updateJsonId"
            class="ml-1 px-2 py-1 rounded-lg border text-base bg-white/90 shadow min-w-[120px]"
          >
            <option value="" disabled>Select field...</option>
            <option v-for="f in idCandidates" :key="f" :value="f">{{ f }}</option>
          </select>
        </label>
      </div>
      <div v-if="innerIdColumn === '__field__' && innerJsonIdField" class="text-xs mt-1 text-purple-700 font-mono">
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-xs font-bold border border-purple-200">
          <!-- Key SVG -->
          <svg class="w-4 h-4 inline-block" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 17v4M12 3v4"/>
          </svg>
          {{ innerJsonIdField }}
        </span>
      </div>
    </template>
    <div class="text-xs text-gray-500 mt-1">
      Controls how documents are matched to trial results for evaluation.
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
const props = defineProps({
  isJson: Boolean,
  isTabular: Boolean,
  idColumn: String,
  jsonIdField: String,
  availableColumns: Array,
  idCandidates: Array,
  currentIdColumn: String,
});
const emit = defineEmits(["update:id-column", "update:json-id-field"]);
const innerIdColumn = ref(props.idColumn || "");
const innerJsonIdField = ref(props.jsonIdField || "");
watch(() => props.idColumn, v => innerIdColumn.value = v);
watch(() => props.jsonIdField, v => innerJsonIdField.value = v);

function updateId() {
  emit("update:id-column", innerIdColumn.value);
}
function updateJsonId() {
  emit("update:json-id-field", innerJsonIdField.value);
}
</script>
