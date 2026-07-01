<template>
  <DataTable
    :columns="columns"
    :items="trials"
    row-key="id"
    row-id-prefix="trial-card-"
    selectable
    :selected-keys="selectedTrials"
    :all-selected="allSelected"
    :total-selected="selectedTrials.length"
    :highlighted-keys="highlightedTrialId ? [highlightedTrialId] : []"
    :pagination="pagination"
    :page-size-options="[20, 50, 100]"
    item-label="trials"
    empty-title="No trials found"
    expandable
    :expanded-keys="expandedKeys"
    @toggle-selection="$emit('toggle-selection', $event)"
    @toggle-all="$emit('toggle-all')"
    @page-change="$emit('page-change', $event)"
    @page-size-change="$emit('page-size-change', $event)"
    @expand="toggleExpand"
  >
    <template #cell-name="{ row: trial }">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-slate-900 dark:text-white truncate">{{
            trial.name || `Trial #${trial.id}`
          }}</span>
          <StatusBadge :status="trial.status" class="font-medium" />
        </div>
        <div v-if="trial.description" class="text-xs text-slate-500 dark:text-slate-400 truncate">
          {{ trial.description }}
        </div>
      </div>
    </template>

    <template #cell-schema="{ row: trial }">
      <span class="text-sm text-slate-700 dark:text-slate-300">{{
        schemaName(trial as unknown as TrialSummary)
      }}</span>
    </template>

    <template #cell-prompt="{ row: trial }">
      <span class="text-sm text-slate-700 dark:text-slate-300">{{
        promptName(trial as unknown as TrialSummary) || '—'
      }}</span>
    </template>

    <template #cell-llm_model="{ row: trial }">
      <span class="text-sm text-slate-700 dark:text-slate-300 truncate">{{ trial.llm_model }}</span>
    </template>

    <template #cell-results="{ row: trial }">
      <div class="flex items-center gap-1.5">
        <StatusBadge color="gray" class="text-[11px] font-medium" title="Processed results">
          {{ trial.results_count || 0 }} res
        </StatusBadge>
        <StatusBadge
          v-if="trial.error_count && trial.error_count > 0"
          color="red"
          class="text-[11px]"
          title="Documents with errors"
        >
          {{ trial.error_count }} err
        </StatusBadge>
      </div>
    </template>

    <template #cell-progress="{ row: trial }">
      <!-- Active: compact inline progress -->
      <div v-if="isActive(trial as unknown as TrialSummary)" class="flex items-center gap-2">
        <div class="w-16 h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 transition-all duration-500"
            :style="{ width: progressPercent(trial as unknown as TrialSummary) + '%' }"
          ></div>
        </div>
        <span class="text-xs text-slate-500 dark:text-slate-400"
          >{{ docsDone(trial as unknown as TrialSummary) }}/{{
            totalDocs(trial as unknown as TrialSummary)
          }}</span
        >
      </div>
      <!-- End states -->
      <div
        v-else-if="trial.status === 'completed'"
        class="flex items-center gap-1 text-green-600 dark:text-green-400 text-xs font-medium"
      >
        <CircleCheckBig class="w-4 h-4" />
        Ready
      </div>
      <div
        v-else-if="trial.status === 'failed'"
        class="flex items-center gap-1 text-red-600 dark:text-red-400 text-xs font-medium"
      >
        <AlertCircle class="w-4 h-4" />
        Failed
      </div>
      <span v-else class="text-xs text-slate-400 dark:text-slate-500">{{ trial.status }}</span>
    </template>

    <template #cell-created_at="{ row: trial }">
      <span class="text-sm text-slate-500 dark:text-slate-400">
        {{ formatDateSmart(trial.created_at) }}
      </span>
    </template>

    <template #row-actions="{ row: trial }">
      <BaseButton
        variant="secondary"
        size="sm"
        @click.stop="$emit('view-results', trial as unknown as TrialSummary)"
      >
        Results
      </BaseButton>
    </template>

    <template #expanded="{ row: trial }">
      <TrialDetailPanel
        :trial="trial as unknown as TrialSummary"
        :schemas="schemas"
        :prompts="prompts"
        @rename="$emit('rename', $event)"
        @delete="$emit('delete', $event)"
        @retry="$emit('retry', $event)"
        @download="$emit('download', $event)"
        @view-results="$emit('view-results', $event)"
        @view-schema="$emit('view-schema', $event)"
        @view-prompt="$emit('view-prompt', $event)"
        @cancel="$emit('cancel', $event)"
      />
    </template>
  </DataTable>
</template>

<script setup lang="ts">
import { computed, ref, type PropType } from 'vue'
import { AlertCircle, CircleCheckBig } from '@lucide/vue'
import DataTable from '@/components/common/DataTable.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import TrialDetailPanel from './TrialDetailPanel.vue'
import { formatDateSmart } from '@/utils/formatters'
import type { TrialSummary, Schema, Prompt } from '@/types'

interface TablePagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

const props = defineProps({
  trials: { type: Array as PropType<TrialSummary[]>, required: true },
  schemas: { type: Array as PropType<Schema[]>, required: true },
  prompts: { type: Array as PropType<Prompt[]>, required: true },
  selectedTrials: { type: Array as PropType<number[]>, default: () => [] },
  highlightedTrialId: { type: [Number, String] as PropType<number | string | null>, default: null },
  pagination: { type: Object as PropType<TablePagination | null>, default: null },
})

defineEmits<{
  'toggle-selection': [id: number]
  'toggle-all': []
  'page-change': [page: number]
  'page-size-change': [size: number]
  rename: [trial: TrialSummary]
  delete: [trial: TrialSummary]
  retry: [trial: TrialSummary]
  download: [trial: TrialSummary]
  'view-results': [trial: TrialSummary]
  'view-schema': [trial: TrialSummary]
  'view-prompt': [trial: TrialSummary]
  cancel: [trial: TrialSummary]
}>()

const allSelected = computed(
  () => props.trials.length > 0 && props.selectedTrials.length === props.trials.length,
)

const expandedKeys = ref<number[]>([])

const toggleExpand = (id: number): void => {
  const idx = expandedKeys.value.indexOf(id)
  if (idx > -1) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(id)
  }
}

const columns = [
  { key: 'name', label: 'Trial' },
  { key: 'schema', label: 'Schema' },
  { key: 'prompt', label: 'Prompt' },
  { key: 'llm_model', label: 'Model' },
  { key: 'results', label: 'Results' },
  { key: 'progress', label: 'Progress' },
  { key: 'created_at', label: 'Started' },
]

function schemaName(trial: TrialSummary): string {
  const name = trial.schema_snapshot?.schema_name
  return (typeof name === 'string' && name) || '-'
}

function promptName(trial: TrialSummary): string | undefined {
  const name = trial.prompt_snapshot?.name
  return typeof name === 'string' ? name : undefined
}

function isActive(trial: TrialSummary): boolean {
  return !['completed', 'failed', 'cancelled'].includes(trial.status)
}

function docsDone(trial: TrialSummary): number {
  if (trial.docs_done != null) return trial.docs_done
  if (trial.progress != null) {
    const total = trial.document_ids?.length ?? 0
    return Math.round((trial.progress || 0) * total)
  }
  return 0
}

function totalDocs(trial: TrialSummary): number {
  return trial.document_ids?.length ?? 0
}

function progressPercent(trial: TrialSummary): number {
  return trial.progress != null ? Math.round((trial.progress || 0) * 100) : 0
}
</script>
