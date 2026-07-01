<template>
  <div class="p-4 space-y-3">
    <!-- Description -->
    <div v-if="trial.description" class="text-sm text-slate-600 dark:text-slate-400">
      {{ trial.description }}
    </div>

    <!-- Metadata -->
    <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
      <span class="inline-flex items-center gap-1">
        <strong class="text-slate-700 dark:text-slate-300">Schema:</strong>
        <button
          type="button"
          class="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
          title="View schema"
          @click.stop="emit('view-schema', trial)"
        >
          {{ schemaName }}
        </button>
      </span>
      <span v-if="promptName" class="inline-flex items-center gap-1">
        <strong class="text-slate-700 dark:text-slate-300">Prompt:</strong>
        <button
          type="button"
          class="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
          title="View prompt"
          @click.stop="emit('view-prompt', trial)"
        >
          {{ promptName }}
        </button>
      </span>
      <span
        ><strong class="text-slate-700 dark:text-slate-300">LLM:</strong>
        {{ trial.llm_model }}</span
      >
      <span
        ><strong class="text-slate-700 dark:text-slate-300">Started:</strong>
        {{ formatDateFull(trial.created_at) }}</span
      >
      <span v-if="trial.last_result_at"
        ><strong class="text-slate-700 dark:text-slate-300">Last result:</strong>
        {{ formatDateFull(trial.last_result_at) }}</span
      >
      <span v-if="trial.documents_count != null"
        ><strong class="text-slate-700 dark:text-slate-300">Docs:</strong>
        {{ trial.documents_count }}</span
      >
    </div>

    <!-- Progress (active) -->
    <div v-if="isActive" class="flex flex-col gap-1">
      <div class="flex items-center gap-2 text-xs">
        <span class="font-medium text-blue-600 dark:text-blue-400"
          >{{ docsDone }}/{{ totalDocs }} docs</span
        >
        <span class="text-slate-500 dark:text-slate-400"
          >{{ formatDuration(elapsedSeconds) }} elapsed</span
        >
        <span v-if="etaSeconds && etaSeconds > 0" class="text-slate-500 dark:text-slate-400"
          >• ≈ {{ formatDuration(etaSeconds) }} left</span
        >
      </div>
      <div class="w-full h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div
          class="h-full bg-blue-500 transition-all duration-500"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </div>

    <!-- End states -->
    <div
      v-else-if="trial.status === 'completed'"
      class="flex items-center gap-2 text-green-600 dark:text-green-400 font-medium text-xs"
    >
      <CircleCheckBig class="w-4 h-4" />
      Results ready
    </div>
    <div
      v-else-if="trial.status === 'failed'"
      class="flex items-center gap-2 text-red-600 dark:text-red-400 text-xs font-medium"
    >
      <AlertCircle class="w-4 h-4" />
      Failed — see details in Results
    </div>

    <!-- Actions -->
    <div
      class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200 dark:border-slate-700"
    >
      <div class="flex gap-2 flex-wrap">
        <BaseButton
          v-if="isActive && trial.status !== 'cancelled'"
          variant="warning"
          size="sm"
          @click.stop="emit('cancel', trial)"
        >
          Cancel
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click.stop="emit('view-results', trial)">
          Results
        </BaseButton>
        <BaseButton
          v-if="trial.status === 'completed'"
          variant="success"
          size="sm"
          @click.stop="emit('download', trial)"
        >
          Download
        </BaseButton>
      </div>
      <div class="flex gap-2 flex-wrap">
        <BaseButton variant="secondary" size="sm" @click.stop="emit('retry', trial)">
          Retry
        </BaseButton>
        <BaseButton variant="secondary" size="sm" @click.stop="emit('rename', trial)">
          Rename
        </BaseButton>
        <BaseButton variant="danger" size="sm" @click.stop="emit('delete', trial)">
          Delete
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { AlertCircle, CircleCheckBig } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { formatDuration, formatDateFull } from '@/utils/formatters'
import type { TrialSummary, Schema, Prompt } from '@/types'

const props = defineProps({
  trial: { type: Object as PropType<TrialSummary>, required: true },
  schemas: { type: Array as PropType<Schema[]>, required: true },
  prompts: { type: Array as PropType<Prompt[]>, required: true },
})

const emit = defineEmits<{
  rename: [trial: TrialSummary]
  delete: [trial: TrialSummary]
  retry: [trial: TrialSummary]
  download: [trial: TrialSummary]
  'view-results': [trial: TrialSummary]
  'view-schema': [trial: TrialSummary]
  'view-prompt': [trial: TrialSummary]
  cancel: [trial: TrialSummary]
}>()

const schema = computed(() => props.schemas.find((s) => s.id === props.trial.schema_id))
const prompt = computed(() => props.prompts.find((p) => p.id === props.trial.prompt_id))
// Prefer the name frozen in the trial snapshot (matches what actually ran);
// fall back to the live schema/prompt name for legacy trials without snapshots.
const schemaName = computed(
  () => props.trial.schema_snapshot?.schema_name || schema.value?.schema_name || '-',
)
const promptName = computed(() => props.trial.prompt_snapshot?.name || prompt.value?.name)

const isActive = computed(() => !['completed', 'failed', 'cancelled'].includes(props.trial.status))

const docsDone = computed(() => {
  if (props.trial.docs_done != null) return props.trial.docs_done
  if (props.trial.progress != null) {
    const total = props.trial.document_ids?.length ?? 0
    return Math.round((props.trial.progress || 0) * total)
  }
  return 0
})
const totalDocs = computed(() => props.trial.document_ids?.length ?? 0)
const progressPercent = computed(() =>
  props.trial.progress != null ? Math.round((props.trial.progress || 0) * 100) : 0,
)

const elapsedSeconds = computed(() =>
  props.trial.started_at ? (Date.now() - Date.parse(props.trial.started_at)) / 1000 : 0,
)
const etaSeconds = computed(() => props.trial.meta?.eta_seconds ?? 0)
</script>
