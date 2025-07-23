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
      <div class="flex items-center gap-3 mb-2">
        <span class="font-semibold text-lg truncate block">{{ trial.name || `Trial #${trial.id}` }}</span>
        <span :class="['text-xs px-2 py-1 rounded-full font-medium', statusClass]">
          {{ trial.status }}
        </span>
      </div>
      <div class="text-sm text-gray-600 truncate mb-1" v-if="trial.description">
        {{ trial.description }}
      </div>
      <div class="flex flex-wrap gap-2 text-xs text-gray-500 mb-2">
        <span><strong>Schema:</strong> {{ schema?.schema_name || '-' }}</span>
        <span v-if="prompt"><strong>Prompt:</strong> {{ prompt.name }}</span>
        <span><strong>LLM:</strong> {{ trial.llm_model }}</span>
        <!--<span><strong>Docs:</strong> {{ trial.document_ids?.length || 0 }}</span>-->
        <span><strong>Started:</strong> {{ formatDate(trial.created_at) }}</span>
      </div>
      <div v-if="isActive" class="flex items-center gap-2 mt-2">
        <span class="text-xs text-blue-600 font-medium">Processing</span>
        <span class="text-xs text-gray-500">{{ progressPercent }}%</span>
        <div class="w-full h-1 bg-gray-200 rounded-full overflow-hidden flex-1">
          <div class="h-full bg-blue-500 transition-all duration-500" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>
      <div v-else-if="trial.status === 'failed'" class="mt-2 flex items-center gap-2 text-red-600 font-medium text-xs">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        Failed
      </div>
      <div v-else-if="trial.results && trial.results.length > 0" class="mt-2 flex items-center gap-2 text-green-600 font-medium text-xs">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        {{ trial.results.length }} results
      </div>
    </div>
    <div class="border-t bg-gray-50 px-4 py-3 flex items-center justify-between rounded-b-xl gap-2">
      <div class="flex gap-2 flex-wrap">
        <button @click.stop="emit('view-results', trial)" v-if="trial.results && trial.results.length > 0"
          class="rounded-md bg-blue-600 text-white px-3 py-1 text-xs font-medium hover:bg-blue-700 transition">
          Results
        </button>
        <button @click.stop="emit('view-schema', trial)" class="rounded-md border border-gray-300 text-gray-700 px-3 py-1 text-xs font-medium hover:bg-gray-100 transition">
          Schema
        </button>
        <button @click.stop="emit('view-prompt', trial)" class="rounded-md border border-gray-300 text-gray-700 px-3 py-1 text-xs font-medium hover:bg-gray-100 transition">
          Prompt
        </button>
        <button @click.stop="emit('download', trial)" v-if="trial.results && trial.results.length > 0"
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
  trial: { type: Object, required: true },
  schemas: { type: Array, required: true },
  prompts: { type: Array, required: true },
  selected: Boolean,
});
const emit = defineEmits(['select', 'rename', 'delete', 'retry', 'download', 'view-results', 'view-schema', 'view-prompt']);

const schema = computed(() => props.schemas.find(s => s.id === props.trial.schema_id));
const prompt = computed(() => props.prompts.find(p => p.id === props.trial.prompt_id));

const statusClass = computed(() => ({
  'pending': 'bg-yellow-100 text-yellow-800',
  'processing': 'bg-blue-100 text-blue-800',
  'completed': 'bg-green-100 text-green-800',
  'failed': 'bg-red-100 text-red-800'
}[props.trial.status] || 'bg-gray-100 text-gray-800'));

const isActive = computed(() => !['completed', 'failed'].includes(props.trial.status));
const progressPercent = computed(() =>
  props.trial.progress != null ? Math.round(props.trial.progress * 100) : (isActive.value ? 25 : 0)
);
function formatDate(dateString) {
  return new Date(dateString).toLocaleString();
}
function toggleSelect() {
  emit('select', props.trial.id);
}
</script>
