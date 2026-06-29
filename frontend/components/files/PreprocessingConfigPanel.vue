<template>
  <BaseModal
    :open="open"
    title="Configure Preprocessing"
    placement="right"
    panel-class="w-screen max-w-md"
    body-class="p-6 space-y-6"
    footer-class="flex items-center space-x-3"
    @close="emit('close')"
  >
    <!-- Panel Content -->
    <div class="space-y-6">
      <!-- Selected Files -->
      <div>
        <h4 class="text-sm font-medium text-slate-700 mb-3">
          Files to Process ({{ selectedFiles.length }})
        </h4>
        <div class="space-y-2 max-h-40 overflow-y-auto border border-slate-200 rounded-lg p-3">
          <div
            v-for="fileId in selectedFiles"
            :key="fileId"
            class="flex items-center justify-between text-sm"
          >
            <span class="truncate">{{ getFileById(fileId)?.file_name || 'Unknown' }}</span>
            <button class="text-slate-400 hover:text-red-500" @click="emit('remove-file', fileId)">
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>
        <BaseButton
          variant="ghost"
          size="sm"
          class="mt-2 font-medium"
          @click="emit('clear-and-close')"
        >
          Select different files
        </BaseButton>
      </div>

      <!-- OCR Engine Selection -->
      <div>
        <label :class="[labelClass, 'mb-3']"> OCR Engine </label>
        <div class="space-y-3">
          <!-- Local OCR -->
          <button
            v-if="doclingOcrEnabled"
            :class="[
              'w-full rounded-lg border-2 p-4 text-left transition-all',
              selectedEngine === 'docling_tesseract'
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300',
            ]"
            @click="selectedEngine = 'docling_tesseract'"
          >
            <div class="flex items-center">
              <Zap class="w-6 h-6 text-blue-600 mr-3" />
              <div>
                <p class="font-medium text-slate-900">
                  {{ getEngineLabel('docling_tesseract') }}
                </p>
                <p class="text-xs text-slate-500">
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
                : 'border-slate-200 hover:border-slate-300',
            ]"
            @click="selectedEngine = 'mistral_ocr'"
          >
            <div class="flex items-center">
              <CircleCheckBig class="w-6 h-6 text-blue-600 mr-3" />
              <div>
                <p class="font-medium text-slate-900">
                  {{ getEngineLabel('mistral_ocr') }}
                </p>
                <p class="text-xs text-slate-500">
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
                : 'border-slate-200 hover:border-slate-300',
            ]"
            @click="selectedEngine = 'llm_vision'"
          >
            <div class="flex items-center">
              <Eye class="w-6 h-6 text-blue-600 mr-3" />
              <div>
                <p class="font-medium text-slate-900">
                  {{ getEngineLabel('llm_vision') }}
                </p>
                <p class="text-xs text-slate-500">{{ getEngineSubtitle('llm_vision') }}</p>
              </div>
            </div>
          </button>
        </div>
        <!-- Warning: No OCR engines enabled -->
        <div v-if="noOcrEnabled" class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p class="text-sm font-medium text-amber-900 inline-flex items-center gap-1.5">
            <AlertTriangle class="w-4 h-4" />
            All OCR engines are disabled. Only PDFs with embedded text can be processed.
          </p>
          <p class="text-xs text-amber-700 mt-1">
            Image files (PNG/JPEG) require OCR. Enable Local OCR, Mistral OCR, or Vision LLM in
            Admin Settings to process images. PDFs will use pypdf for embedded text extraction.
          </p>
        </div>
      </div>

      <!-- Force OCR (always visible) -->
      <div class="border-t border-slate-200 pt-4">
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
        <label :class="labelClass">Prompt</label>
        <textarea
          v-model="visionPrompt"
          rows="2"
          placeholder="Extract all text as markdown..."
          :class="textareaClass"
        ></textarea>
      </div>

      <!-- Advanced Options -->
      <div class="border-t border-slate-200 pt-4">
        <button
          class="text-sm font-medium text-slate-700 flex items-center"
          @click="showAdvanced = !showAdvanced"
        >
          <ChevronRight
            :class="['w-4 h-4 mr-2 transition-transform', showAdvanced ? 'rotate-90' : '']"
          />
          Advanced Options
        </button>

        <div v-show="showAdvanced" class="mt-4 space-y-4">
          <!-- Tesseract Language -->
          <div v-if="selectedEngine === 'docling_tesseract'">
            <label :class="labelClass"> Tesseract Language </label>
            <select v-model="tesseractLang" :class="selectClass">
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
            <FormField
              v-model="mistralApiKey"
              label="API Key"
              type="text"
              maxlength="512"
              placeholder="Leave empty to use server default"
            />
            <FormField
              v-model="mistralModel"
              label="Model"
              type="text"
              placeholder="mistral-ocr-latest"
            />
          </div>

          <!-- Vision LLM Advanced Settings -->
          <div v-if="selectedEngine === 'llm_vision'" class="space-y-3">
            <FormField
              v-model="visionApiKey"
              label="API Key"
              type="text"
              maxlength="512"
              placeholder="Leave empty to use server default"
            />
            <FormField
              v-model="visionBaseUrl"
              label="Base URL"
              type="text"
              maxlength="512"
              placeholder="https://api.openai.com/v1"
            />
            <FormField
              v-model="visionModel"
              label="Model"
              type="text"
              placeholder="Leave empty to use server default"
            />
            <FormField
              v-model.number="visionMaxImageDim"
              label="Max Image Dimension (px)"
              type="number"
              :min="400"
              :max="4096"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Panel Footer -->
    <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex-shrink-0">
      <!-- Warning for unconfigured CSV/XLSX files -->
      <div
        v-if="unconfiguredCsvXlsxFiles.length > 0"
        class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg"
      >
        <div class="flex items-start gap-2">
          <AlertTriangle class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
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

      <p class="text-xs text-slate-500 mb-4">
        This will create a new preprocessing run. Existing runs and documents are preserved.
      </p>
    </div>
    <template #footer>
      <BaseButton variant="secondary" class="flex-1" @click="emit('close')"> Cancel </BaseButton>
      <BaseButton
        class="flex-1"
        :disabled="!canStartProcessing || isSubmitting"
        :loading="isSubmitting"
        @click="onStart"
      >
        {{ isSubmitting ? 'Processing...' : 'Start Processing' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { AlertTriangle, ChevronRight, CircleCheckBig, Eye, X, Zap } from '@lucide/vue'
import { getEngineLabel, getEngineSubtitle } from '@/utils/ocrLabels'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FormField from '@/components/common/FormField.vue'
import { textareaClass, selectClass, labelClass } from '@/utils/formStyles'

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
