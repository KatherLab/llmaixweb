<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';

const props = defineProps({
  open: Boolean,
  trial: Object,
  projectId: [String, Number]
});
const emit = defineEmits(['close']);

const format = ref('json');
const includeContent = ref(true);

const isDownloading = ref(false);
const toast = useToast();

const isJsonZip = computed(() => format.value === 'json');
const isCsvZip = computed(() => format.value === 'csv' && includeContent.value);
const isCsvOnly = computed(() => format.value === 'csv' && !includeContent.value);
const fileExt = computed(() => isCsvOnly.value ? 'csv' : 'zip');

function lockBodyScroll() { document.body.style.overflow = 'hidden'; }
function unlockBodyScroll() { document.body.style.overflow = ''; }

watch(() => props.open, (open) => {
  if (open) {
    format.value = 'json';
    includeContent.value = true;
    lockBodyScroll();
  } else {
    unlockBodyScroll();
  }
});
onMounted(() => { if (props.open) lockBodyScroll(); });
onBeforeUnmount(unlockBodyScroll);

async function download() {
  if (isDownloading.value) return;
  isDownloading.value = true;
  try {
    const resp = await api.get(
      `/project/${props.projectId}/trial/${props.trial.id}/download?format=${format.value}&include_content=${includeContent.value}`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([resp.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `trial_${props.trial.id}_results.${fileExt.value}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    toast.success('Downloaded!');
    emit('close');
  } catch (e) {
    toast.error('Download failed');
  } finally {
    isDownloading.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center"
      style="backdrop-filter: blur(8px); background: rgba(30,30,40,0.27);"
      @click.self="$emit('close')"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 flex flex-col max-h-[80vh] overflow-auto">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Download Trial Results</h3>

        <div class="mb-4 flex items-center gap-2 text-xs text-gray-600 bg-gray-50 rounded px-3 py-2 border border-gray-100">
          <svg class="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 16h-1v-4h-1m1 4v1m6-5a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span v-if="isJsonZip">
            <strong>JSON (per-document):</strong> Downloads a <b>ZIP archive</b> with one JSON file per document.
            <span class="block">
              Each file includes all extracted results, full document metadata, preprocessing configuration, and trial configuration.
            </span>
          </span>
          <span v-else-if="isCsvZip">
            <strong>CSV (with files):</strong> Downloads a <b>ZIP archive</b> with the CSV and attached files.
            <span class="block">
              The CSV includes all extracted results, full document metadata, preprocessing configuration, and trial configuration.
            </span>
          </span>
          <span v-else>
            <strong>CSV (flat):</strong> Downloads a single CSV file, one row per document.<br>
            Includes all extracted results, document metadata, preprocessing configuration, and trial configuration.
          </span>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Format</label>
          <select v-model="format" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option value="json">JSON (per-document, ZIP)</option>
            <option value="csv">CSV (table, with optional files)</option>
          </select>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Options</label>
          <label class="flex items-center text-sm">
            <input
              type="checkbox"
              v-model="includeContent"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span class="ml-2">Include document content
              <span class="text-gray-400" title="If checked: you will also receive the original document text and files inside the ZIP.">
                (adds document text and source files)
              </span>
            </span>
          </label>
        </div>

        <div v-if="format === 'csv'" class="mb-3 text-xs text-gray-500">
          <span v-if="includeContent">
            Will include original files and full document text inside a ZIP.<br>
            <b>Note:</b> Download may be large if your trial contains many files.
          </span>
          <span v-else>
            Only a single CSV will be downloaded (no files/text included).
          </span>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button @click="$emit('close')" class="px-4 py-2 rounded bg-gray-100 hover:bg-gray-200 text-gray-700">
            Cancel
          </button>
          <button
            :disabled="isDownloading"
            class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-2"
            @click="download"
          >
            <svg v-if="isDownloading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            {{ isDownloading ? 'Downloading...' : 'Download' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
