<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 overflow-hidden bg-black/30 backdrop-blur-md transition-opacity"
      @click="emit('close')"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0"></div>

      <!-- Panel -->
      <div class="absolute inset-0 flex justify-end">
        <div class="w-screen max-w-md panel-slide-enter">
          <div class="h-full flex flex-col bg-white shadow-xl" @click.stop>
            <!-- Panel Header -->
            <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 class="text-lg font-semibold text-gray-900">Configure Preprocessing</h3>
              <button class="text-gray-400 hover:text-gray-600" @click="emit('close')">
                <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <!-- Panel Content -->
            <div class="flex-1 overflow-y-auto p-6 space-y-6">
              <!-- Selected Files -->
              <div>
                <h4 class="text-sm font-medium text-gray-700 mb-3">
                  Files to Process ({{ selectedFiles.length }})
                </h4>
                <div
                  class="space-y-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3"
                >
                  <div
                    v-for="fileId in selectedFiles"
                    :key="fileId"
                    class="flex items-center justify-between text-sm"
                  >
                    <span class="truncate">{{ getFileById(fileId)?.file_name || 'Unknown' }}</span>
                    <button
                      class="text-gray-400 hover:text-red-500"
                      @click="emit('remove-file', fileId)"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
                <button
                  class="mt-2 text-xs text-blue-600 hover:text-blue-800 font-medium"
                  @click="emit('clear-and-close')"
                >
                  Select different files
                </button>
              </div>

              <!-- OCR Engine Selection -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-3"> OCR Engine </label>
                <div class="space-y-3">
                  <!-- Local OCR -->
                  <button
                    v-if="doclingOcrEnabled"
                    :class="[
                      'w-full rounded-lg border-2 p-4 text-left transition-all',
                      selectedEngine === 'docling_tesseract'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300',
                    ]"
                    @click="selectedEngine = 'docling_tesseract'"
                  >
                    <div class="flex items-center">
                      <svg
                        class="w-6 h-6 text-blue-600 mr-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                      <div>
                        <p class="font-medium text-gray-900">
                          {{ getEngineLabel('docling_tesseract') }}
                        </p>
                        <p class="text-xs text-gray-500">
                          {{ getEngineSubtitle('docling_tesseract') }}
                        </p>
                      </div>
                    </div>
                  </button>

                  <!-- Mistral OCR -->
                  <button
                    v-if="mistralOcrEnabled"
                    :class="[
                      'w-full rounded-lg border-2 p-4 text-left transition-all',
                      selectedEngine === 'mistral_ocr'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300',
                    ]"
                    @click="selectedEngine = 'mistral_ocr'"
                  >
                    <div class="flex items-center">
                      <svg
                        class="w-6 h-6 text-blue-600 mr-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <div>
                        <p class="font-medium text-gray-900">
                          {{ getEngineLabel('mistral_ocr') }}
                        </p>
                        <p class="text-xs text-gray-500">
                          {{ getEngineSubtitle('mistral_ocr') }}
                        </p>
                      </div>
                    </div>
                  </button>

                  <!-- Vision LLM -->
                  <button
                    v-if="visionOcrEnabled"
                    :class="[
                      'w-full rounded-lg border-2 p-4 text-left transition-all',
                      selectedEngine === 'llm_vision'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300',
                    ]"
                    @click="selectedEngine = 'llm_vision'"
                  >
                    <div class="flex items-center">
                      <svg
                        class="w-6 h-6 text-blue-600 mr-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                        />
                      </svg>
                      <div>
                        <p class="font-medium text-gray-900">
                          {{ getEngineLabel('llm_vision') }}
                        </p>
                        <p class="text-xs text-gray-500">{{ getEngineSubtitle('llm_vision') }}</p>
                      </div>
                    </div>
                  </button>
                </div>
                <!-- Warning: No OCR engines enabled -->
                <div
                  v-if="noOcrEnabled"
                  class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                >
                  <p class="text-sm font-medium text-amber-900">
                    ⚠️ All OCR engines are disabled. Only PDFs with embedded text can be processed.
                  </p>
                  <p class="text-xs text-amber-700 mt-1">
                    Image files (PNG/JPEG) require OCR. Enable Local OCR, Mistral OCR, or Vision LLM
                    in Admin Settings to process images. PDFs will use pypdf for embedded text
                    extraction.
                  </p>
                </div>
              </div>

              <!-- Force OCR (always visible) -->
              <div class="border-t border-gray-200 pt-4">
                <label
                  class="flex items-start space-x-3 p-3 bg-amber-50 rounded-lg border border-amber-200"
                >
                  <input v-model="forceOcr" type="checkbox" class="mt-0.5 text-amber-600 rounded" />
                  <div>
                    <p class="text-sm font-medium text-amber-900">Force OCR for PDFs</p>
                    <p class="text-xs text-amber-700 mt-1">
                      Skip embedded text extraction and run OCR on all PDF pages
                    </p>
                  </div>
                </label>
              </div>

              <!-- Vision LLM Prompt (always visible when using Vision LLM) -->
              <div v-if="selectedEngine === 'llm_vision'" class="pt-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
                <textarea
                  v-model="visionPrompt"
                  rows="2"
                  placeholder="Extract all text as markdown..."
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>

              <!-- Advanced Options -->
              <div class="border-t border-gray-200 pt-4">
                <button
                  class="text-sm font-medium text-gray-700 flex items-center"
                  @click="showAdvanced = !showAdvanced"
                >
                  <svg
                    :class="['w-4 h-4 mr-2 transition-transform', showAdvanced ? 'rotate-90' : '']"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                  Advanced Options
                </button>

                <div v-show="showAdvanced" class="mt-4 space-y-4">
                  <!-- Tesseract Language -->
                  <div v-if="selectedEngine === 'docling_tesseract'">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      Tesseract Language
                    </label>
                    <select
                      v-model="tesseractLang"
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="eng">English</option>
                      <option value="deu">German</option>
                      <option value="fra">French</option>
                      <option value="spa">Spanish</option>
                      <option value="ita">Italian</option>
                      <option value="por">Portuguese</option>
                      <option value="nld">Dutch</option>
                      <option value="pol">Polish</option>
                      <option value="rus">Russian</option>
                      <option value="chi-sim">Chinese (Simplified)</option>
                      <option value="lat">Latin</option>
                    </select>
                  </div>

                  <!-- Mistral Settings -->
                  <div v-if="selectedEngine === 'mistral_ocr'" class="space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                      <input
                        v-model="mistralApiKey"
                        type="text"
                        placeholder="Leave empty to use server default"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                      <input
                        v-model="mistralModel"
                        type="text"
                        placeholder="mistral-ocr-latest"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <!-- Vision LLM Advanced Settings -->
                  <div v-if="selectedEngine === 'llm_vision'" class="space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                      <input
                        v-model="visionApiKey"
                        type="text"
                        placeholder="Leave empty to use server default"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                      <input
                        v-model="visionBaseUrl"
                        type="text"
                        placeholder="https://api.openai.com/v1"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                      <input
                        v-model="visionModel"
                        type="text"
                        placeholder="Leave empty to use server default"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Max Image Dimension (px)
                      </label>
                      <input
                        v-model.number="visionMaxImageDim"
                        type="number"
                        min="400"
                        max="4096"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Panel Footer -->
            <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
              <!-- Warning for unconfigured CSV/XLSX files -->
              <div
                v-if="unconfiguredCsvXlsxFiles.length > 0"
                class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg"
              >
                <div class="flex items-start gap-2">
                  <svg
                    class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <div class="flex-1">
                    <p class="text-sm font-medium text-amber-900">
                      {{ unconfiguredCsvXlsxFiles.length }} file(s) need import configuration
                    </p>
                    <ul class="mt-1 text-xs text-amber-700 list-disc list-inside">
                      <li v-for="file in unconfiguredCsvXlsxFiles" :key="file.id" class="truncate">
                        {{ file.file_name }}
                      </li>
                    </ul>
                    <p class="mt-2 text-xs text-amber-700">
                      Click "Configure" next to each file above to set up import settings before
                      preprocessing.
                    </p>
                  </div>
                </div>
              </div>

              <p class="text-xs text-gray-500 mb-4">
                This will create a new preprocessing run. Existing runs and documents are preserved.
              </p>
              <div class="flex items-center space-x-3">
                <button
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                  @click="emit('close')"
                >
                  Cancel
                </button>
                <button
                  :disabled="!canStartProcessing || isSubmitting"
                  class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  @click="onStart"
                >
                  <svg
                    v-if="isSubmitting"
                    class="animate-spin w-4 h-4 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  {{ isSubmitting ? 'Processing...' : 'Start Processing' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { getEngineLabel, getEngineSubtitle } from '@/utils/ocrLabels'
import { useScrollLock } from '@/composables/useScrollLock'

const props = defineProps({
  open: { type: Boolean, required: true },
  selectedFiles: { type: Array, required: true },
  getFileById: { type: Function, required: true },
  unconfiguredCsvXlsxFiles: { type: Array, required: true },
  canStartProcessing: { type: Boolean, required: true },
  isSubmitting: { type: Boolean, required: true },
  // OCR engine availability flags (from server settings)
  doclingOcrEnabled: { type: Boolean, default: true },
  mistralOcrEnabled: { type: Boolean, default: false },
  visionOcrEnabled: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'remove-file', 'clear-and-close', 'start'])

// Ref-counted scroll lock
useScrollLock({ watch: () => props.open })

// Processing config (owned by this panel)
const selectedEngine = ref('docling_tesseract')
const forceOcr = ref(false)
const tesseractLang = ref('auto')
const mistralApiKey = ref('')
const mistralModel = ref('')
const visionApiKey = ref('')
const visionBaseUrl = ref('')
const visionModel = ref('')
const visionPrompt = ref('Extract all text from this image and return it as clean markdown.')
const visionMaxImageDim = ref(0)
const showAdvanced = ref(false)

// Reset advanced toggle whenever the panel is opened.
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) showAdvanced.value = false
  },
)

// Reset selected engine if server settings disable the current selection.
// Mirrors the reset logic that previously lived in the parent's fetchOcrSettings().
watch(
  () => [props.doclingOcrEnabled, props.mistralOcrEnabled, props.visionOcrEnabled],
  ([docling, mistral, vision]) => {
    if (selectedEngine.value === 'llm_vision' && !vision) {
      selectedEngine.value = 'docling_tesseract'
    } else if (selectedEngine.value === 'mistral_ocr' && !mistral) {
      selectedEngine.value = 'docling_tesseract'
    }
    // If all OCR engines are disabled, reset to null to show the warning.
    if (!vision && !mistral && !docling) {
      selectedEngine.value = null
    }
  },
)

const anyOcrEnabled = computed(
  () => props.doclingOcrEnabled || props.mistralOcrEnabled || props.visionOcrEnabled,
)
const noOcrEnabled = computed(() => !anyOcrEnabled.value)

// Build the processing settings payload and emit start.
// Mirrors the logic that previously lived in the parent's startProcessing().
const onStart = () => {
  if (!props.canStartProcessing || props.isSubmitting) return

  const settings = {
    ocr_engine: selectedEngine.value,
    force_ocr: forceOcr.value,
  }

  if (selectedEngine.value === 'docling_tesseract' && tesseractLang.value !== 'auto') {
    settings.docling_ocr_languages = [tesseractLang.value]
  }

  if (selectedEngine.value === 'mistral_ocr') {
    if (mistralApiKey.value) settings.mistral_api_key = mistralApiKey.value
    if (mistralModel.value) settings.mistral_model = mistralModel.value
  }

  if (selectedEngine.value === 'llm_vision') {
    if (visionApiKey.value) settings.vision_api_key = visionApiKey.value
    if (visionBaseUrl.value) settings.vision_base_url = visionBaseUrl.value
    if (visionModel.value) settings.vision_model = visionModel.value
    if (visionPrompt.value) settings.vision_prompt = visionPrompt.value
    if (visionMaxImageDim.value > 0) settings.vision_max_image_dim = visionMaxImageDim.value
  }

  const engineNames = {
    docling_tesseract: 'Local OCR (Docling)',
    mistral_ocr: 'Mistral OCR',
    llm_vision: 'Vision LLM',
  }
  const forceOcrText = forceOcr.value ? ' + Force OCR' : ''
  const taskName = `${engineNames[selectedEngine.value] || 'Custom'}${forceOcrText}`

  emit('start', {
    file_ids: props.selectedFiles,
    inline_config: {
      name: taskName,
      additional_settings: settings,
    },
  })
}
</script>

<style scoped>
/* Panel slide-in animation */
.panel-slide-enter {
  transform: translateX(100%);
  animation: slideIn 0.3s ease-in-out forwards;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
</style>
