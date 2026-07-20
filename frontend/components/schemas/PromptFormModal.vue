<template>
  <BaseModal
    :open="open"
    size="xl"
    body-class="p-0 flex flex-col min-h-0"
    @close="cancelPromptModal"
  >
    <template #header>
      <div class="flex items-center gap-4">
        <h3 class="text-lg font-semibold text-content">
          {{ isEdit ? 'Edit Prompt' : 'Create New Prompt' }}
        </h3>
        <!-- Simple/Advanced Mode Toggle -->
        <BaseSegmentedControl
          v-model="simplePromptMode"
          :options="[
            { label: 'Simple', value: true },
            { label: 'Advanced', value: false },
          ]"
        />
      </div>
    </template>

    <form
      class="flex flex-col flex-1 min-h-0"
      @submit.prevent="isEdit ? updatePrompt() : createPrompt()"
    >
      <div class="flex-1 overflow-y-auto p-6 space-y-8">
        <!-- Name & Description -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label for="prompt-name" :class="labelClass"
              >Prompt Name <span class="text-red-500">*</span></label
            >
            <input
              id="prompt-name"
              v-model="promptForm.name"
              :class="[
                inputClass,
                { 'border-red-300 dark:border-red-500': !promptForm.name && isSubmitting },
              ]"
              placeholder="e.g., Medical Document Extraction"
              maxlength="100"
              required
            />
            <p
              v-if="!promptForm.name && isSubmitting"
              class="mt-1 text-xs text-red-600 dark:text-red-400"
            >
              This field is required
            </p>
          </div>
          <div>
            <label for="prompt-description" :class="labelClass">Description</label>
            <textarea
              id="prompt-description"
              v-model="promptForm.description"
              rows="2"
              :class="textareaClass"
              maxlength="500"
              placeholder="Describe what this prompt is designed to extract..."
            />
          </div>
        </div>

        <!-- Simple Mode Prompt Editor -->
        <div v-if="simplePromptMode" class="space-y-4">
          <div>
            <label for="simple-prompt" :class="labelClass"> Extraction Instruction </label>
            <textarea
              id="simple-prompt"
              v-model="promptForm.user_prompt"
              rows="6"
              :class="textareaClass"
              placeholder="Based on the document content, extract these fields:"
              @input="validatePromptPlaceholder"
            />
            <p class="mt-2 text-xs text-content-muted">
              This will be used as the user prompt. The document text and the selected schema are
              appended automatically when the trial runs.
            </p>
            <p
              v-if="promptForm.system_prompt"
              class="mt-1 text-xs text-amber-700 dark:text-amber-400"
            >
              This prompt has a system prompt from Advanced mode. It is kept while you edit, but
              will not be saved while Simple mode is selected.
            </p>
            <div class="flex justify-end mt-2">
              <button
                v-if="promptForm.user_prompt"
                type="button"
                class="px-3 py-1 text-xs font-medium bg-surface border border-strong rounded hover:bg-surface-muted text-primary"
                @click="showPreviewSimple = !showPreviewSimple"
              >
                {{ showPreviewSimple ? 'Hide' : 'Preview' }}
              </button>
            </div>
          </div>

          <!-- Simple mode preview: what is actually sent to the model -->
          <div v-if="showPreviewSimple && promptForm.user_prompt" class="space-y-2">
            <h4 class="text-sm font-medium text-content">Preview with Sample Document</h4>
            <p class="text-xs text-content-muted">
              In Simple mode no system message is sent — your instruction becomes the user message,
              with the document and the trial's schema appended:
            </p>
            <div class="bg-primary-soft rounded-card p-4 border border-default">
              <span class="text-xs font-semibold text-primary uppercase tracking-wider"
                >User Message Preview</span
              >
              <div class="mt-2 whitespace-pre-wrap text-sm text-content-muted font-mono">
                {{ simplePreview }}
              </div>
            </div>
          </div>
        </div>

        <!-- Advanced Mode Prompt Sections -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <!-- Info Banner - Advanced Mode Only -->
          <div class="md:col-span-2">
            <Callout variant="info" title="How prompts work" class="p-4">
              <div class="space-y-2">
                <p>
                  <strong>System prompt</strong> — the AI's role and rules (applies to every
                  document). <strong>User prompt</strong> — per-document instructions, where
                  <code class="px-1.5 py-0.5 bg-primary-soft text-primary rounded font-mono text-xs"
                    >{document_content}</code
                  >
                  is replaced with the document text.
                </p>
                <p>
                  <strong>The selected schema is automatically included</strong> when the trial
                  runs, so the model knows which fields to extract. You don't need to paste the
                  schema JSON into your prompt — doing so would duplicate it.
                </p>
              </div>
            </Callout>
          </div>

          <!-- System Prompt -->
          <div>
            <div class="mb-2 flex items-center gap-2">
              <label for="system-prompt" :class="[labelClass, 'flex-1']">System Prompt</label>
              <StatusBadge
                v-if="promptForm.system_prompt?.includes('{document_content}')"
                color="green"
              >
                <Check class="h-3 w-3" />
                Contains placeholder
              </StatusBadge>
              <button
                v-if="!hasDocumentContentPlaceholder"
                type="button"
                class="ml-2 px-2 py-0.5 text-xs bg-primary-soft hover:bg-primary-soft rounded text-primary border border-default transition"
                title="Insert {document_content} at cursor"
                @click="insertPlaceholder('system')"
              >
                + Insert {document_content}
              </button>
            </div>
            <textarea
              id="system-prompt"
              ref="systemPromptRef"
              v-model="promptForm.system_prompt"
              rows="7"
              :class="[
                textareaClass,
                'font-mono',
                {
                  'border-amber-300 dark:border-amber-500':
                    promptError &&
                    !promptForm.system_prompt?.includes('{document_content}') &&
                    !promptForm.user_prompt?.includes('{document_content}'),
                },
              ]"
              placeholder="You are an AI assistant specialized in extracting structured information from documents..."
              @input="validatePromptPlaceholder"
            />
            <div class="flex justify-end mt-2">
              <button
                v-if="promptForm.system_prompt"
                type="button"
                class="px-3 py-1 text-xs font-medium bg-surface border border-strong rounded hover:bg-surface-muted text-primary"
                @click="togglePreview('system')"
              >
                {{ showPreviewSystem ? 'Hide' : 'Preview' }}
              </button>
            </div>
          </div>

          <!-- User Prompt -->
          <div>
            <div class="mb-2 flex items-center gap-2">
              <label for="user-prompt" :class="[labelClass, 'flex-1']">User Prompt</label>
              <StatusBadge
                v-if="promptForm.user_prompt?.includes('{document_content}')"
                color="green"
              >
                <Check class="h-3 w-3" />
                Contains placeholder
              </StatusBadge>
              <button
                v-if="!hasDocumentContentPlaceholder"
                type="button"
                class="ml-2 px-2 py-0.5 text-xs bg-primary-soft hover:bg-primary-soft rounded text-primary border border-default transition"
                title="Insert {document_content} at cursor"
                @click="insertPlaceholder('user')"
              >
                + Insert {document_content}
              </button>
            </div>
            <textarea
              id="user-prompt"
              ref="userPromptRef"
              v-model="promptForm.user_prompt"
              rows="7"
              :class="[textareaClass, 'font-mono']"
              placeholder="Extract the following information from this document:\n\n{document_content}"
              @input="validatePromptPlaceholder"
            />
            <div class="flex justify-end mt-2">
              <button
                v-if="promptForm.user_prompt"
                type="button"
                class="px-3 py-1 text-xs font-medium bg-surface border border-strong rounded hover:bg-surface-muted text-primary"
                @click="togglePreview('user')"
              >
                {{ showPreviewUser ? 'Hide' : 'Preview' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Preview Section (Advanced mode; Simple mode has its own preview above) -->
        <div
          v-if="!simplePromptMode && (showPreviewSystem || showPreviewUser)"
          class="mt-4 space-y-4"
        >
          <h4 class="text-sm font-medium text-content">Preview with Sample Document</h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-if="showPreviewSystem && promptForm.system_prompt"
              class="bg-surface-muted rounded-card p-4 border border-default"
            >
              <span class="text-xs font-semibold text-content-muted uppercase tracking-wider"
                >System Message Preview</span
              >
              <div class="mt-2 whitespace-pre-wrap text-sm text-content-muted font-mono">
                {{ promptForm.system_prompt.replaceAll('{document_content}', sampleDocument) }}
              </div>
            </div>
            <div
              v-if="showPreviewUser && promptForm.user_prompt"
              class="bg-primary-soft rounded-card p-4 border border-default"
            >
              <span class="text-xs font-semibold text-primary uppercase tracking-wider"
                >User Message Preview</span
              >
              <div class="mt-2 whitespace-pre-wrap text-sm text-content-muted font-mono">
                {{ promptForm.user_prompt.replaceAll('{document_content}', sampleDocument) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Validation Error -->
        <ErrorBanner v-if="promptError" :message="promptError" class="mt-4" />
      </div>
    </form>
    <template #footer>
      <div class="flex flex-col md:flex-row md:items-center md:justify-between w-full gap-3">
        <BaseButton variant="secondary" @click="useTemplate">
          <FileText class="h-4 w-4" />
          Use Template
        </BaseButton>
        <div class="flex gap-3">
          <BaseButton variant="secondary" @click="cancelPromptModal">Cancel</BaseButton>
          <BaseButton
            variant="primary"
            :loading="isSubmitting"
            :disabled="!isPromptValid"
            @click="isEdit ? updatePrompt() : createPrompt()"
          >
            {{ isEdit ? 'Update' : 'Create' }}
          </BaseButton>
        </div>
      </div>
    </template>
  </BaseModal>

  <!-- Discard unsaved changes confirmation -->
  <ConfirmationDialog
    :open="showConfirm"
    title="Discard unsaved changes?"
    message="Your prompt edits will be lost."
    confirm-text="Discard"
    cancel-text="Keep editing"
    confirm-variant="danger"
    @confirm="confirmDiscard"
    @cancel="showConfirm = false"
  />

  <!-- Template-overwrite confirmation -->
  <ConfirmationDialog
    :open="showTemplateConfirm"
    title="Apply template?"
    message="Applying the template replaces the current name, description, and prompts."
    confirm-text="Apply template"
    cancel-text="Cancel"
    confirm-variant="warning"
    @confirm="applyTemplate"
    @cancel="showTemplateConfirm = false"
  />
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { Check, FileText } from '@lucide/vue'
import { promptsApi } from '@/services/promptsApi'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import Callout from '@/components/common/Callout.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { inputClass, textareaClass, labelClass } from '@/utils/formStyles'
import { promptTemplates, sampleDocument } from '@/utils/promptTemplates'
import { extractErrorMessage } from '@/utils/errors'
import type { Prompt } from '@/types'

interface Props {
  open: boolean
  projectId: string | number
  prompt?: Prompt | null
}

const props = withDefaults(defineProps<Props>(), {
  prompt: null,
})

const emit = defineEmits<{
  close: []
  created: [prompt: Prompt]
  updated: [prompt: Prompt]
}>()

const toast = useToast()

const isEdit = computed(() => !!props.prompt)

const promptError = ref('')
const showPreviewSystem = ref(false)
const showPreviewUser = ref(false)
const showPreviewSimple = ref(false)

const systemPromptRef = ref<HTMLTextAreaElement | null>(null)
const userPromptRef = ref<HTMLTextAreaElement | null>(null)

const promptForm = ref<{
  name: string
  description: string
  system_prompt: string
  user_prompt: string
}>({
  name: '',
  description: '',
  system_prompt: '',
  user_prompt: '',
})

const isSubmitting = ref(false)
const simplePromptMode = ref(true)

// What Simple mode actually sends: no system message; the instruction becomes
// the user message with the document auto-appended between markers and the
// trial's schema appended after it (mirrors backend _build_messages).
const simplePreview = computed(() => {
  return (
    `${promptForm.value.user_prompt}\n\n` +
    `--- DOCUMENT CONTENT ---\n${sampleDocument}\n--- END DOCUMENT ---\n\n` +
    'Extract the data according to this JSON schema:\n' +
    '```json\n{ …the schema selected when the trial runs… }\n```'
  )
})

// Computed property for prompt validation
const isPromptValid = computed(() => {
  if (!promptForm.value.name) return false

  // In simple mode, only check user_prompt
  if (simplePromptMode.value) {
    return !!promptForm.value.user_prompt && promptForm.value.user_prompt.trim() !== ''
  }

  // Advanced mode validation
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) return false

  const hasPlaceholder =
    (!!promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (!!promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))

  return hasPlaceholder
})

const hasDocumentContentPlaceholder = computed(
  () =>
    (!!promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (!!promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}')),
)

function insertPlaceholder(type: 'system' | 'user') {
  if (hasDocumentContentPlaceholder.value) return // Defensive, shouldn't show if true.

  let refObj: HTMLTextAreaElement | null, modelValue: string, setter: (v: string) => void
  if (type === 'system') {
    refObj = systemPromptRef.value
    modelValue = promptForm.value.system_prompt || ''
    setter = (v) => (promptForm.value.system_prompt = v)
  } else {
    refObj = userPromptRef.value
    modelValue = promptForm.value.user_prompt || ''
    setter = (v) => (promptForm.value.user_prompt = v)
  }

  // If either prompt already has the placeholder, bail
  if (
    (!!promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (!!promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))
  ) {
    return
  }

  // Insert at cursor if focused, else at end
  let insertPos = modelValue.length
  if (refObj && document.activeElement === refObj) {
    insertPos = refObj.selectionStart
    const before = modelValue.slice(0, insertPos)
    const after = modelValue.slice(insertPos)
    setter(before + '{document_content}' + after)
    nextTick(() => {
      refObj!.focus()
      const newPos = insertPos + '{document_content}'.length
      refObj!.setSelectionRange(newPos, newPos)
    })
  } else {
    setter(modelValue + '{document_content}')
  }
  validatePromptPlaceholder()
}

const validatePromptPlaceholder = (): boolean => {
  promptError.value = '' // Clear previous errors

  // In simple mode, just check user_prompt has content
  // Document content is auto-appended by backend
  if (simplePromptMode.value) {
    if (!promptForm.value.user_prompt || !promptForm.value.user_prompt.trim()) {
      promptError.value = 'Please enter an extraction instruction'
      return false
    }
    // NOTE: the system prompt is intentionally NOT cleared here. It stays in
    // memory so toggling Advanced → Simple → Advanced doesn't destroy it; it's
    // only dropped from the payload at save time (see buildPayload).
    promptError.value = ''
    return true
  }

  // Advanced mode validation (original)
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) {
    promptError.value = 'At least one prompt (system or user) must be provided'
    return false
  }

  const hasPlaceholder =
    (!!promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (!!promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))

  if (!hasPlaceholder) {
    promptError.value =
      'The placeholder {document_content} must be present in either system or user prompt'
    return false
  }

  promptError.value = ''
  return true
}

// Payload for save. In Simple mode the system prompt is not part of the
// prompt (schema & document are auto-injected by the backend), so it's
// dropped here — not wiped from the form while editing.
const buildPayload = () => ({
  name: promptForm.value.name,
  description: promptForm.value.description,
  system_prompt: simplePromptMode.value ? '' : promptForm.value.system_prompt,
  user_prompt: promptForm.value.user_prompt,
})

const createPrompt = async () => {
  // Check if name is provided
  if (!promptForm.value.name || promptForm.value.name.trim() === '') {
    toast.error('Prompt name is required')
    return
  }

  // Validate prompts
  if (!validatePromptPlaceholder()) {
    toast.error(promptError.value || 'Please check the prompt requirements')
    return
  }

  isSubmitting.value = true
  try {
    const response = await promptsApi.create(props.projectId, {
      ...buildPayload(),
      project_id: Number(props.projectId),
    })
    emit('created', response.data)
    emit('close')
    resetPromptForm()
    toast.success('Prompt created')
  } catch (err) {
    console.error('Failed to create prompt:', err)
    toast.error(extractErrorMessage(err, 'Failed to create prompt'))
  } finally {
    isSubmitting.value = false
  }
}

const updatePrompt = async () => {
  if (!validatePromptPlaceholder()) {
    toast.error(promptError.value || 'Please check the prompt requirements')
    return
  }

  isSubmitting.value = true
  try {
    const response = await promptsApi.update(props.projectId, props.prompt!.id, buildPayload())
    emit('updated', response.data)
    emit('close')
    resetPromptForm()
    toast.success('Prompt updated')
  } catch (err) {
    console.error('Failed to update prompt:', err)
    toast.error(extractErrorMessage(err, 'Failed to update prompt'))
  } finally {
    isSubmitting.value = false
  }
}

const togglePreview = (type: 'system' | 'user') => {
  if (type === 'system') {
    showPreviewSystem.value = !showPreviewSystem.value
  } else {
    showPreviewUser.value = !showPreviewUser.value
  }
}

// "Use Template" overwrites name/description/both prompts — confirm first
// when the user has already typed anything.
const showTemplateConfirm = ref(false)
const useTemplate = () => {
  const f = promptForm.value
  const hasContent = !!(f.name || f.description || f.system_prompt || f.user_prompt)
  if (hasContent) {
    showTemplateConfirm.value = true
    return
  }
  applyTemplate()
}

const applyTemplate = () => {
  showTemplateConfirm.value = false
  const template = promptTemplates.medical
  if (!template) return
  promptForm.value = {
    name: template.name,
    description: template.description,
    system_prompt: template.system_prompt,
    user_prompt: template.user_prompt,
  }
  // The template uses a system prompt + explicit {document_content} — switch
  // to Advanced mode so nothing it sets is hidden or dropped on save.
  if (template.system_prompt || template.user_prompt.includes('{document_content}')) {
    simplePromptMode.value = false
  }
  validatePromptPlaceholder()
  toast.info('Medical extraction template applied')
}

const resetPromptForm = () => {
  simplePromptMode.value = true // Reset to simple mode
  promptForm.value = {
    name: '',
    description: '',
    system_prompt: '',
    user_prompt: '',
  }
  promptError.value = ''
  showPreviewSystem.value = false
  showPreviewUser.value = false
  showPreviewSimple.value = false
}

// --- Unsaved-changes guard (snapshot compare, same pattern as CreateTrialModal) ---
// Baseline captured after modal-open initialization; only *user* edits count.
const initialSnapshot = ref('')
const currentSnapshot = (): string => JSON.stringify(promptForm.value)
const isDirty = computed(
  () => initialSnapshot.value !== '' && currentSnapshot() !== initialSnapshot.value,
)

const showConfirm = ref(false)
const cancelPromptModal = () => {
  if (isDirty.value) {
    showConfirm.value = true
    return
  }
  emit('close')
}
const confirmDiscard = () => {
  showConfirm.value = false
  emit('close')
}

// Initialize/reset when modal opens/closes
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      if (props.prompt) {
        // Edit mode
        promptForm.value = {
          name: props.prompt.name || '',
          description: props.prompt.description || '',
          system_prompt: props.prompt.system_prompt || '',
          user_prompt: props.prompt.user_prompt || '',
        }
        // Open in Advanced mode when the prompt uses advanced features (a
        // system prompt, or an explicit {document_content} placeholder).
        // Simple mode clears system_prompt in validatePromptPlaceholder, so
        // defaulting an advanced prompt to Simple would silently wipe it.
        const usesAdvanced =
          !!promptForm.value.system_prompt ||
          promptForm.value.user_prompt.includes('{document_content}')
        simplePromptMode.value = !usesAdvanced
      } else {
        // Create mode
        resetPromptForm()
      }
      // Baseline for the unsaved-changes guard: everything written above is
      // initialization, not a user edit.
      initialSnapshot.value = currentSnapshot()
    } else {
      resetPromptForm()
      initialSnapshot.value = ''
    }
  },
)

watch(
  () => promptForm.value.name,
  (newValue) => {
    if (newValue && promptError.value && promptError.value.includes('name')) {
      validatePromptPlaceholder()
    }
  },
)

watch([() => promptForm.value.system_prompt, () => promptForm.value.user_prompt], () => {
  if (promptForm.value.system_prompt || promptForm.value.user_prompt) {
    validatePromptPlaceholder()
  }
})
</script>
