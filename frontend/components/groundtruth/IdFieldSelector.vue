<template>
  <div class="flex flex-col gap-1 min-w-[220px]">
    <div
      class="font-semibold text-blue-900 dark:text-blue-300 mb-0.5 text-base flex items-center gap-2"
    >
      <span class="text-xs text-blue-500 dark:text-blue-400">
        <!-- File SVG -->
        <FileText class="w-4 h-4 inline-block" />
      </span>
      Document ID
      <span v-if="isTabular" class="text-red-500 text-lg leading-none ml-1">*</span>
    </div>
    <!-- CSV/XLSX: column dropdown -->
    <template v-if="isTabular">
      <select
        v-model="innerIdColumn"
        :class="[
          selectClass,
          'min-w-[140px]',
          !innerIdColumn ? 'border-red-300 focus:border-red-400' : 'border-blue-200',
        ]"
        required
        @change="updateId"
      >
        <option value="" disabled>Select ID column...</option>
        <option v-for="c in availableColumns" :key="c" :value="c">{{ c }}</option>
      </select>
      <div v-if="!innerIdColumn" class="text-xs text-red-500 mt-1 flex items-center gap-1">
        <CircleAlert class="w-4 h-4" />
        Please select an ID column to enable evaluation.
      </div>
    </template>
    <!-- JSON/ZIP: radio chip choice -->
    <template v-else-if="isJson">
      <div class="flex flex-wrap gap-3 items-center mt-1">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="innerIdColumn"
            type="radio"
            class="accent-purple-500"
            value=""
            @change="updateId"
          />
          <span
            class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold border border-blue-100 dark:border-blue-800"
          >
            Use document filename
          </span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="innerIdColumn"
            type="radio"
            class="accent-purple-500"
            value="__field__"
            @change="updateId"
          />
          <span
            class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-semibold border border-blue-100 dark:border-blue-800"
          >
            Use field:
          </span>
          <select
            v-if="innerIdColumn === '__field__'"
            v-model="innerJsonIdField"
            :class="[selectClass, 'min-w-[120px]']"
            @change="updateJsonId"
          >
            <option value="" disabled>Select field...</option>
            <option v-for="f in idCandidates" :key="f" :value="f">{{ f }}</option>
          </select>
        </label>
      </div>
      <div
        v-if="innerIdColumn === '__field__' && innerJsonIdField"
        class="text-xs mt-1 text-purple-700 font-mono"
      >
        <StatusBadge color="purple" class="gap-1 font-bold border border-purple-200">
          <!-- Key SVG -->
          <Key class="w-4 h-4 inline-block" />
          {{ innerJsonIdField }}
        </StatusBadge>
      </div>
    </template>
    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
      Controls how documents are matched to trial results for evaluation.
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { CircleAlert, FileText, Key } from '@lucide/vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { selectClass } from '@/utils/formStyles'
const props = defineProps({
  isJson: Boolean,
  isTabular: Boolean,
  idColumn: { type: String, default: '' },
  jsonIdField: { type: String, default: '' },
  availableColumns: { type: Array, default: () => [] },
  idCandidates: { type: Array, default: () => [] },
  currentIdColumn: { type: String, default: '' },
})
const emit = defineEmits(['update:id-column', 'update:json-id-field'])
const innerIdColumn = ref(props.idColumn || '')
const innerJsonIdField = ref(props.jsonIdField || '')
watch(
  () => props.idColumn,
  (v) => (innerIdColumn.value = v),
)
watch(
  () => props.jsonIdField,
  (v) => (innerJsonIdField.value = v),
)

function updateId() {
  emit('update:id-column', innerIdColumn.value)
}
function updateJsonId() {
  emit('update:json-id-field', innerJsonIdField.value)
}
</script>
