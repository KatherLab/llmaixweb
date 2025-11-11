<template>
  <div
    class="group border border-gray-200 bg-white rounded-xl shadow hover:shadow-lg transition relative flex flex-col min-h-[220px]"
    :class="{ 'ring-2 ring-blue-500': selected }"
  >
    <button
      class="absolute top-4 right-4 z-10 bg-white border border-gray-300 rounded-full p-2 shadow-sm hover:ring-2 ring-blue-500 transition"
      @click.stop="toggleSelect"
      :aria-label="selected ? 'Deselect' : 'Select'"
    >
      <svg v-if="selected" class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-7.364 7.364a1 1 0 01-1.415 0L3.293 10.707a1 1 0 011.414-1.414l3.222 3.221 6.657-6.657a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>
      <svg v-else class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
    </button>

    <div class="flex-1 p-6 flex flex-col">
      <div class="flex items-start justify-between gap-3 mb-2">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-semibold text-lg truncate block">{{ trial.name || `Trial #${trial.id}` }}</span>
            <span :class="['text-xs px-2 py-1 rounded-full font-medium', statusClass]">{{ trial.status }}</span>
          </div>
          <div class="text-xs text-gray-400 mt-0.5" v-if="trial.last_result_at">
            Last result: {{ formatDate(trial.last_result_at) }}
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="text-[11px] bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full font-medium" title="Processed results">
            {{ trial.results_count || 0 }} res
          </span>
          <span v-if="trial.error_count && trial.error_count > 0" class="text-[11px] bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-semibold" title="Documents with errors">
            {{ trial.error_count }} err
          </span>
        </div>
      </div>

      <div class="text-sm text-gray-600 truncate mb-1" v-if="trial.description">
        {{ trial.description }}
      </div>

      <div class="flex flex-wrap gap-2 text-xs text-gray-500 mb-2">
        <span><strong>Schema:</strong> {{ schema?.schema_name || '-' }}</span>
        <span v-if="prompt"><strong>Prompt:</strong> {{ prompt.name }}</span>
        <span><strong>LLM:</strong> {{ trial.llm_model }}</span>
        <span><strong>Started:</strong> {{ formatDate(trial.created_at) }}</span>
        <span v-if="trial.documents_count != null"><strong>Docs:</strong> {{ trial.documents_count }}</span>
      </div>

      <!-- Progress -->
      <div v-if="isActive" class="flex flex-col gap-1 mt-2">
        <div class="flex items-center gap-2 text-xs">
          <span class="font-medium text-blue-600">{{ docsDone }}/{{ totalDocs }} docs</span>
          <span class="text-gray-500">{{ pretty(elapsedSeconds) }} elapsed</span>
          <span v-if="etaSeconds && etaSeconds > 0" class="text-gray-500">• ≈ {{ pretty(etaSeconds) }} left</span>
        </div>
        <div class="w-full h-1 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full bg-blue-500 transition-all duration-500" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>

      <!-- Compact end state -->
      <div v-else-if="trial.status === 'completed'" class="mt-2 flex items-center gap-2 text-green-600 font-medium text-xs">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Results ready
      </div>
      <div v-else-if="trial.status === 'failed'" class="mt-2 flex items-center gap-2 text-red-600 text-xs font-medium">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        Failed — see details in Results
      </div>
    </div>

    <!-- Footer -->
    <div class="border-t bg-gray-50 px-4 py-3 flex items-center justify-between rounded-b-xl gap-2">
      <div class="flex gap-2 flex-wrap">
        <button
          v-if="isActive && trial.status !== 'cancelled'"
          @click.stop="emit('cancel', trial)"
          class="rounded-md bg-yellow-100 text-yellow-700 px-3 py-1 text-xs font-medium hover:bg-yellow-200 transition"
        >Cancel</button>

        <button
          @click.stop="emit('view-results', trial)"
          class="rounded-md bg-blue-600 text-white px-3 py-1 text-xs font-medium hover:bg-blue-700 transition">
          Results
        </button>

        <button @click.stop="emit('view-schema', trial)" class="rounded-md border border-gray-300 text-gray-700 px-3 py-1 text-xs font-medium hover:bg-gray-100 transition">
          Schema
        </button>
        <button @click.stop="emit('view-prompt', trial)" class="rounded-md border border-gray-300 text-gray-700 px-3 py-1 text-xs font-medium hover:bg-gray-100 transition">
          Prompt
        </button>

        <button
          v-if="trial.status === 'completed'"
          @click.stop="emit('download', trial)"
          class="rounded-md bg-green-600 text-white px-3 py-1 text-xs font-medium hover:bg-green-700 transition">
          Download
        </button>
      </div>

      <div class="flex gap-2 flex-wrap">
        <button @click.stop="emit('retry', trial)" class="rounded-md bg-gray-100 text-gray-700 px-3 py-1 text-xs font-medium hover:bg-gray-200 transition">
          Retry
        </button>
        <button @click.stop="emit('rename', trial)" class="rounded-md bg-purple-100 text-purple-700 px-3 py-1 text-xs font-medium hover:bg-purple-200 transition">
          Rename
        </button>
        <button @click.stop="emit('delete', trial)" class="rounded-md bg-red-100 text-red-700 px-3 py-1 text-xs font-medium hover:bg-red-200 transition">
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  trial:   { type: Object, required: true },
  schemas: { type: Array,  required: true },
  prompts: { type: Array,  required: true },
  selected: Boolean,
});
const emit = defineEmits(['select','rename','delete','retry','download','view-results','view-schema','view-prompt','cancel']);

const schema = computed(() => props.schemas.find(s => s.id === props.trial.schema_id));
const prompt = computed(() => props.prompts.find(p => p.id === props.trial.prompt_id));

const statusClass = computed(() => ({
  pending:    'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed:  'bg-green-100 text-green-800',
  failed:     'bg-red-100 text-red-800',
  cancelled:  'bg-gray-200 text-gray-500',
}[props.trial.status] || 'bg-gray-100 text-gray-800'));

const isActive = computed(() => !['completed', 'failed', 'cancelled'].includes(props.trial.status));

const docsDone = computed(() => {
  if (props.trial.docs_done != null) return props.trial.docs_done;
  if (props.trial.progress != null) {
    const total = props.trial.document_ids?.length ?? 0;
    return Math.round((props.trial.progress || 0) * total);
  }
  return 0;
});
const totalDocs = computed(() => props.trial.document_ids?.length ?? 0);
const progressPercent = computed(() => props.trial.progress != null ? Math.round((props.trial.progress || 0) * 100) : 0);

const elapsedSeconds = computed(() => props.trial.started_at ? (Date.now() - Date.parse(props.trial.started_at)) / 1000 : 0);
const etaSeconds = computed(() => props.trial.meta?.eta_seconds ?? 0);

function pretty(sec) { if (!sec || isNaN(sec)) return "00:00:00"; return new Date(sec * 1000).toISOString().substring(11, 19); }
function formatDate(dateString) { if (!dateString) return "-"; return new Date(dateString).toLocaleString(); }
function toggleSelect() { emit('select', props.trial.id); }
</script>
