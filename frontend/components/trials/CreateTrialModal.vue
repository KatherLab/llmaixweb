<template>
  <!-- body-class makes the body a flex column at lg+, so the two-column area
       below can take exactly the height that's left instead of guessing a vh
       value that over- or undershoots depending on what else is on screen. -->
  <BaseModal
    :open="open"
    size="2xl"
    panel-class="max-h-[95vh]"
    body-class="p-6 lg:flex lg:flex-col"
    @close="tryClose"
  >
    <template #header>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-semibold text-content">{{ $t('trials.create.title') }}</h3>
          <Tooltip :text="trialHelpText">
            <Info class="h-4 w-4 text-content-subtle hover:text-content-muted" />
          </Tooltip>
        </div>
        <!-- Simple/Advanced Mode Toggle -->
        <BaseSegmentedControl
          v-model="simpleMode"
          :options="[
            { label: $t('trials.create.mode_simple'), value: true },
            { label: $t('trials.create.mode_advanced'), value: false },
          ]"
        />
      </div>
    </template>

    <!-- Orientation: a primer for the first run, dismissed for good once read.
         The same text stays available under the ⓘ next to the title, so keeping
         it on screen forever only costs every later run ~130px of height. -->
    <Callout
      v-if="showIntro"
      variant="info"
      :title="$t('trials.create.what_is_title')"
      class="mb-4 lg:shrink-0"
    >
      <p class="mt-1" v-html="$t('trials.create.what_is_body')"></p>
      <BaseButton variant="link" tone="blue" class="mt-2 text-xs" @click="dismissIntro">
        {{ $t('trials.create.intro_dismiss') }}
      </BaseButton>
    </Callout>

    <!-- Two independently scrolling columns at lg+: the choices on the left stay
         put while a long document list is browsed on the right. Below lg the
         columns stack and the modal body scrolls as one, as before. -->
    <!-- min-h floor: the columns share the leftover height, so on a short window
         (or on the first run, where the primer takes ~150px) the document list
         would otherwise be squeezed down to a row and a half. Below the floor
         the modal body scrolls again, which is the lesser evil. -->
    <div class="grid md:grid-cols-2 gap-8 lg:flex-1 lg:min-h-[26rem]">
      <!-- LEFT COLUMN -->
      <div class="lg:min-h-0 lg:overflow-y-auto lg:pr-2">
        <!-- Prompt / Schema / Model -->
        <div class="mb-8 bg-surface border border-default rounded-modal p-6 shadow">
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

          <!-- Source quotes: kept out of the collapsed Advanced section on
               purpose — it changes what the results viewer can show, so it has
               to be discoverable in Simple mode too. The explanation lives in
               the tooltip; only the cost stays inline, because that is the part
               nobody should have to hover to discover. -->
          <div class="flex items-center gap-2 mt-4 pt-4 border-t border-default">
            <input
              id="trial-evidence-mode"
              v-model="evidenceMode"
              type="checkbox"
              :class="checkboxClass"
            />
            <label
              for="trial-evidence-mode"
              class="text-sm font-medium text-content cursor-pointer"
            >
              {{ $t('trials.advanced.evidence_label') }}
            </label>
            <span class="text-xs text-content-subtle">{{
              $t('trials.advanced.evidence_cost')
            }}</span>
            <Tooltip :text="$t('trials.advanced.evidence_help')">
              <Info class="h-4 w-4 text-content-subtle hover:text-content-muted" />
            </Tooltip>
          </div>
        </div>

        <!-- Optional metadata sits *after* the required card: it used to be the
             first thing in the dialog, pushing the four required inputs down. -->
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
            <span>{{
              metadataVisible
                ? $t('trials.create.name_notes_hide')
                : $t('trials.create.name_notes_add')
            }}</span>
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

        <!-- Advanced toggles + sections (Advanced mode only) -->
        <div v-if="!simpleMode">
          <div class="flex items-center gap-4 mb-2">
            <BaseButton
              variant="link"
              tone="blue"
              class="text-sm flex items-center"
              @click="advancedSettingsVisible = !advancedSettingsVisible"
            >
              <span>{{
                advancedSettingsVisible
                  ? $t('trials.create.advanced_settings_hide')
                  : $t('trials.create.advanced_settings_show')
              }}</span>
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
              <span>{{
                advancedOptionsVisible
                  ? $t('trials.create.custom_api_hide')
                  : $t('trials.create.custom_api_use')
              }}</span>
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
            v-model:prompt-language="promptLanguage"
          />

          <!-- Custom API Settings -->
          <CustomApiSettingsPanel
            v-if="advancedOptionsVisible"
            v-model:api-key="trialData.api_key"
            v-model:base-url="trialData.base_url"
          />
        </div>

        <!-- Simple mode: custom-API escape hatch. Always discoverable (not just
             when the system config is broken), so a scientist pointing at a
             self-hosted / Ollama / vLLM endpoint can find it without switching
             to Advanced mode. -->
        <div v-else class="mb-8">
          <Callout
            v-if="!hasValidConfig && !hasCustomApiSettings"
            variant="warning"
            :title="$t('trials.create.no_model_title')"
            class="mb-3"
          >
            <p class="mt-1">
              {{ $t('trials.create.no_model_body') }}
            </p>
          </Callout>
          <BaseButton
            variant="link"
            tone="blue"
            class="text-sm flex items-center"
            @click="advancedOptionsVisible = !advancedOptionsVisible"
          >
            <span>{{
              advancedOptionsVisible
                ? $t('trials.create.custom_api_simple_hide')
                : hasCustomApiSettings
                  ? $t('trials.create.custom_api_simple_edit')
                  : $t('trials.create.custom_api_simple_use')
            }}</span>
            <ChevronDown
              :class="{ 'rotate-180': advancedOptionsVisible }"
              class="h-4 w-4 ml-1 transition-transform"
              aria-hidden="true"
            />
          </BaseButton>
          <CustomApiSettingsPanel
            v-if="advancedOptionsVisible"
            v-model:api-key="trialData.api_key"
            v-model:base-url="trialData.base_url"
            class="mt-3"
          />
        </div>

        <!-- Model test / status indicator. Advanced mode only — in Simple mode the
             check runs silently on Start Trial with a spinner overlay, so the card
             would just be noise. -->
        <ModelTestCard
          v-if="!simpleMode && trialData.llm_model && trialData.schema_id && hasValidConfig"
          :status="modelTestStatus"
          :is-testing="isTestingModel"
          :llm-model="trialData.llm_model"
          :schema-id="trialData.schema_id"
          @test="testSelectedModel"
        />
      </div>

      <!-- RIGHT COLUMN — a plain flex box, not a scroller: the panel inside
           already scrolls its own list, and nesting the two produced a second
           scrollbar and content sliding past the panel's bottom border. -->
      <div class="flex flex-col lg:min-h-0">
        <DocumentSelectionPanel
          v-model:mode="documentSelectionMode"
          v-model:selected-ids="trialData.document_ids"
          :project-id="projectId"
        />
      </div>
    </div>

    <!-- Submission overlay: compatibility test running -->
    <Callout v-if="submitting" variant="info" class="mt-6">
      <div class="flex items-center gap-3">
        <LoadingSpinner size="small" color="blue" inline label="" />
        <div class="text-sm">
          <p class="font-medium">{{ $t('trials.create.checking_title') }}</p>
          <p class="mt-0.5">
            {{
              $t('trials.create.checking_body', {
                model: trialData.llm_model || $t('trials.create.the_model'),
              })
            }}
          </p>
        </div>
      </div>
    </Callout>

    <!-- Inline status line (hidden while submitting — the overlay above takes over) -->
    <div v-else class="mt-6 flex items-center gap-2 text-sm lg:shrink-0">
      <component :is="statusIcon" v-if="statusIcon" :class="['h-4 w-4', statusIconClass]" />
      <p :class="statusTextClass">{{ statusMessage }}</p>
    </div>

    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="tryClose">{{
        $t('trials.create.cancel')
      }}</BaseButton>
      <!-- Defensive: the entry points to this modal are already gated, but a
           viewer must never see a start button that the backend would reject. -->
      <BaseButton
        v-if="canEdit"
        variant="primary"
        :disabled="!canSubmit || submitting"
        :loading="submitting"
        @click="handleStartTrial"
      >
        {{ submitting ? $t('trials.create.verifying') : startTrialLabel }}
      </BaseButton>
    </template>

    <!-- Large-run cost confirmation: every selected document is a separate,
         potentially billable LLM call (mirrors the retry dialog's warning). -->
    <ConfirmationDialog
      :open="showLargeRunConfirm"
      :title="$t('trials.create.large_run.title')"
      :message="$t('trials.create.large_run.message', { count: selectedDocCount.toLocaleString() })"
      :confirm-text="$t('trials.create.start_trial')"
      confirm-variant="primary"
      @confirm="confirmLargeRun"
      @cancel="showLargeRunConfirm = false"
    />

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      :title="$t('trials.create.discard_title')"
      :message="$t('trials.create.discard_message')"
      :confirm-text="$t('trials.create.discard_confirm')"
      :cancel-text="$t('trials.create.discard_cancel')"
      confirm-variant="danger"
      @confirm="confirmDiscard"
      @cancel="showConfirm = false"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, ref, toRef, watch, type Component, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, ChevronDown, CircleAlert, Info, Loader2 } from '@lucide/vue'
import { useToast } from '@/composables/useToast'
import { useProjectAccess } from '@/composables/useProjectAccess'
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
import { checkboxClass } from '@/utils/formStyles'
import { useModelTesting, type TrialFormData } from '@/composables/useModelTesting'
import type { DocumentListItem, Schema, Prompt } from '@/types'

/** Concrete form-data shape (narrower than TrialFormData so v-model children
 *  that expect `string` type-check against non-null fields). */
interface CreateTrialFormData extends TrialFormData {
  name: string
  description: string
  schema_id: string
  prompt_id: string
  document_ids: number[]
  llm_model: string
  api_key: string
  base_url: string
  advanced_options: Record<string, unknown>
}

interface TrialCreatePayload {
  name?: string
  description?: string
  schema_id: number
  prompt_id: number
  document_ids: number[]
  llm_model?: string | null
  api_key?: string
  base_url?: string
  advanced_options?: Record<string, unknown>
}

const toast = useToast()
const { t, locale } = useI18n({ useScope: 'global' })
const { canEdit } = useProjectAccess()

const props = defineProps({
  open: { type: Boolean, required: true },
  documents: { type: Array as PropType<DocumentListItem[]>, required: true }, // kept for compatibility; Individual tab now uses backend pagination
  schemas: { type: Array as PropType<Schema[]>, required: true },
  prompts: { type: Array as PropType<Prompt[]>, default: () => [] },
  projectId: { type: [String, Number] as PropType<string | number>, required: true },
})

const emit = defineEmits<{
  close: []
  /** `done(success)` lets the parent report the API outcome back: on failure
   *  the modal re-enables its form instead of staying stuck in "Verifying…". */
  create: [payload: TrialCreatePayload, done: (success: boolean) => void]
  'create-group': []
}>()

const trialHelpText = t('trials.create.help_text')

/* -------------------------------------------------------
 * General trial state
 * -----------------------------------------------------*/
const trialData = ref<CreateTrialFormData>({
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
const documentSelectionMode = ref<'individual' | 'groups' | 'smart'>('individual')

// Advanced options
const maxCompletionTokens = ref('')
const temperature = ref('')
const reasoningEffort = ref('')
const evidenceMode = ref(false)
// Language of the instructions the backend appends to the prompt. Defaults to
// the UI language: a German prompt over a German report shouldn't be diluted
// with English scaffolding.
const promptLanguage = ref<string>(locale.value)

const advancedSettingsVisible = ref(false)
const advancedOptionsVisible = ref(false)

/* -------------------------------------------------------
 * Getting started: the first-run primer
 * -----------------------------------------------------*/
const INTRO_KEY = 'llmaix.trialIntroDismissed'
const showIntro = ref(false)

function dismissIntro(): void {
  showIntro.value = false
  try {
    localStorage.setItem(INTRO_KEY, '1')
  } catch {
    // Private mode / storage disabled — the primer just returns next time.
  }
}

/* -------------------------------------------------------
 * Model memory — the model is the one required input with no natural default,
 * which is exactly why it gets hunted for. Reuse the last model the project
 * ran, or the only one on offer; never guess between several unknowns.
 * -----------------------------------------------------*/
const lastModelKey = computed(() => `llmaix.lastModel.${props.projectId}`)

function rememberModel(model: string): void {
  try {
    if (model) localStorage.setItem(lastModelKey.value, model)
  } catch {
    /* storage disabled — preselection is a convenience, not a requirement */
  }
}

function preselectModel(models: string[]): void {
  if (trialData.value.llm_model || !models.length) return
  let remembered: string | null
  try {
    remembered = localStorage.getItem(lastModelKey.value)
  } catch {
    remembered = null
  }
  if (remembered && models.includes(remembered)) trialData.value.llm_model = remembered
  else if (models.length === 1) trialData.value.llm_model = models[0]
}

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

// Fill the model in as soon as the list arrives. Also re-baselines the dirty
// check: a preselection the user never touched must not trigger the
// "Discard changes?" prompt when they close the dialog.
watch(availableModels, (models) => {
  preselectModel(models || [])
  initialValues.value.llm_model = trialData.value.llm_model
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
    (trialData.value.document_ids?.length ?? 0) > 0 &&
    trialData.value.llm_model &&
    availableModels.value.length > 0 &&
    hasValidConfig.value
  )
})

/* -------------------------------------------------------
 * Inline status line
 * -----------------------------------------------------*/
const statusMessage = computed(() => {
  if (submitting.value) return t('trials.create.status.verifying')
  if (isTestingModel.value) return modelTestStatus.value.message
  if (!trialData.value.llm_model) return t('trials.create.status.choose_model')
  if (!hasValidConfig.value) return configStatus.value.message
  if ((trialData.value.document_ids?.length ?? 0) === 0)
    return t('trials.create.status.select_documents')
  if (modelTested.value && modelValid.value) return t('trials.create.status.verified_ready')
  if (modelTested.value && !modelValid.value)
    return t('trials.create.status.verification_failed', { message: modelTestStatus.value.message })
  return t('trials.create.status.will_check')
})

const statusIcon = computed<Component | null>(() => {
  if (submitting.value || isTestingModel.value) return Loader2
  if (modelTested.value && modelValid.value && canSubmit.value) return CheckCircle2
  if (modelTested.value && !modelValid.value) return CircleAlert
  return Info
})

const statusIconClass = computed(() => {
  if (submitting.value || isTestingModel.value) return 'text-primary animate-spin'
  if (modelTested.value && modelValid.value && canSubmit.value) return 'text-green-500'
  if (modelTested.value && !modelValid.value) return 'text-red-500'
  return 'text-content-subtle'
})

const statusTextClass = computed(() => {
  if (modelTested.value && modelValid.value && canSubmit.value)
    return 'text-green-700 dark:text-green-400'
  if (modelTested.value && !modelValid.value) return 'text-red-700 dark:text-red-400'
  return 'text-content-muted'
})

/* -------------------------------------------------------
 * Initialize form on open
 * -----------------------------------------------------*/
const initializeForm = (): void => {
  trialData.value = {
    name: '',
    description: '',
    schema_id: props.schemas.length > 0 ? (props.schemas[0]?.id.toString() ?? '') : '',
    prompt_id: props.prompts.length > 0 ? (props.prompts[0]?.id.toString() ?? '') : '',
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
  evidenceMode.value = false
  promptLanguage.value = locale.value
  try {
    showIntro.value = localStorage.getItem(INTRO_KEY) !== '1'
  } catch {
    showIntro.value = true
  }
  resetModelTest()

  snapshotInitialValues()
  testAndLoadModels()
}

/* -------------------------------------------------------
 * Submission (guided: verify model, then create)
 * -----------------------------------------------------*/
const buildFormData = (): TrialCreatePayload => {
  const formData: TrialCreatePayload = {
    name: (trialData.value.name || '').trim() || undefined,
    description: (trialData.value.description || '').trim() || undefined,
    schema_id: parseInt(String(trialData.value.schema_id)),
    prompt_id: parseInt(String(trialData.value.prompt_id)),
    document_ids: trialData.value.document_ids || [],
    llm_model: trialData.value.llm_model,
  }

  if ((trialData.value.api_key || '').trim()) formData.api_key = trialData.value.api_key!.trim()
  if ((trialData.value.base_url || '').trim()) formData.base_url = trialData.value.base_url!.trim()

  const advancedOptions: Record<string, unknown> = {}
  if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
    advancedOptions.max_completion_tokens = parseInt(maxCompletionTokens.value)
  }
  if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
    advancedOptions.temperature = Number(temperature.value)
  }
  if (reasoningEffort.value) {
    advancedOptions.reasoning_effort = reasoningEffort.value
  }
  if (evidenceMode.value) {
    advancedOptions.evidence_mode = true
  }
  if (promptLanguage.value) {
    advancedOptions.prompt_language = promptLanguage.value
  }
  if (Object.keys(advancedOptions).length > 0) {
    formData.advanced_options = advancedOptions
  }

  return formData
}

/* Scale cue + cost guard: the Start button shows how many documents are
 * attached, and runs above the threshold get an explicit confirmation —
 * each document is a separate (potentially billable) LLM call. */
const LARGE_TRIAL_THRESHOLD = 100
const showLargeRunConfirm = ref(false)

const selectedDocCount = computed(() => trialData.value.document_ids?.length ?? 0)

const startTrialLabel = computed(() => {
  const count = selectedDocCount.value
  if (!count) return t('trials.create.start_trial')
  return t('trials.create.start_trial_count', { count: count.toLocaleString() }, count)
})

const handleStartTrial = async (): Promise<void> => {
  if (!canEdit.value || !canSubmit.value || submitting.value) return
  if (selectedDocCount.value > LARGE_TRIAL_THRESHOLD) {
    showLargeRunConfirm.value = true
    return
  }
  await startTrial()
}

const confirmLargeRun = async (): Promise<void> => {
  showLargeRunConfirm.value = false
  await startTrial()
}

const startTrial = async (): Promise<void> => {
  if (!canEdit.value || !canSubmit.value || submitting.value) return

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
    // The model passed verification, so it is worth offering again next time.
    rememberModel(trialData.value.llm_model)
    // Phase 2 — submit. The parent closes the modal on success; on failure it
    // reports back so the form is re-enabled (otherwise Cancel and Start stay
    // disabled behind `submitting` forever).
    emit('create', buildFormData(), (success: boolean) => {
      if (!success) submitting.value = false
    })
  } catch {
    toast.error(t('trials.create.toast.start_failed'))
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
const initialValues = ref<{
  name: string
  description: string
  schema_id: string
  prompt_id: string
  document_ids: number[]
  llm_model: string
  api_key: string
  base_url: string
}>({
  name: '',
  description: '',
  schema_id: '',
  prompt_id: '',
  document_ids: [],
  llm_model: '',
  api_key: '',
  base_url: '',
})

const snapshotInitialValues = (): void => {
  initialValues.value = {
    name: trialData.value.name,
    description: trialData.value.description,
    schema_id: trialData.value.schema_id,
    prompt_id: trialData.value.prompt_id,
    document_ids: [...(trialData.value.document_ids || [])],
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
const tryClose = (): void => {
  if (submitting.value) return
  if (isDirty.value) {
    showConfirm.value = true
  } else {
    emit('close')
  }
}
const confirmDiscard = (): void => {
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

let customSettingsTimeout: ReturnType<typeof setTimeout> | undefined
watch([() => trialData.value.api_key, () => trialData.value.base_url], () => {
  connectionTested.value = false
  connectionValid.value = false
  resetModelTest()

  trialData.value.llm_model = ''
  availableModels.value = []

  // Debounce BOTH branches: while typing, the fields transiently pass through
  // the empty state (e.g. select-all + retype), and an immediate system-config
  // retest on every such keystroke is just as noisy as the custom one.
  // Auto-triggered tests are silent — the inline configStatus line shows the
  // outcome (see useModelTesting).
  if (customSettingsTimeout) clearTimeout(customSettingsTimeout)
  customSettingsTimeout = setTimeout(() => {
    if (hasCustomApiSettings.value) {
      testAndLoadModels(trialData.value.api_key || '', trialData.value.base_url || '')
    } else {
      testAndLoadModels()
    }
  }, 1000)
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
