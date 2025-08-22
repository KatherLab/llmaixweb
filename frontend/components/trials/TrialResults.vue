<template>
  <teleport to="body">
    <transition name="fade">
      <div
        v-if="isModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
        @click="handleBackdropClick"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div
          class="relative bg-white rounded-3xl shadow-2xl max-w-8xl w-full max-h-[95vh] flex flex-col ring-1 ring-blue-100 overflow-hidden"
          @click.stop
        >
          <div class="flex items-center justify-between gap-4 px-8 py-6 border-b rounded-t-3xl bg-white/90">
            <h3 class="text-2xl font-bold tracking-tight text-gray-800">Trial Results</h3>
            <button
              @click="$emit('close')"
              class="text-gray-400 hover:text-blue-700 hover:bg-blue-50 rounded-full p-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close"
              autofocus
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="flex-1 overflow-y-auto p-8 bg-white/70">
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-16">
              <span class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mb-3"></span>
              <span class="mt-2 text-gray-500">Loading trial results…</span>
            </div>
            <div v-else-if="error" class="bg-red-50 border-l-4 border-red-400 p-5 mb-5 rounded-lg flex items-start gap-2">
              <svg class="h-6 w-6 mt-1 text-red-400" fill="none" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 00-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 101.4 1.4L10 11.4l1.3 1.3a1 1 0 001.4-1.4L11.4 10l1.3-1.3a1 1 0 00-1.4-1.4L10 8.6 8.7 7.3z" clip-rule="evenodd"/>
              </svg>
              <span class="text-sm text-red-700">{{ error }}</span>
            </div>
            <template v-else-if="trial">
              <!-- Enhanced Trial Information Card -->
              <div class="bg-gradient-to-br from-white via-blue-50 to-white shadow-inner rounded-xl p-6 mb-7 border border-gray-100">
                <div class="flex flex-col md:flex-row md:justify-between gap-6">
                  <!-- Trial Details Column -->
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <h2 class="text-xl font-bold text-blue-900 truncate">
                        {{ trial.name || `Trial #${trial.id}` }}
                      </h2>
                      <span v-if="trial.status"
                        class="ml-2 px-2 py-0.5 rounded-full text-xs font-semibold shadow"
                        :class="{
                          'bg-green-100 text-green-700': trial.status === 'completed',
                          'bg-blue-100 text-blue-700': trial.status === 'processing',
                          'bg-yellow-100 text-yellow-700': trial.status === 'pending',
                          'bg-red-100 text-red-700': trial.status === 'failed'
                        }"
                      >
                        {{ trial.status }}
                      </span>
                    </div>
                    <div v-if="trial.description" class="text-gray-700 text-sm mb-1">
                      {{ trial.description }}
                    </div>
                    <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600 mt-1">
                      <span>
                        <span class="font-semibold">Started:</span> {{ formatDate(trial.created_at, true) }}
                      </span>
                      <span>
                        <span class="font-semibold">Model:</span> {{ trial.llm_model }}
                      </span>
                      <span v-if="trial.prompt">
                        <span class="font-semibold">Prompt:</span>
                        <span class="text-gray-800">{{ trial.prompt.name || '[unnamed prompt]' }}</span>
                      </span>
                      <span v-if="trial.document_set">
                        <span class="font-semibold">Document Set:</span>
                        <span class="text-gray-800">{{ trial.document_set.name || ('Set #' + trial.document_set.id) }}</span>
                      </span>
                      <span>
                        <span class="font-semibold">Documents:</span> {{ trial.document_ids?.length || 0 }}
                      </span>
                    </div>
                  </div>

                  <!-- Advanced Options & Doc Count & Total Usage -->
                  <div class="flex flex-col items-start md:items-end gap-2 min-w-[200px]">
                    <span class="text-sm bg-blue-50 px-4 py-2 rounded-lg font-medium text-blue-800 shadow-sm">
                      {{ trial.results?.length || 0 }} documents processed
                    </span>
                    <!-- TOTAL USAGE BADGE -->
                    <span
                      v-if="totalUsage.total_tokens !== undefined"
                      class="text-xs bg-blue-100 px-3 py-1 rounded-lg font-semibold text-blue-800 mt-1"
                      title="Sum of prompt and completion tokens across all results"
                    >
                      Usage: {{ totalUsage.prompt_tokens || 0 }} prompt /
                      {{ totalUsage.completion_tokens || 0 }} completion /
                      <b>{{ totalUsage.total_tokens || 0 }}</b> total tokens
                    </span>
                    <div
                      v-if="trial.advanced_options && Object.keys(trial.advanced_options).length"
                      class="mt-2 bg-white rounded-lg border border-blue-100 px-4 py-2 shadow text-xs max-w-xs"
                    >
                      <div class="text-xs font-semibold text-blue-700 mb-1">LLM Advanced Options</div>
                      <ul>
                        <li
                          v-for="(value, key) in trial.advanced_options"
                          :key="key"
                          class="flex items-center gap-1 mb-0.5"
                        >
                          <span class="font-medium capitalize">{{ key.replace(/_/g, ' ') }}:</span>
                          <span class="text-blue-900">{{ value }}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="!trial.results || trial.results.length === 0" class="flex flex-col items-center justify-center py-16 bg-gray-50 rounded-lg border border-gray-200">
                <svg class="h-14 w-14 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span class="text-gray-500 mt-3">No results available for this trial.</span>
                <span v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-gray-400">Please wait for the trial to complete.</span>
              </div>
              <div v-else class="grid grid-cols-1 gap-5">
                <div
                  v-for="(result, index) in trial.results"
                  :key="index"
                  class="bg-white shadow border border-gray-100 rounded-xl transition-shadow hover:shadow-lg"
                >
                  <div
                    @click="toggleResultExpansion(index)"
                    class="cursor-pointer flex items-center justify-between px-6 py-4 border-b hover:bg-gray-50/70 transition-colors rounded-t-xl select-none"
                  >
                    <div class="flex flex-col gap-0.5">
                      <div class="flex items-center">
                        <span class="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center mr-3 text-base font-bold">{{ index + 1 }}</span>
                        <span class="font-medium text-gray-800">
                          {{ documentLabels[index]?.name || 'Loading document name...' }}
                        </span>
                      </div>
                      <span v-if="documentLabels[index]?.original && documentLabels[index]?.original !== documentLabels[index]?.name"
                            class="text-xs text-gray-400 italic ml-10 truncate max-w-xs">
                        (Original: {{ documentLabels[index].original }})
                      </span>
                    </div>
                    <svg
                      class="w-5 h-5 text-gray-400 transition-transform duration-200"
                      :class="{ 'rotate-180': expandedResults[index] }"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                  </div>
                  <div v-if="expandedResults[index]" class="p-6 bg-gradient-to-b from-white to-blue-50/20">
                    <div
                      class="flex gap-6"
                      :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
                    >
                      <div class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100">
                        <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
                          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          Document Content
                        </h4>
                        <div v-if="isMarkdown(documentContents[index])" class="markdown-content" v-html="renderMarkdown(documentContents[index])"></div>
                        <pre v-else class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContents[index] }}</pre>
                      </div>
                      <div class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100">
                        <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
                          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          Extracted Information
                        </h4>
                        <JsonViewer :data="result.result" />
                      </div>
                      <div v-if="showDocumentPanel[index]" class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100">
                        <h4 class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5">
                          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                          </svg>
                          Original Document
                        </h4>
                        <iframe v-if="documentPdfUrls[index]" :src="documentPdfUrls[index]" frameborder="0" width="100%" height="400px" class="rounded-md"></iframe>
                        <div v-else-if="documentPdfLoading[index]" class="text-center py-10">
                          <span class="inline-block animate-spin h-8 w-8 border-4 border-blue-400 border-t-transparent rounded-full"></span>
                          <span class="mt-2 text-gray-500 block">Loading PDF…</span>
                        </div>
                        <span v-else class="text-gray-500">Failed to load PDF</span>
                      </div>
                    </div>

                    <!-- Reasoning & Usage Panel -->
                    <div v-if="getReasoningContent(index) || getAdditionalContent(index)?.usage || getAdditionalContent(index)?.finish_reason" class="mt-6">
                      <button
                        @click="showReasoningPanel[index] = !showReasoningPanel[index]"
                        class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                      >
                        <svg :class="showReasoningPanel[index] ? 'rotate-90' : ''" class="h-4 w-4 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                        <span>
                          {{ showReasoningPanel[index] ? 'Hide' : 'Show' }} LLM Reasoning & Metadata
                        </span>
                      </button>
                      <div v-if="showReasoningPanel[index]" class="bg-blue-50/60 border border-blue-100 rounded-lg mt-3 p-5">
                        <div v-if="getReasoningContent(index)" class="mb-4">
                          <h5 class="font-semibold text-blue-800 mb-2">Reasoning</h5>
                          <div class="markdown-content" v-html="renderMarkdown(getReasoningContent(index))"></div>
                        </div>
                        <div v-if="getAdditionalContent(index)?.usage" class="mb-2">
                          <h5 class="font-semibold text-blue-800 mb-1">Token Usage</h5>
                          <ul class="text-xs text-blue-900 ml-2">
                            <li v-for="(v, k) in getAdditionalContent(index).usage" :key="k">
                              <span class="font-medium">{{ k.replace(/_/g, ' ') }}:</span> {{ v }}
                            </li>
                          </ul>
                        </div>
                        <div v-if="getAdditionalContent(index)?.finish_reason">
                          <h5 class="font-semibold text-blue-800 mb-1">Finish Reason</h5>
                          <span class="text-xs text-blue-900">{{ getAdditionalContent(index).finish_reason }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="mt-6 flex flex-wrap gap-3 justify-end">
                      <button
                        @click="toggleViewMode(index)"
                        class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
                        </svg>
                        {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
                      </button>
                      <button
                        @click="toggleDocumentPanel(index)"
                        class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path v-if="showDocumentPanel[index]" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268-2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                          <path v-else d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                          <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268-2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        </svg>
                        {{ showDocumentPanel[index] ? 'Hide Original Document' : 'View Original Document' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="flex flex-col items-center justify-center py-16">
              <svg class="h-14 w-14 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span class="text-gray-500 mt-3">Trial not found</span>
              <button @click="$emit('close')" class="mt-6 inline-block px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors duration-150 shadow">
                Return to trials
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>



<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/services/api.js';
import { formatDate } from '@/utils/formatters.js';
import { useToast } from 'vue-toastification';
import JsonViewer from '../JsonViewer.vue';
import { marked } from 'marked';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  trialId: {
    type: [String, Number],
    required: true
  },
  isModal: {
    type: Boolean,
    default: false
  }
});

defineEmits(['close']);

const route = useRoute();
const router = useRouter();
const toast = useToast();

const trialId = computed(() => props.trialId || parseInt(route.params.trialId));
const isLoading = ref(true);
const error = ref(null);
const trial = ref(null);
const selectedResultIndex = ref(0);

const expandedResults = ref({});
const documentContents = ref({});
const documentNames = ref({});
const documentLabels = ref({});
const viewMode = ref({});
const documentPdfUrls = ref({});
const documentPdfLoading = ref({});
const showDocumentPanel = ref({});
const showReasoningPanel = ref({}); // For reasoning/metadata accordion

const renderMarkdown = (text) => {
  try {
    return marked(text);
  } catch (e) {
    return text;
  }
};

const isMarkdown = (text) => {
  if (!text) return false;
  try {
    return text.includes('#') ||
           text.includes('**') ||
           text.includes('*') ||
           text.includes('[') ||
           text.includes('```') ||
           /\n\s*-\s/.test(text) ||
           /\n\s*\d+\.\s/.test(text);
  } catch (e) {
    return false;
  }
};

// Helper to parse additional_content (may be JSON string or object)
const getAdditionalContent = (index) => {
  const result = trial.value?.results?.[index];
  if (!result || !result.additional_content) return null;
  if (typeof result.additional_content === 'string') {
    try { return JSON.parse(result.additional_content); } catch { return null; }
  }
  return result.additional_content;
};
// Helper for reasoning content
const getReasoningContent = (index) => {
  const ac = getAdditionalContent(index);
  if (!ac) return null;
  return ac.reasoning_content || null;
};

// Compute total token usage for the trial
const totalUsage = computed(() => {
  const usageTotals = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
  if (!trial.value?.results?.length) return usageTotals;

  for (const result of trial.value.results) {
    let ac = result.additional_content;
    if (!ac) continue;
    if (typeof ac === 'string') {
      try { ac = JSON.parse(ac); } catch { continue; }
    }
    if (!ac.usage) continue;
    // Accept numbers or strings for tokens, fallback to 0
    for (const key of ['prompt_tokens', 'completion_tokens', 'total_tokens']) {
      if (ac.usage[key] !== undefined) {
        usageTotals[key] += Number(ac.usage[key]) || 0;
      }
    }
  }
  return usageTotals;
});

// Fetch trial data
const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await api.get(`/project/${props.projectId}/trial/${trialId.value}`);
    trial.value = response.data;
    if (trial.value?.document_ids) {
      loadDocumentNames();
    }
  } catch (err) {
    console.error('Error loading trial data:', err);
    error.value = err.message || 'Failed to load trial data';
  } finally {
    isLoading.value = false;
  }
};

// Load document names
const loadDocumentNames = async () => {
  if (!trial.value?.document_ids) return;
  for (let i = 0; i < trial.value.document_ids.length; i++) {
    try {
      const docId = trial.value.document_ids[i];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      const doc = response.data;
      documentLabels.value[i] = {
        name: doc.document_name || doc.original_file?.file_name || `Document ${docId}`,
        original: doc.original_file?.file_name || '',
      };
    } catch (err) {
      console.error(`Error loading document label for index ${i}:`, err);
      documentLabels.value[i] = {
        name: `Document (ID: ${trial.value.document_ids[i]})`,
        original: '',
      };
    }
  }
};

const goBack = () => {
  if (props.isModal) {
    $emit('close');
  } else {
    router.push(`/projects/${props.projectId}/trials`);
  }
};

const toggleResultExpansion = async (index) => {
  expandedResults.value[index] = !expandedResults.value[index];
  if (viewMode.value[index] === undefined) {
    viewMode.value[index] = 'horizontal';
  }
  if (expandedResults.value[index] && !documentContents.value[index]) {
    try {
      const docId = trial.value.document_ids[index];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      documentContents.value[index] = response.data.text || 'No text content available';
    } catch (err) {
      documentContents.value[index] = 'Error loading document content';
      console.error(err);
    }
  }
};

const toggleViewMode = (index) => {
  viewMode.value[index] = viewMode.value[index] === 'vertical' ? 'horizontal' : 'vertical';
};

const toggleDocumentPanel = async (index) => {
  showDocumentPanel.value[index] = !showDocumentPanel.value[index];
  if (showDocumentPanel.value[index] && !documentPdfUrls.value[index] && !documentPdfLoading.value[index]) {
    documentPdfLoading.value[index] = true;
    try {
      const docId = trial.value.document_ids[index];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      const document = response.data;
      let fileId;
      if (document.preprocessed_file_id && document.preprocessed_file.file_type === 'application/pdf') {
        fileId = document.preprocessed_file_id;
      } else if (['application/pdf', 'image/png', 'image/jpeg'].includes(document.original_file.file_type)) {
        fileId = document.original_file_id;
      }
      if (fileId) {
        const fileResponse = await api.get(`/project/${props.projectId}/file/${fileId}/content?preview=true`, {
          responseType: 'blob'
        });
        const blob = new Blob([fileResponse.data], { type: fileResponse.headers['content-type'] });
        documentPdfUrls.value[index] = URL.createObjectURL(blob);
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to load document");
    } finally {
      documentPdfLoading.value[index] = false;
    }
  }
};

watch(() => props.isModal, (v) => {
  if (v) document.body.style.overflow = 'hidden';
  else document.body.style.overflow = '';
});

onMounted(() => {
  fetchData();
  if (props.isModal) document.body.style.overflow = 'hidden';
});
onUnmounted(() => {
  document.body.style.overflow = '';
});
</script>

<style>
.json-viewer {
  font-family: monospace;
  font-size: 14px;
}
.json-item { margin: 2px 0; }
.json-key { cursor: pointer; display: flex; align-items: flex-start; }
.toggle-icon { width: 16px; display: inline-block; }
.key-name { color: #881391; margin-right: 5px; }
.json-value { color: #1a1aa6; }
.json-children { border-left: 1px dashed #ccc; padding-left: 1rem; }
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
.markdown-content {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #333;
}
.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
}
.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.25em; }
.markdown-content h3 { font-size: 1.125em; }
.markdown-content p { margin-bottom: 1em; }
.markdown-content ul,
.markdown-content ol { margin-bottom: 1em; padding-left: 1.5em; }
.markdown-content li { margin-bottom: 0.25em; }
.markdown-content code {
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 85%;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
}
.markdown-content pre {
  background-color: #f6f8fa;
  border-radius: 3px;
  padding: 1em;
  overflow: auto;
  margin-bottom: 1em;
}
.markdown-content pre code { background-color: transparent; padding: 0; }
.markdown-content a { color: #0366d6; text-decoration: none; }
.markdown-content a:hover { text-decoration: underline; }
.markdown-content img { max-width: 100%; }
.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}
.markdown-content table th,
.markdown-content table td {
  border: 1px solid #ddd;
  padding: 0.5em;
}
.markdown-content table th { background-color: #f6f8fa; font-weight: 600; }
.markdown-content blockquote {
  border-left: 4px solid #dfe2e5;
  padding-left: 1em;
  color: #6a737d;
  margin: 0 0 1em;
}
</style>
