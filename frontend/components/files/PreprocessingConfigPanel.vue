<template>
  <BaseModal
    :open="open"
    :title="$t('files.actions.configure_preprocessing')"
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
        <h4 class="text-sm font-medium text-content-muted mb-3">
          {{ $t('files.config.files_to_process', { count: selectedFiles.length }) }}
        </h4>
        <div class="space-y-2 max-h-40 overflow-y-auto border border-default rounded-card p-3">
          <div
            v-for="fileId in selectedFiles"
            :key="fileId"
            class="flex items-center justify-between text-sm"
          >
            <span class="truncate">{{
              getFileById(fileId)?.file_name || $t('files.config.unknown')
            }}</span>
            <button
              class="text-content-subtle hover:text-red-500 dark:hover:text-red-400"
              @click="emit('remove-file', fileId)"
            >
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
          {{ $t('files.config.select_different') }}
        </BaseButton>
      </div>

      <!-- OCR configuration — only shown when the selection includes files that
           need OCR (PDF / images). CSV, Excel and plain-text files are imported as
           structured text and never touch an OCR engine, so we neither show this
           section nor force an engine choice for a table/text-only selection. -->
      <template v-if="hasOcrRequiringFiles">
        <div>
          <label :class="[labelClass, 'mb-3']"> {{ $t('files.config.ocr_engine') }} </label>

          <!-- Hard error: the selection needs OCR but no engine is enabled. -->
          <Callout v-if="ocrRequiredButUnavailable" variant="danger">
            <p class="text-sm font-medium">
              {{ $t('files.config.ocr_required_title') }}
            </p>
            <p class="text-xs mt-1">
              {{ $t('files.config.ocr_required_desc') }}
            </p>
          </Callout>

          <div v-else class="space-y-3">
            <!-- Local OCR -->
            <button
              v-if="doclingOcrEnabled"
              :class="[
                'w-full rounded-card border-2 p-4 text-left transition-all',
                selectedEngine === 'docling_tesseract'
                  ? 'border-primary bg-primary-soft'
                  : 'border-default hover:border-strong',
              ]"
              @click="selectedEngine = 'docling_tesseract'"
            >
              <div class="flex items-center">
                <Zap class="w-6 h-6 text-primary mr-3" />
                <div>
                  <p class="font-medium text-content">
                    {{ getEngineLabel('docling_tesseract') }}
                  </p>
                  <p class="text-xs text-content-muted">
                    {{ getEngineSubtitle('docling_tesseract') }}
                  </p>
                </div>
              </div>
            </button>

            <!-- Mistral OCR -->
            <button
              v-if="mistralOcrEnabled"
              :class="[
                'w-full rounded-card border-2 p-4 text-left transition-all',
                selectedEngine === 'mistral_ocr'
                  ? 'border-primary bg-primary-soft'
                  : 'border-default hover:border-strong',
              ]"
              @click="selectedEngine = 'mistral_ocr'"
            >
              <div class="flex items-center">
                <CircleCheckBig class="w-6 h-6 text-primary mr-3" />
                <div>
                  <p class="font-medium text-content">
                    {{ getEngineLabel('mistral_ocr') }}
                  </p>
                  <p class="text-xs text-content-muted">
                    {{ getEngineSubtitle('mistral_ocr') }}
                  </p>
                </div>
              </div>
            </button>

            <!-- Vision LLM -->
            <button
              v-if="visionOcrEnabled"
              :class="[
                'w-full rounded-card border-2 p-4 text-left transition-all',
                selectedEngine === 'llm_vision'
                  ? 'border-primary bg-primary-soft'
                  : 'border-default hover:border-strong',
              ]"
              @click="selectedEngine = 'llm_vision'"
            >
              <div class="flex items-center">
                <Eye class="w-6 h-6 text-primary mr-3" />
                <div>
                  <p class="font-medium text-content">
                    {{ getEngineLabel('llm_vision') }}
                  </p>
                  <p class="text-xs text-content-muted">
                    {{ getEngineSubtitle('llm_vision') }}
                  </p>
                </div>
              </div>
            </button>
          </div>
        </div>

        <!-- Force OCR (PDFs only; needs an enabled engine and PDFs in the selection) -->
        <div v-if="anyOcrEnabled && hasPdfFiles" class="border-t border-default pt-4">
          <label
            class="flex items-start space-x-3 p-3 bg-amber-50 rounded-card border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800"
          >
            <input v-model="forceOcr" type="checkbox" class="mt-0.5 text-amber-600 rounded" />
            <div>
              <p class="text-sm font-medium text-amber-900 dark:text-amber-300">
                {{ $t('files.config.force_ocr_title') }}
              </p>
              <p class="text-xs text-amber-700 dark:text-amber-400 mt-1">
                {{ $t('files.config.force_ocr_desc') }}
              </p>
            </div>
          </label>
        </div>
      </template>

      <!-- Table/text-only selection: no OCR engine required. -->
      <Callout v-else variant="info">
        <p class="text-sm font-medium">{{ $t('files.config.no_ocr_title') }}</p>
        <p class="text-xs mt-1">
          {{ $t('files.config.no_ocr_desc') }}
        </p>
      </Callout>

      <!-- Vision LLM Prompt (visible when Vision LLM is picked for an OCR file) -->
      <div v-if="hasOcrRequiringFiles && selectedEngine === 'llm_vision'" class="pt-4">
        <label :class="labelClass" for="vision-ocr-prompt">{{ $t('files.config.prompt') }}</label>
        <textarea
          id="vision-ocr-prompt"
          v-model="visionPrompt"
          rows="2"
          :placeholder="$t('files.config.prompt_placeholder')"
          :class="textareaClass"
        ></textarea>
      </div>

      <!-- Advanced Options (OCR-engine specific) -->
      <div v-if="hasOcrRequiringFiles && anyOcrEnabled" class="border-t border-default pt-4">
        <button
          class="text-sm font-medium text-content-muted flex items-center"
          @click="showAdvanced = !showAdvanced"
        >
          <ChevronRight
            :class="['w-4 h-4 mr-2 transition-transform', showAdvanced ? 'rotate-90' : '']"
          />
          {{ $t('files.config.advanced_options') }}
        </button>

        <div v-show="showAdvanced" class="mt-4 space-y-4">
          <!-- Tesseract Language -->
          <div v-if="selectedEngine === 'docling_tesseract'">
            <label :class="labelClass" for="tesseract-language">
              {{ $t('files.config.tesseract_language') }}
            </label>
            <select id="tesseract-language" v-model="tesseractLang" :class="selectClass">
              <option value="auto">{{ $t('files.config.lang_auto') }}</option>
              <option value="eng">{{ $t('files.config.lang_eng') }}</option>
              <option value="deu">{{ $t('files.config.lang_deu') }}</option>
              <option value="fra">{{ $t('files.config.lang_fra') }}</option>
              <option value="spa">{{ $t('files.config.lang_spa') }}</option>
              <option value="ita">{{ $t('files.config.lang_ita') }}</option>
              <option value="por">{{ $t('files.config.lang_por') }}</option>
              <option value="nld">{{ $t('files.config.lang_nld') }}</option>
              <option value="pol">{{ $t('files.config.lang_pol') }}</option>
              <option value="rus">{{ $t('files.config.lang_rus') }}</option>
              <option value="chi-sim">{{ $t('files.config.lang_chi_sim') }}</option>
              <option value="lat">{{ $t('files.config.lang_lat') }}</option>
            </select>
          </div>

          <!-- Mistral Settings -->
          <div v-if="selectedEngine === 'mistral_ocr'" class="space-y-3">
            <PasswordInput
              v-model="mistralApiKey"
              :label="$t('files.config.api_key')"
              :show-strength="false"
              autocomplete="off"
              maxlength="512"
              :placeholder="$t('files.config.leave_empty_default')"
            />
            <FormField
              v-model="mistralModel"
              :label="$t('files.config.model')"
              type="text"
              placeholder="mistral-ocr-latest"
            />
          </div>

          <!-- Vision LLM Advanced Settings -->
          <div v-if="selectedEngine === 'llm_vision'" class="space-y-3">
            <PasswordInput
              v-model="visionApiKey"
              :label="$t('files.config.api_key')"
              :show-strength="false"
              autocomplete="off"
              maxlength="512"
              :placeholder="$t('files.config.leave_empty_default')"
            />
            <FormField
              v-model="visionBaseUrl"
              :label="$t('files.config.base_url')"
              type="text"
              maxlength="512"
              placeholder="https://api.openai.com/v1"
            />
            <FormField
              v-model="visionModel"
              :label="$t('files.config.model')"
              type="text"
              :placeholder="$t('files.config.leave_empty_default')"
            />
            <FormField
              v-model.number="visionMaxImageDim"
              :label="$t('files.config.max_image_dim')"
              type="number"
              :min="400"
              :max="4096"
            />
          </div>
        </div>
      </div>

      <!-- Warning for unconfigured CSV/XLSX files (part of the scrollable body,
           right where the blocked state needs explaining) -->
      <Callout
        v-if="unconfiguredCsvXlsxFiles.length > 0"
        variant="warning"
        :title="$t('files.config.needs_config_title', { count: unconfiguredCsvXlsxFiles.length })"
      >
        <ul class="mt-1 text-xs list-disc list-inside">
          <li v-for="file in unconfiguredCsvXlsxFiles" :key="file.id" class="truncate">
            {{ file.file_name }}
          </li>
        </ul>
        <p class="mt-2 text-xs">
          {{ $t('files.config.needs_config_hint') }}
        </p>
      </Callout>
    </div>

    <!-- Single real footer: reassurance note + actions (the note used to sit in
         a footer-styled block inside the scroll body, reading as two stacked
         footers). -->
    <template #footer>
      <div class="w-full space-y-3">
        <p class="text-xs text-content-muted">
          {{ $t('files.config.footer_note') }}
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="emit('close')">
            {{ $t('files.actions.cancel') }}
          </BaseButton>
          <BaseButton
            class="flex-1"
            :disabled="!canSubmit || isSubmitting"
            :loading="isSubmitting"
            @click="onStart"
          >
            {{ isSubmitting ? $t('files.config.processing') : $t('files.config.start_processing') }}
          </BaseButton>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ChevronRight, CircleCheckBig, Eye, X, Zap } from '@lucide/vue'
import { getEngineLabel, getEngineSubtitle } from '@/utils/ocrLabels'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import { textareaClass, selectClass, labelClass } from '@/utils/formStyles'
import type { File, PreprocessingTaskCreate } from '@/types'

type OcrEngine = 'docling_tesseract' | 'mistral_ocr' | 'llm_vision' | null

interface Props {
  open: boolean
  selectedFiles: number[]
  getFileById: (id: number) => File | undefined
  unconfiguredCsvXlsxFiles: File[]
  canStartProcessing: boolean
  isSubmitting: boolean
  // OCR engine availability flags (from server settings)
  doclingOcrEnabled?: boolean
  mistralOcrEnabled?: boolean
  visionOcrEnabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  doclingOcrEnabled: true,
  mistralOcrEnabled: false,
  visionOcrEnabled: false,
})

const emit = defineEmits<{
  close: []
  'remove-file': [fileId: number]
  'clear-and-close': []
  start: [payload: PreprocessingTaskCreate]
}>()

// Processing config (owned by this panel). The engine is seeded by the watcher
// below to the first *enabled* engine, so we start empty rather than assuming a
// default (e.g. 'docling_tesseract') that may be disabled.
const selectedEngine = ref<OcrEngine>(null)
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

const anyOcrEnabled = computed(
  () => props.doclingOcrEnabled || props.mistralOcrEnabled || props.visionOcrEnabled,
)
const noOcrEnabled = computed(() => !anyOcrEnabled.value)

// The first enabled engine — the default selection and the fallback when the
// current choice becomes unavailable. null when no engine is enabled.
const firstEnabledEngine = computed<OcrEngine>(() => {
  if (props.doclingOcrEnabled) return 'docling_tesseract'
  if (props.mistralOcrEnabled) return 'mistral_ocr'
  if (props.visionOcrEnabled) return 'llm_vision'
  return null
})

// Keep the selected engine valid as server settings load/change: if the current
// choice isn't an enabled engine (e.g. the old default 'docling_tesseract' while
// docling is disabled), fall back to the first enabled one — or null if none.
// `immediate` seeds the default on mount.
watch(
  firstEnabledEngine,
  () => {
    const stillValid =
      (selectedEngine.value === 'docling_tesseract' && props.doclingOcrEnabled) ||
      (selectedEngine.value === 'mistral_ocr' && props.mistralOcrEnabled) ||
      (selectedEngine.value === 'llm_vision' && props.visionOcrEnabled)
    if (!stillValid) selectedEngine.value = firstEnabledEngine.value
  },
  { immediate: true },
)

// ── File-type–aware OCR requirement ──────────────────────────────────────────
// CSV / Excel / plain-text files are imported as structured text and never use
// an OCR engine. Any other type (PDF, images, …) may need OCR, so when one is in
// the selection we require an enabled engine (and error if none is enabled).
const NON_OCR_FILE_TYPES = new Set<string>([
  'text/plain',
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
])

const hasOcrRequiringFiles = computed(() =>
  props.selectedFiles.some((id) => {
    const type = props.getFileById(id)?.file_type
    // Unknown/undefined type → treat as OCR-requiring (safer: forces a choice).
    return !type || !NON_OCR_FILE_TYPES.has(type)
  }),
)

// Whether the selection contains any PDFs — "Force OCR for PDFs" is meaningless
// (and hidden) otherwise.
const hasPdfFiles = computed(() =>
  props.selectedFiles.some((id) => props.getFileById(id)?.file_type === 'application/pdf'),
)

// OCR-requiring files are selected but no engine is enabled → hard block + error.
const ocrRequiredButUnavailable = computed(() => hasOcrRequiringFiles.value && noOcrEnabled.value)

// Combine the parent's gate (files selected, CSV/XLSX configured, not submitting)
// with the OCR rules: a table/text-only selection needs no engine; an
// OCR-requiring selection needs an enabled engine to be picked.
const canSubmit = computed(() => {
  if (!props.canStartProcessing) return false
  if (!hasOcrRequiringFiles.value) return true // table/text only → no engine needed
  if (noOcrEnabled.value) return false // needs OCR, none enabled
  return selectedEngine.value !== null // needs OCR → must pick an engine
})

// Build the processing settings payload and emit start.
// Mirrors the logic that previously lived in the parent's startProcessing().
const onStart = (): void => {
  if (!canSubmit.value || props.isSubmitting) return

  // Table/text-only selections don't use OCR — send no engine (and no
  // engine-specific options). Otherwise send the picked engine + its options.
  const engine = hasOcrRequiringFiles.value ? selectedEngine.value : null

  const settings: Record<string, unknown> = {
    ocr_engine: engine,
    // The Force-OCR toggle only renders (and only makes sense) for PDFs.
    force_ocr: hasPdfFiles.value ? forceOcr.value : false,
  }

  if (engine === 'docling_tesseract' && tesseractLang.value !== 'auto') {
    settings.docling_ocr_languages = [tesseractLang.value]
  }

  if (engine === 'mistral_ocr') {
    if (mistralApiKey.value) settings.mistral_api_key = mistralApiKey.value
    if (mistralModel.value) settings.mistral_model = mistralModel.value
  }

  if (engine === 'llm_vision') {
    if (visionApiKey.value) settings.vision_api_key = visionApiKey.value
    if (visionBaseUrl.value) settings.vision_base_url = visionBaseUrl.value
    if (visionModel.value) settings.vision_model = visionModel.value
    if (visionPrompt.value) settings.vision_prompt = visionPrompt.value
    if (visionMaxImageDim.value > 0) settings.vision_max_image_dim = visionMaxImageDim.value
  }

  const engineNames: Record<string, string> = {
    docling_tesseract: 'Local OCR (Docling)',
    mistral_ocr: 'Mistral OCR',
    llm_vision: 'Vision LLM',
  }
  const forceOcrText = settings.force_ocr ? ' + Force OCR' : ''
  const taskName = engine ? `${engineNames[engine] || 'Custom'}${forceOcrText}` : 'Text extraction'

  emit('start', {
    file_ids: props.selectedFiles,
    inline_config: {
      name: taskName,
      additional_settings: settings,
    },
  })
}
</script>
