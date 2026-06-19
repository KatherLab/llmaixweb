<template>
  <div
    :id="`trial-card-${trial.id}`"
    class="group border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 rounded-xl shadow hover:shadow-lg dark:hover:shadow-xl transition relative flex flex-col min-h-[220px]"
    :class="{
      'ring-2 ring-blue-500': selected,
      'ring-2 ring-emerald-500 bg-emerald-50 dark:bg-emerald-900/20': highlighted,
    }"
  >
    <button
      class="absolute top-4 right-4 z-10 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 rounded-full p-2 shadow-sm hover:ring-2 ring-blue-500 transition"
      :aria-label="selected ? 'Deselect' : 'Select'"
      @click.stop="toggleSelect"
    >
      <svg v-if="selected" class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
        <path
          fill-rule="evenodd"
          d="M16.707 5.293a1 1 0 010 1.414l-7.364 7.364a1 1 0 01-1.415 0L3.293 10.707a1 1 0 011.414-1.414l3.222 3.221 6.657-6.657a1 1 0 011.414 0z"
          clip-rule="evenodd"
        />
      </svg>
      <svg
        v-else
        class="w-5 h-5 text-gray-400 dark:text-gray-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <circle cx="12" cy="12" r="10" stroke-width="2" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
    </button>

    <div class="flex-1 p-6 flex flex-col">
      <div class="flex items-start justify-between gap-3 mb-2">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-semibold text-lg text-gray-900 dark:text-white truncate block">{{
              trial.name || `Trial #${trial.id}`
            }}</span>
            <span :class="['text-xs px-2 py-1 rounded-full font-medium', statusClass]">{{
              trial.status
            }}</span>
          </div>
          <div v-if="trial.last_result_at" class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
            Last result: {{ formatDate(trial.last_result_at) }}
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span
            class="text-[11px] bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded-full font-medium"
            title="Processed results"
          >
            {{ trial.results_count || 0 }} res
          </span>
          <span
            v-if="trial.error_count && trial.error_count > 0"
            class="text-[11px] bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-2 py-0.5 rounded-full font-semibold"
            title="Documents with errors"
          >
            {{ trial.error_count }} err
          </span>
        </div>
      </div>

      <div v-if="trial.description" class="text-sm text-gray-600 dark:text-gray-400 truncate mb-1">
        {{ trial.description }}
      </div>

      <div class="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
        <span><strong>Schema:</strong> {{ schemaName }}</span>
        <span v-if="promptName"><strong>Prompt:</strong> {{ promptName }}</span>
        <span><strong>LLM:</strong> {{ trial.llm_model }}</span>
        <span><strong>Started:</strong> {{ formatDate(trial.created_at) }}</span>
        <span v-if="trial.documents_count != null"
          ><strong>Docs:</strong> {{ trial.documents_count }}</span
        >
      </div>

      <!-- Progress -->
      <div v-if="isActive" class="flex flex-col gap-1 mt-2">
        <div class="flex items-center gap-2 text-xs">
          <span class="font-medium text-blue-600 dark:text-blue-400"
            >{{ docsDone }}/{{ totalDocs }} docs</span
          >
          <span class="text-gray-500 dark:text-gray-400">{{ pretty(elapsedSeconds) }} elapsed</span>
          <span v-if="etaSeconds && etaSeconds > 0" class="text-gray-500 dark:text-gray-400"
            >• ≈ {{ pretty(etaSeconds) }} left</span
          >
        </div>
        <div class="w-full h-1 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 transition-all duration-500"
            :style="{ width: progressPercent + '%' }"
          ></div>
        </div>
      </div>

      <!-- Compact end state -->
      <div
        v-else-if="trial.status === 'completed'"
        class="mt-2 flex items-center gap-2 text-green-600 dark:text-green-400 font-medium text-xs"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        Results ready
      </div>
      <div
        v-else-if="trial.status === 'failed'"
        class="mt-2 flex items-center gap-2 text-red-600 dark:text-red-400 text-xs font-medium"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        Failed — see details in Results
      </div>
    </div>

    <!-- Footer -->
    <div
      class="border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 px-4 py-3 flex items-center justify-between rounded-b-xl gap-2"
    >
      <div class="flex gap-2 flex-wrap">
        <button
          v-if="isActive && trial.status !== 'cancelled'"
          class="rounded-md bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-3 py-1 text-xs font-medium hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition"
          @click.stop="emit('cancel', trial)"
        >
          Cancel
        </button>

        <button
          class="rounded-md bg-blue-600 text-white px-3 py-1 text-xs font-medium hover:bg-blue-700 dark:hover:bg-blue-800 transition"
          @click.stop="emit('view-results', trial)"
        >
          Results
        </button>

        <button
          class="rounded-md border border-gray-300 dark:border-slate-700 text-gray-700 dark:text-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-100 dark:hover:bg-slate-700 transition"
          @click.stop="emit('view-schema', trial)"
        >
          Schema
        </button>
        <button
          class="rounded-md border border-gray-300 dark:border-slate-700 text-gray-700 dark:text-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-100 dark:hover:bg-slate-700 transition"
          @click.stop="emit('view-prompt', trial)"
        >
          Prompt
        </button>

        <button
          v-if="trial.status === 'completed'"
          class="rounded-md bg-green-600 text-white px-3 py-1 text-xs font-medium hover:bg-green-700 dark:hover:bg-green-800 transition"
          @click.stop="emit('download', trial)"
        >
          Download
        </button>
      </div>

      <div class="flex gap-2 flex-wrap">
        <button
          class="rounded-md bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-200 dark:hover:bg-slate-600 transition"
          @click.stop="emit('retry', trial)"
        >
          Retry
        </button>
        <button
          class="rounded-md bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-3 py-1 text-xs font-medium hover:bg-purple-200 dark:hover:bg-purple-900/50 transition"
          @click.stop="emit('rename', trial)"
        >
          Rename
        </button>
        <button
          class="rounded-md bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-3 py-1 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/50 transition"
          @click.stop="emit('delete', trial)"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  trial: { type: Object, required: true },
  schemas: { type: Array, required: true },
  prompts: { type: Array, required: true },
  selected: Boolean,
  highlighted: Boolean,
})
const emit = defineEmits([
  'select',
  'rename',
  'delete',
  'retry',
  'download',
  'view-results',
  'view-schema',
  'view-prompt',
  'cancel',
])

const schema = computed(() => props.schemas.find((s) => s.id === props.trial.schema_id))
const prompt = computed(() => props.prompts.find((p) => p.id === props.trial.prompt_id))
// Prefer the name frozen in the trial snapshot (matches what actually ran);
// fall back to the live schema/prompt name for legacy trials without snapshots.
const schemaName = computed(
  () => props.trial.schema_snapshot?.schema_name || schema.value?.schema_name || '-',
)
const promptName = computed(() => props.trial.prompt_snapshot?.name || prompt.value?.name)

const statusClass = computed(
  () =>
    ({
      pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
      processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
      completed: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
      failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
      cancelled: 'bg-gray-200 dark:bg-slate-700 text-gray-500 dark:text-gray-400',
    })[props.trial.status] || 'bg-gray-100 dark:bg-slate-700 text-gray-800 dark:text-gray-400',
)

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

function pretty(sec) {
  if (!sec || isNaN(sec)) return '00:00:00'
  return new Date(sec * 1000).toISOString().substring(11, 19)
}
function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}
function toggleSelect() {
  emit('select', props.trial.id)
}
</script>
