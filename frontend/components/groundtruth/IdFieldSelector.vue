<template>
  <div class="flex flex-col gap-1 min-w-[220px]">
    <div class="font-semibold text-primary mb-0.5 text-base flex items-center gap-2">
      <span class="text-xs text-primary">
        <!-- File SVG -->
        <FileText class="w-4 h-4 inline-block" />
      </span>
      {{ $t('groundtruth.id_field.document_id') }}
      <span v-if="isTabular" class="text-red-500 text-lg leading-none ml-1">*</span>
    </div>
    <!-- CSV/XLSX: column dropdown -->
    <template v-if="isTabular">
      <select
        v-model="innerIdColumn"
        :class="[
          selectClass,
          'min-w-[140px]',
          !innerIdColumn
            ? 'border-red-300 dark:border-red-500 focus:border-red-400 dark:focus:border-red-400'
            : 'border-primary',
        ]"
        required
        @change="updateId"
      >
        <option value="" disabled>{{ $t('groundtruth.id_field.select_id_column') }}</option>
        <option v-for="c in availableColumns" :key="c" :value="c">{{ c }}</option>
      </select>
      <div v-if="!innerIdColumn" class="text-xs text-red-500 mt-1 flex items-center gap-1">
        <CircleAlert class="w-4 h-4" />
        {{ $t('groundtruth.id_field.select_id_column_hint') }}
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
            class="inline-flex items-center px-2 py-0.5 rounded-full bg-primary-soft text-primary text-xs font-semibold border border-default"
          >
            {{ $t('groundtruth.id_field.use_filename') }}
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
            class="inline-flex items-center px-2 py-0.5 rounded-full bg-primary-soft text-primary text-xs font-semibold border border-default"
          >
            {{ $t('groundtruth.id_field.use_field') }}
          </span>
          <select
            v-if="innerIdColumn === '__field__'"
            v-model="innerJsonIdField"
            :class="[selectClass, 'min-w-[120px]']"
            @change="updateJsonId"
          >
            <option value="" disabled>{{ $t('groundtruth.id_field.select_field') }}</option>
            <option v-for="f in idCandidates" :key="f" :value="f">{{ f }}</option>
          </select>
        </label>
      </div>
      <div
        v-if="innerIdColumn === '__field__' && innerJsonIdField"
        class="text-xs mt-1 text-purple-700 dark:text-purple-400 font-mono"
      >
        <StatusBadge color="purple" class="gap-1 font-bold border border-purple-200">
          <!-- Key SVG -->
          <Key class="w-4 h-4 inline-block" />
          {{ innerJsonIdField }}
        </StatusBadge>
      </div>
    </template>
    <div class="text-xs text-content-muted mt-1">
      {{ $t('groundtruth.id_field.match_hint') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { CircleAlert, FileText, Key } from '@lucide/vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { selectClass } from '@/utils/formStyles'

interface Props {
  isJson?: boolean
  isTabular?: boolean
  idColumn?: string
  jsonIdField?: string
  availableColumns?: string[]
  idCandidates?: string[]
  currentIdColumn?: string
}

const props = withDefaults(defineProps<Props>(), {
  isJson: false,
  isTabular: false,
  idColumn: '',
  jsonIdField: '',
  availableColumns: () => [],
  idCandidates: () => [],
  currentIdColumn: '',
})

const emit = defineEmits<{
  'update:id-column': [value: string]
  'update:json-id-field': [value: string]
}>()

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
