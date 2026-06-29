<template>
  <div class="p-6">
    <!-- Modern Tab Navigation -->
    <div
      class="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 mb-6"
    >
      <div class="border-b border-slate-200 dark:border-slate-700">
        <nav class="-mb-px flex" aria-label="Tabs">
          <button
            :class="[
              activeSection === 'schemas'
                ? 'border-blue-500 text-blue-600 bg-blue-50/50 dark:bg-blue-900/20 dark:text-blue-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600',
              'group relative min-w-0 flex-1 overflow-hidden py-4 px-6 text-sm font-medium text-center border-b-2 hover:bg-slate-50 dark:hover:bg-slate-800 focus:z-10 transition-all duration-200',
            ]"
            @click="activeSection = 'schemas'"
          >
            <div class="flex items-center justify-center space-x-2">
              <Database class="h-5 w-5" />
              <span>JSON Schemas</span>
              <StatusBadge v-if="schemas.length > 0" color="gray" class="ml-2">{{
                schemas.length
              }}</StatusBadge>
            </div>
          </button>

          <button
            :class="[
              activeSection === 'prompts'
                ? 'border-blue-500 text-blue-600 bg-blue-50/50 dark:bg-blue-900/20 dark:text-blue-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600',
              'group relative min-w-0 flex-1 overflow-hidden py-4 px-6 text-sm font-medium text-center border-b-2 hover:bg-slate-50 dark:hover:bg-slate-800 focus:z-10 transition-all duration-200',
            ]"
            @click="activeSection = 'prompts'"
          >
            <div class="flex items-center justify-center space-x-2">
              <MessageSquare class="h-5 w-5" />
              <span>Extraction Prompts</span>
              <StatusBadge v-if="prompts.length > 0" color="gray" class="ml-2">{{
                prompts.length
              }}</StatusBadge>
            </div>
          </button>
        </nav>
      </div>
    </div>

    <!-- Schemas Section -->
    <SchemaListSection
      v-if="activeSection === 'schemas'"
      :schemas="schemas"
      :is-loading="isLoading"
      @create="showCreateModal = true"
      @view="viewSchema"
      @edit="editSchema"
      @delete="confirmDelete"
    />

    <!-- Prompts Section -->
    <PromptListSection
      v-if="activeSection === 'prompts'"
      :prompts="prompts"
      :is-loading="isLoadingPrompts"
      @create="showCreatePromptModal = true"
      @view="viewPrompt"
      @edit="editPrompt"
      @delete="confirmDeletePrompt"
    />

    <!-- Create/Edit Schema Modal -->
    <SchemaFormModal
      :open="showCreateModal || showEditModal"
      :project-id="props.projectId"
      :schema="showEditModal ? currentSchema : null"
      @close="closeSchemaModal"
      @created="onSchemaCreated"
      @updated="onSchemaUpdated"
    />

    <!-- Create/Edit Prompt Modal -->
    <PromptFormModal
      :open="showCreatePromptModal || showEditPromptModal"
      :project-id="props.projectId"
      :prompt="showEditPromptModal ? currentPrompt : null"
      @close="closePromptModal"
      @created="onPromptCreated"
      @updated="onPromptUpdated"
    />

    <!-- View Schema Modal -->
    <SchemaViewModal :open="showViewModal" :schema="currentSchema" @close="showViewModal = false" />

    <!-- View Prompt Modal -->
    <PromptViewModal
      :open="showViewPromptModal"
      :prompt="currentPrompt"
      @close="showViewPromptModal = false"
    />

    <!-- Delete Schema Confirmation -->
    <ConfirmationDialog
      :open="showDeleteModal"
      title="Delete Schema"
      :message="`Are you sure you want to delete the schema &quot;${schemaToDelete?.schema_name}&quot;? This action cannot be undone.`"
      confirm-text="Delete"
      :loading="isDeleting"
      @confirm="deleteSchema"
      @cancel="showDeleteModal = false"
    />

    <!-- Delete Prompt Confirmation -->
    <ConfirmationDialog
      :open="showDeletePromptModal"
      title="Delete Prompt"
      :message="`Are you sure you want to delete the prompt &quot;${promptToDelete?.name}&quot;? This action cannot be undone.`"
      confirm-text="Delete"
      :loading="isDeleting"
      @confirm="deletePrompt"
      @cancel="showDeletePromptModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Database, MessageSquare } from '@lucide/vue'
import { schemasApi } from '@/services/schemasApi'
import { promptsApi } from '@/services/promptsApi'
import { useToast } from 'vue-toastification'
import SchemaListSection from './SchemaListSection.vue'
import PromptListSection from './PromptListSection.vue'
import SchemaFormModal from './SchemaFormModal.vue'
import PromptFormModal from './PromptFormModal.vue'
import SchemaViewModal from './SchemaViewModal.vue'
import PromptViewModal from './PromptViewModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const toast = useToast()

// Tab state
const activeSection = ref('schemas')

// Schema list state
const schemas = ref([])
const isLoading = ref(true)
const error = ref('')

// Prompt list state
const prompts = ref([])
const isLoadingPrompts = ref(false)

// Modal visibility
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showViewModal = ref(false)
const showDeleteModal = ref(false)
const showCreatePromptModal = ref(false)
const showEditPromptModal = ref(false)
const showViewPromptModal = ref(false)
const showDeletePromptModal = ref(false)

// Current items
const currentSchema = ref(null)
const currentPrompt = ref(null)
const schemaToDelete = ref(null)
const promptToDelete = ref(null)

// Delete state
const isDeleting = ref(false)

// --- Fetch ---

const fetchSchemas = async () => {
  isLoading.value = true
  try {
    const response = await schemasApi.list(props.projectId)
    schemas.value = response.data
  } catch (err) {
    error.value = 'Failed to load schemas'
    toast.error('Failed to load schemas. Please try again.')
    console.error(err)
  } finally {
    isLoading.value = false
  }
}

const fetchPrompts = async () => {
  isLoadingPrompts.value = true
  try {
    const response = await promptsApi.list(props.projectId)
    prompts.value = response.data
  } catch (err) {
    console.error('Failed to load prompts:', err)
    toast.error('Failed to load prompts. Please try again.')
  } finally {
    isLoadingPrompts.value = false
  }
}

// --- Schema handlers ---

const viewSchema = (schema) => {
  currentSchema.value = schema
  showViewModal.value = true
}

const editSchema = (schema) => {
  currentSchema.value = schema
  showEditModal.value = true
}

const closeSchemaModal = () => {
  showCreateModal.value = false
  showEditModal.value = false
}

const onSchemaCreated = (schema) => {
  schemas.value.push(schema)
}

const onSchemaUpdated = (schema) => {
  const index = schemas.value.findIndex((s) => s.id === schema.id)
  if (index !== -1) {
    schemas.value[index] = schema
  }
}

const confirmDelete = (schema) => {
  schemaToDelete.value = schema
  showDeleteModal.value = true
}

const deleteSchema = async () => {
  if (!schemaToDelete.value) return
  isDeleting.value = true
  try {
    await schemasApi.delete(props.projectId, schemaToDelete.value.id)
    schemas.value = schemas.value.filter((s) => s.id !== schemaToDelete.value.id)
    showDeleteModal.value = false
    toast.success(`Schema "${schemaToDelete.value.schema_name}" deleted successfully`)
  } catch (err) {
    const errorMessage = extractErrorMessage(err, 'Failed to delete schema')
    toast.error(errorMessage)
    console.error(err)
  } finally {
    isDeleting.value = false
    schemaToDelete.value = null
  }
}

// --- Prompt handlers ---

const viewPrompt = (prompt) => {
  currentPrompt.value = prompt
  showViewPromptModal.value = true
}

const editPrompt = (prompt) => {
  currentPrompt.value = prompt
  showEditPromptModal.value = true
}

const closePromptModal = () => {
  showCreatePromptModal.value = false
  showEditPromptModal.value = false
}

const onPromptCreated = (prompt) => {
  prompts.value.push(prompt)
}

const onPromptUpdated = (prompt) => {
  const index = prompts.value.findIndex((p) => p.id === prompt.id)
  if (index !== -1) {
    prompts.value[index] = prompt
  }
}

const confirmDeletePrompt = (prompt) => {
  promptToDelete.value = prompt
  showDeletePromptModal.value = true
}

const deletePrompt = async () => {
  if (!promptToDelete.value) return
  isDeleting.value = true
  try {
    await promptsApi.delete(props.projectId, promptToDelete.value.id)
    prompts.value = prompts.value.filter((p) => p.id !== promptToDelete.value.id)
    showDeletePromptModal.value = false
    toast.success(`Prompt "${promptToDelete.value.name}" deleted successfully`)
  } catch (err) {
    console.error('Failed to delete prompt:', err)
    const errorMessage = extractErrorMessage(err, 'Failed to delete prompt')
    toast.error(errorMessage)
  } finally {
    isDeleting.value = false
    promptToDelete.value = null
  }
}

// --- Lifecycle ---

onMounted(() => {
  fetchSchemas()
  fetchPrompts()
})
</script>
