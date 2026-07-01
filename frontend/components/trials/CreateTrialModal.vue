<template>
  <BaseModal :open="open" size="2xl" panel-class="max-h-[95vh]" @close="tryClose">
    <template #header>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-semibold text-slate-900 dark:text-white">Start New Trial</h3>
          <Tooltip :text="trialHelpText">
            <Info
              class="h-4 w-4 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
            />
          </Tooltip>
        </div>
        <!-- Simple/Advanced Mode Toggle -->
        <BaseSegmentedControl
          v-model="simpleMode"
          :options="[
            { label: 'Simple', value: true },
            { label: 'Advanced', value: false },
          ]"
        />
      </div>
    </template>

    <!-- Orientation (Advanced mode only) -->
    <Callout v-if="!simpleMode" variant="info" title="What is a trial?" class="mb-6">
      <p class="mt-1">
        A trial runs an AI model over your documents to extract structured data. You need four
        things: a <strong>Schema</strong> (the fields to extract), a
        <strong>Prompt</strong> (extraction instructions), a <strong>Model</strong> (the AI), and
        the <strong>Documents</strong> to process. Your schema is automatically included with the
        prompt — you don't need to describe the fields manually.
      </p>
    </Callout>

    <div class="grid md:grid-cols-2 gap-8">
      <!-- LEFT COLUMN -->
      <div>
        <!-- Name / Description: collapsible in Simple mode, always visible in Advanced -->
        <div v-if="!simpleMode" class="mb-8">
          <TrialMetadataCard
            v-model:name="trialData.name"
            v-model:description="trialData.description"
          />
        </div>
        <div v-else class="mb-6">
          <BaseButton
            variant="link"
            tone="blue"
            class="text-sm flex items-center"
            @click="metadataVisible = !metadataVisible"
          >
            <span>{{ metadataVisible ? 'Hide' : 'Add' }} name / notes</span>
            <ChevronDown
              :class="{ 'rotate-180': metadataVisible }"
              class="h-4 w-4 ml-1 transition-transform"
              aria-hidden="true"
            />
          </BaseButton>
          <div v-if="metadataVisible" class="mt-3">
            <TrialMetadataCard
              v-model:name="trialData.name"
              v-model:description="trialData.description"
            />
          </div>
        </div>

        <!-- Prompt / Schema / Model -->
        <div
          class="mb-8 bg-white dark:bg-slate-800/40 border dark:border-slate-700 rounded-xl p-6 shadow"
        >
          <TrialPromptSelect
            v-model="trialData.prompt_id"
            :prompts="prompts"
            @change="resetModelTest"
          />

          <TrialSchemaSelect
            v-model="trialData.schema_id"
            :schemas="schemas"
            @change="resetModelTest"
          />

          <TrialModelSelect
            v-model="trialData.llm_model"
            :available-models="availableModels"
            :is-loading-models="isLoadingModels"
            :is-testing-connection="isTestingConnection"
            :config-status="configStatus"
          />
        </div>

        <!-- Advanced toggles + sections (Advanced mode only) -->
        <div v-if="!simpleMode">
          <div class="flex items-center gap-4 mb-2">
            <BaseButton
              variant="link"
              tone="blue"
              class="text-sm flex items-center"
              @click="advancedSettingsVisible = !advancedSettingsVisible"
            >
              <span>{{ advancedSettingsVisible ? 'Hide' : 'Show' }} Advanced Settings</span>
              <ChevronDown
                :class="{ 'rotate-180': advancedSettingsVisible }"
                class="h-4 w-4 ml-1 transition-transform"
                aria-hidden="true"
              />
            </BaseButton>
            <BaseButton
              variant="link"
              tone="blue"
              class="text-sm flex items-center"
              @click="advancedOptionsVisible = !advancedOptionsVisible"
            >
              <span>{{ advancedOptionsVisible ? 'Hide' : 'Use' }} Custom API Settings</span>
              <ChevronDown
                :class="{ 'rotate-180': advancedOptionsVisible }"
                class="h-4 w-4 ml-1 transition-transform"
                aria-hidden="true"
              />
            </BaseButton>
          </div>

          <!-- Advanced Settings -->
          <AdvancedSettingsPanel
            v-if="advancedSettingsVisible"
            v-model:max-completion-tokens="maxCompletionTokens"
            v-model:temperature="temperature"
            v-model:reasoning-effort="reasoningEffort"
          />

          <!-- Custom API Settings -->
          <CustomApiSettingsPanel
            v-if="advancedOptionsVisible"
            v-model:api-key="trialData.api_key"
            v-model:base-url="trialData.base_url"
          />
        </div>

        <!-- Model test / status indicator (Advanced mode only — Simple mode runs the
             check transparently on submit) -->
        <ModelTestCard
          v-if="!simpleMode && trialData.llm_model && trialData.schema_id && hasValidConfig"
          :status="modelTestStatus"
          :is-testing="isTestingModel"
          :llm-model="trialData.llm_model"
          :schema-id="trialData.schema_id"
          @test="testSelectedModel"
        />
      </div>

      <!-- RIGHT COLUMN -->
      <div>
        <DocumentSelectionPanel
          v-model:mode="documentSelectionMode"
          v-model:selected-ids="trialData.document_ids"
          :project-id="projectId"
        />
      </div>
    </div>

    <!-- Submission overlay: compatibility test running -->
    <div
      v-if="submitting"
      class="mt-6 flex items-center gap-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
    >
      <LoadingSpinner size="small" color="blue" inline label="" />
      <div class="text-sm text-blue-800 dark:text-blue-300">
        <p class="font-medium text-blue-900 dark:text-blue-200">Checking model compatibility…</p>
        <p class="mt-0.5">
          Verifying that {{ trialData.llm_model || 'the model' }} works with your schema before
          starting the trial.
        </p>
      </div>
    </div>

    <!-- Inline status line (hidden while submitting — the overlay above takes over) -->
    <div v-else class="mt-6 flex items-center gap-2 text-sm">
      <component :is="statusIcon" v-if="statusIcon" :class="['h-4 w-4', statusIconClass]" />
      <p :class="statusTextClass">{{ statusMessage }}</p>
    </div>

    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="tryClose">Cancel</BaseButton>
      <BaseButton
        variant="primary"
        :disabled="!canSubmit || submitting"
        :loading="submitting"
        @click="handleStartTrial"
      >
        {{ submitting ? 'Verifying…' : 'Start Trial' }}
      </BaseButton>
    </template>

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      title="Discard unsaved changes?"
      message="Your trial configuration will be lost."
      confirm-text="Discard"
      cancel-text="Keep editing"
      confirm-variant="danger"
      @confirm="confirmDiscard"
      @cancel="showConfirm = false"
    />
  </BaseModal>
</template>

<script setup>
import { computed, ref, toRef, watch } from 'vue'
import { CheckCircle2, ChevronDown, CircleAlert, Info, Loader2 } from '@lucide/vue'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import Callout from '@/components/common/Callout.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import TrialMetadataCard from './TrialMetadataCard.vue'
import TrialPromptSelect from './TrialPromptSelect.vue'
import TrialSchemaSelect from './TrialSchemaSelect.vue'
import TrialModelSelect from './TrialModelSelect.vue'
import AdvancedSettingsPanel from './AdvancedSettingsPanel.vue'
import CustomApiSettingsPanel from './CustomApiSettingsPanel.vue'
import ModelTestCard from './ModelTestCard.vue'
import DocumentSelectionPanel from './DocumentSelectionPanel.vue'
import { useModelTesting } from '@/composables/useModelTesting'

const toast = useToast()

const props = defineProps({
  open: { type: Boolean, required: true },
  documents: { type: Array, required: true }, // kept for compatibility; Individual tab now uses backend pagination
  schemas: { type: Array, required: true },
  prompts: { type: Array, default: () => [] },
  projectId: { type: [String, Number], required: true },
})

const emit = defineEmits(['close', 'create', 'create-group'])

const trialHelpText =
  'A trial runs an AI model over your documents to extract structured data. You need a Schema, a Prompt, a Model, and the Documents to process. The schema is automatically included with the prompt.'

/* -------------------------------------------------------
 * General trial state
 * -----------------------------------------------------*/
const trialData = ref({
  name: '',
  description: '',
  schema_id: '',
  prompt_id: '',
  document_ids: [],
  llm_model: '',
  api_key: '',
  base_url: '',
  advanced_options: {},
})

const simpleMode = ref(true)
const submitting = ref(false)
const metadataVisible = ref(false)
const documentSelectionMode = ref('individual')

// Advanced options
const maxCompletionTokens = ref('')
const temperature = ref('')
const reasoningEffort = ref('')

const advancedSettingsVisible = ref(false)
const advancedOptionsVisible = ref(false)

/* -------------------------------------------------------
 * Model testing (connection + model/schema test)
 * -----------------------------------------------------*/
const {
  availableModels,
  isLoadingModels,
  isTestingConnection,
  isTestingModel,
  connectionTested,
  connectionValid,
  modelTested,
  modelValid,
  systemConfigError,
  customConfigError,
  hasSystemConfig,
  hasCustomApiSettings,
  hasValidConfig,
  configStatus,
  modelTestStatus,
  resetModelTest,
  testAndLoadModels,
  testSelectedModel,
} = useModelTesting({
  trialData,
  projectId: toRef(props, 'projectId'),
  maxCompletionTokens,
  temperature,
  reasoningEffort,
})

/* -------------------------------------------------------
 * Form validation
 * -----------------------------------------------------*/
// Core readiness — gates the Start Trial button. The model/schema compatibility
// check is run automatically on submit (see handleStartTrial), so it is NOT
// required to enable the button.
const canSubmit = computed(() => {
  return (
    trialData.value.schema_id &&
    trialData.value.prompt_id &&
    trialData.value.document_ids.length > 0 &&
    trialData.value.llm_model &&
    availableModels.value.length > 0 &&
    hasValidConfig.value
  )
})

/* -------------------------------------------------------
 * Inline status line
 * -----------------------------------------------------*/
const statusMessage = computed(() => {
  if (submitting.value) return 'Verifying model works with your schema…'
  if (isTestingModel.value) return modelTestStatus.value.message
  if (!trialData.value.llm_model) return 'Choose a model to continue.'
  if (!hasValidConfig.value) return configStatus.value.message
  if (trialData.value.document_ids.length === 0) return 'Select documents to continue.'
  if (modelTested.value && modelValid.value)
    return 'Model verified with this schema — ready to start.'
  if (modelTested.value && !modelValid.value)
    return `Verification failed: ${modelTestStatus.value.message}`
  return 'Model will be checked when you start the trial.'
})

const statusIcon = computed(() => {
  if (submitting.value || isTestingModel.value) return Loader2
  if (modelTested.value && modelValid.value && canSubmit.value) return CheckCircle2
  if (modelTested.value && !modelValid.value) return CircleAlert
  return Info
})

const statusIconClass = computed(() => {
  if (submitting.value || isTestingModel.value) return 'text-blue-500 animate-spin'
  if (modelTested.value && modelValid.value && canSubmit.value) return 'text-green-500'
  if (modelTested.value && !modelValid.value) return 'text-red-500'
  return 'text-slate-400'
})

const statusTextClass = computed(() => {
  if (modelTested.value && modelValid.value && canSubmit.value)
    return 'text-green-700 dark:text-green-400'
  if (modelTested.value && !modelValid.value) return 'text-red-700 dark:text-red-400'
  return 'text-slate-600 dark:text-slate-400'
})

/* -------------------------------------------------------
 * Initialize form on open
 * -----------------------------------------------------*/
const initializeForm = () => {
  trialData.value = {
    name: '',
    description: '',
    schema_id: props.schemas.length > 0 ? props.schemas[0].id.toString() : '',
    prompt_id: props.prompts.length > 0 ? props.prompts[0].id.toString() : '',
    document_ids: [],
    llm_model: '',
    api_key: '',
    base_url: '',
    advanced_options: {},
  }

  simpleMode.value = true
  submitting.value = false
  metadataVisible.value = false
  documentSelectionMode.value = 'individual'

  connectionTested.value = false
  connectionValid.value = false
  systemConfigError.value = null
  customConfigError.value = null
  hasSystemConfig.value = true
  availableModels.value = []
  advancedSettingsVisible.value = false
  maxCompletionTokens.value = ''
  temperature.value = ''
  reasoningEffort.value = ''
  resetModelTest()

  snapshotInitialValues()
  testAndLoadModels()
}

/* -------------------------------------------------------
 * Submission (guided: verify model, then create)
 * -----------------------------------------------------*/
const buildFormData = () => {
  const formData = {
    name: (trialData.value.name || '').trim() || undefined,
    description: (trialData.value.description || '').trim() || undefined,
    schema_id: parseInt(trialData.value.schema_id),
    prompt_id: parseInt(trialData.value.prompt_id),
    document_ids: trialData.value.document_ids,
    llm_model: trialData.value.llm_model,
  }

  if ((trialData.value.api_key || '').trim()) formData.api_key = trialData.value.api_key.trim()
  if ((trialData.value.base_url || '').trim()) formData.base_url = trialData.value.base_url.trim()

  const advancedOptions = {}
  if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
    advancedOptions.max_completion_tokens = parseInt(maxCompletionTokens.value)
  }
  if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
    advancedOptions.temperature = Number(temperature.value)
  }
  if (reasoningEffort.value) {
    advancedOptions.reasoning_effort = reasoningEffort.value
  }
  if (Object.keys(advancedOptions).length > 0) {
    formData.advanced_options = advancedOptions
  }

  return formData
}

const handleStartTrial = async () => {
  if (!canSubmit.value || submitting.value) return

  submitting.value = true
  try {
    // Fast path: already verified with the current model/schema/options.
    if (!(modelTested.value && modelValid.value)) {
      await testSelectedModel() // Phase 1 — verify
      if (!modelValid.value) {
        // Reason is shown via the inline status line + ModelTestCard.
        submitting.value = false
        return
      }
    }
    emit('create', buildFormData()) // Phase 2 — submit
  } catch {
    toast.error('Could not start the trial. Please try again.')
    submitting.value = false
  }
}

/* -------------------------------------------------------
 * Close with confirmation
 * -----------------------------------------------------*/
// Snapshot of the form state captured right after initializeForm(). Because
// schema_id/prompt_id are pre-selected on open, comparing against an empty
// baseline would always mark the form dirty and prompt "Discard changes?" on a
// no-op open/close. Comparing against this baseline only flags *user* edits.
const initialValues = ref({
  name: '',
  description: '',
  schema_id: '',
  prompt_id: '',
  document_ids: [],
  llm_model: '',
  api_key: '',
  base_url: '',
})

const snapshotInitialValues = () => {
  initialValues.value = {
    name: trialData.value.name,
    description: trialData.value.description,
    schema_id: trialData.value.schema_id,
    prompt_id: trialData.value.prompt_id,
    document_ids: [...trialData.value.document_ids],
    llm_model: trialData.value.llm_model,
    api_key: trialData.value.api_key,
    base_url: trialData.value.base_url,
  }
}

const isDirty = computed(() => {
  const i = initialValues.value
  const t = trialData.value
  return (
    t.name !== i.name ||
    t.description !== i.description ||
    t.schema_id !== i.schema_id ||
    t.prompt_id !== i.prompt_id ||
    t.llm_model !== i.llm_model ||
    t.api_key !== i.api_key ||
    t.base_url !== i.base_url ||
    (t.document_ids || []).length !== (i.document_ids || []).length ||
    (t.document_ids || []).some((id, idx) => id !== i.document_ids[idx])
  )
})

const showConfirm = ref(false)
const tryClose = () => {
  if (submitting.value) return
  if (isDirty.value) {
    showConfirm.value = true
  } else {
    emit('close')
  }
}
const confirmDiscard = () => {
  showConfirm.value = false
  emit('close')
}

/* -------------------------------------------------------
 * Watchers
 * -----------------------------------------------------*/
watch(
  () => props.open,
  (newValue) => {
    if (newValue) {
      initializeForm()
    }
  },
  { immediate: true },
)

watch([() => trialData.value.api_key, () => trialData.value.base_url], () => {
  connectionTested.value = false
  connectionValid.value = false
  resetModelTest()

  trialData.value.llm_model = ''
  availableModels.value = []

  if (hasCustomApiSettings.value) {
    clearTimeout(window.customSettingsTimeout)
    window.customSettingsTimeout = setTimeout(() => {
      testAndLoadModels(trialData.value.api_key, trialData.value.base_url)
    }, 1000)
  } else {
    testAndLoadModels()
  }
})

watch(
  [() => trialData.value.llm_model, () => trialData.value.schema_id],
  ([newModel, newSchema], [oldModel, oldSchema]) => {
    if (newModel !== oldModel || newSchema !== oldSchema) {
      resetModelTest()
    }
  },
)

watch(
  [() => maxCompletionTokens.value, () => temperature.value, () => reasoningEffort.value],
  () => {
    resetModelTest()
  },
)
</script>
