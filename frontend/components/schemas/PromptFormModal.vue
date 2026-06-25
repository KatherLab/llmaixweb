<template>
  <BaseModal
    :open="open"
    size="xl"
    body-class="p-0 flex flex-col min-h-0"
    panel-class="dark:bg-slate-900 dark:border-slate-700"
    header-class="dark:border-slate-700"
    @close="cancelPromptModal"
  >
    <template #header>
      <div class="flex items-center gap-4">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          {{ isEdit ? 'Edit Prompt' : 'Create New Prompt' }}
        </h3>
        <!-- Simple/Advanced Mode Toggle -->
        <div class="flex items-center gap-2 bg-gray-100 dark:bg-slate-800 rounded-lg p-1">
          <button
            type="button"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              !simplePromptMode
                ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-slate-400 hover:text-gray-900',
            ]"
            @click="simplePromptMode = false"
          >
            Advanced
          </button>
          <button
            type="button"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              simplePromptMode
                ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-slate-400 hover:text-gray-900',
            ]"
            @click="simplePromptMode = true"
          >
            Simple
          </button>
        </div>
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
            <label
              for="prompt-name"
              class="block text-sm font-semibold text-gray-800 dark:text-slate-200 mb-1"
              >Prompt Name <span class="text-red-500">*</span></label
            >
            <input
              id="prompt-name"
              v-model="promptForm.name"
              class="block w-full border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg shadow focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-base px-3 py-2"
              :class="{ 'border-red-300': !promptForm.name && isSubmitting }"
              placeholder="e.g., Medical Document Extraction"
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
            <label
              for="prompt-description"
              class="block text-sm font-semibold text-gray-800 dark:text-slate-200 mb-1"
              >Description</label
            >
            <textarea
              id="prompt-description"
              v-model="promptForm.description"
              rows="2"
              class="block w-full border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg shadow focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-base px-3 py-2"
              placeholder="Describe what this prompt is designed to extract..."
            />
          </div>
        </div>

        <!-- Simple Mode Prompt Editor -->
        <div v-if="simplePromptMode" class="space-y-4">
          <div>
            <label
              for="simple-prompt"
              class="block text-sm font-medium text-gray-800 dark:text-slate-200 mb-2"
            >
              Extraction Instruction
            </label>
            <textarea
              id="simple-prompt"
              v-model="promptForm.user_prompt"
              rows="6"
              class="block w-full border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg shadow focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-base px-4 py-3"
              placeholder="Based on the document content, extract these fields:"
              @input="validatePromptPlaceholder"
            />
            <p class="mt-2 text-xs text-gray-600 dark:text-slate-400">
              This will be used as the user prompt. The schema is automatically included.
            </p>
          </div>
        </div>

        <!-- Advanced Mode Prompt Sections -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <!-- Info Banner - Advanced Mode Only -->
          <div class="md:col-span-2">
            <div
              class="flex items-start bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
            >
              <div class="flex-shrink-0 mt-0.5">
                <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clip-rule="evenodd"
                  />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-900 dark:text-blue-300">
                  Document Content Placeholder
                </h3>
                <p class="text-sm text-blue-800 dark:text-blue-300">
                  Use
                  <code
                    class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 rounded font-mono text-xs"
                    >{document_content}</code
                  >
                  in your prompts where you want the document text to be inserted.
                </p>
              </div>
            </div>
          </div>

          <!-- System Prompt -->
          <div>
            <div class="mb-2 flex items-center gap-2">
              <label
                for="system-prompt"
                class="block text-sm font-medium text-gray-800 dark:text-slate-200 flex-1"
                >System Prompt</label
              >
              <StatusBadge
                v-if="promptForm.system_prompt?.includes('{document_content}')"
                color="green"
              >
                <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Contains placeholder
              </StatusBadge>
              <button
                v-if="!hasDocumentContentPlaceholder"
                type="button"
                class="ml-2 px-2 py-0.5 text-xs bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 rounded text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition"
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
              class="block w-full border border-gray-200 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg shadow focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono px-3 py-2 transition"
              :class="{
                'border-amber-300':
                  promptError &&
                  !promptForm.system_prompt?.includes('{document_content}') &&
                  !promptForm.user_prompt?.includes('{document_content}'),
              }"
              placeholder="You are an AI assistant specialized in extracting structured information from documents..."
              @input="validatePromptPlaceholder"
            />
            <div class="flex justify-end mt-2">
              <button
                v-if="promptForm.system_prompt"
                type="button"
                class="px-3 py-1 text-xs font-medium bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-600 text-indigo-600 dark:text-indigo-400"
                @click="togglePreview('system')"
              >
                {{ showPreviewSystem ? 'Hide' : 'Preview' }}
              </button>
            </div>
          </div>

          <!-- User Prompt -->
          <div>
            <div class="mb-2 flex items-center gap-2">
              <label
                for="user-prompt"
                class="block text-sm font-medium text-gray-800 dark:text-slate-200 flex-1"
                >User Prompt</label
              >
              <StatusBadge
                v-if="promptForm.user_prompt?.includes('{document_content}')"
                color="green"
              >
                <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Contains placeholder
              </StatusBadge>
              <button
                v-if="!hasDocumentContentPlaceholder"
                type="button"
                class="ml-2 px-2 py-0.5 text-xs bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 rounded text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition"
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
              class="block w-full border border-gray-200 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded-lg shadow focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono px-3 py-2 transition"
              placeholder="Extract the following information from this document:\n\n{document_content}"
              @input="validatePromptPlaceholder"
            />
            <div class="flex justify-end mt-2">
              <button
                v-if="promptForm.user_prompt"
                type="button"
                class="px-3 py-1 text-xs font-medium bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded hover:bg-gray-50 dark:hover:bg-slate-600 text-indigo-600 dark:text-indigo-400"
                @click="togglePreview('user')"
              >
                {{ showPreviewUser ? 'Hide' : 'Preview' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Preview Section -->
        <div v-if="showPreviewSystem || showPreviewUser" class="mt-4 space-y-4">
          <h4 class="text-sm font-medium text-gray-800 dark:text-slate-200">
            Preview with Sample Document
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-if="showPreviewSystem && promptForm.system_prompt"
              class="bg-gray-50 dark:bg-slate-800 rounded-lg p-4 border border-gray-200 dark:border-slate-700"
            >
              <span
                class="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider"
                >System Message Preview</span
              >
              <div
                class="mt-2 whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-300 font-mono"
              >
                {{ promptForm.system_prompt.replace('{document_content}', sampleDocument) }}
              </div>
            </div>
            <div
              v-if="showPreviewUser && promptForm.user_prompt"
              class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800"
            >
              <span
                class="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider"
                >User Message Preview</span
              >
              <div
                class="mt-2 whitespace-pre-wrap text-sm text-gray-700 dark:text-slate-300 font-mono"
              >
                {{ promptForm.user_prompt.replace('{document_content}', sampleDocument) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Validation Error -->
        <ErrorBanner v-if="promptError" :message="promptError" class="mt-4" />
      </div>

      <!-- Modal Footer -->
      <div
        class="px-6 py-4 bg-gray-50 dark:bg-slate-800 border-t dark:border-slate-700 flex flex-col md:flex-row md:items-center md:justify-between space-y-3 md:space-y-0 md:space-x-3 flex-shrink-0"
      >
        <button
          type="button"
          class="inline-flex items-center px-3 py-2 border border-indigo-100 dark:border-indigo-800 text-sm font-medium rounded-lg text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition"
          @click="useTemplate"
        >
          <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Use Template
        </button>
        <div class="flex space-x-3">
          <BaseButton variant="secondary" @click="cancelPromptModal">Cancel</BaseButton>
          <BaseButton type="submit" :loading="isSubmitting" :disabled="!isPromptValid">
            {{ isEdit ? 'Update' : 'Create' }}
          </BaseButton>
        </div>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { promptsApi } from '@/services/promptsApi'
import { useToast } from 'vue-toastification'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { promptTemplates, sampleDocument } from '@/utils/promptTemplates'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: [String, Number],
    required: true,
  },
  prompt: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'created', 'updated'])

const toast = useToast()

const isEdit = computed(() => !!props.prompt)

const promptError = ref('')
const showPreviewSystem = ref(false)
const showPreviewUser = ref(false)

const systemPromptRef = ref(null)
const userPromptRef = ref(null)

const promptForm = ref({
  name: '',
  description: '',
  system_prompt: '',
  user_prompt: '',
})

const isSubmitting = ref(false)
const simplePromptMode = ref(true)

// Computed property for prompt validation
const isPromptValid = computed(() => {
  if (!promptForm.value.name) return false

  // In simple mode, only check user_prompt
  if (simplePromptMode.value) {
    return promptForm.value.user_prompt && promptForm.value.user_prompt.trim() !== ''
  }

  // Advanced mode validation
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) return false

  const hasPlaceholder =
    (promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))

  return hasPlaceholder
})

const hasDocumentContentPlaceholder = computed(
  () =>
    (promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}')),
)

function insertPlaceholder(type) {
  if (hasDocumentContentPlaceholder.value) return // Defensive, shouldn't show if true.

  let refObj, modelValue, setter
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
    (promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))
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
      refObj.focus()
      const newPos = insertPos + '{document_content}'.length
      refObj.setSelectionRange(newPos, newPos)
    })
  } else {
    setter(modelValue + '{document_content}')
  }
  validatePromptPlaceholder()
}

const validatePromptPlaceholder = () => {
  promptError.value = '' // Clear previous errors

  // In simple mode, just check user_prompt has content
  // Document content is auto-appended by backend
  if (simplePromptMode.value) {
    if (!promptForm.value.user_prompt || !promptForm.value.user_prompt.trim()) {
      promptError.value = 'Please enter an extraction instruction'
      return false
    }
    // In simple mode, system_prompt is empty (schema & document auto-injected by backend)
    promptForm.value.system_prompt = ''
    promptError.value = ''
    return true
  }

  // Advanced mode validation (original)
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) {
    promptError.value = 'At least one prompt (system or user) must be provided'
    return false
  }

  const hasPlaceholder =
    (promptForm.value.system_prompt &&
      promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'))

  if (!hasPlaceholder) {
    promptError.value =
      'The placeholder {document_content} must be present in either system or user prompt'
    return false
  }

  promptError.value = ''
  return true
}

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
      ...promptForm.value,
      project_id: props.projectId,
    })
    emit('created', response.data)
    emit('close')
    resetPromptForm()
    toast.success('Prompt created successfully')
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
    const response = await promptsApi.update(props.projectId, props.prompt.id, promptForm.value)
    emit('updated', response.data)
    emit('close')
    resetPromptForm()
    toast.success('Prompt updated successfully')
  } catch (err) {
    console.error('Failed to update prompt:', err)
    toast.error(extractErrorMessage(err, 'Failed to update prompt'))
  } finally {
    isSubmitting.value = false
  }
}

const togglePreview = (type) => {
  if (type === 'system') {
    showPreviewSystem.value = !showPreviewSystem.value
  } else {
    showPreviewUser.value = !showPreviewUser.value
  }
}

const useTemplate = () => {
  const template = promptTemplates.medical
  promptForm.value = {
    name: template.name,
    description: template.description,
    system_prompt: template.system_prompt,
    user_prompt: template.user_prompt,
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
}

const cancelPromptModal = () => {
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
          name: props.prompt.name,
          description: props.prompt.description || '',
          system_prompt: props.prompt.system_prompt || '',
          user_prompt: props.prompt.user_prompt || '',
        }
      } else {
        // Create mode
        resetPromptForm()
      }
    } else {
      resetPromptForm()
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
