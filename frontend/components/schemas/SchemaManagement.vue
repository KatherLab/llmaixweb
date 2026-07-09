<template>
  <div class="p-6 space-y-6">
    <PageHeader
      title="Schemas &amp; Prompts"
      subtitle="Define the structure and instructions for information extraction"
      :sticky="false"
      class="mb-6"
    />

    <!-- Tab Navigation -->
    <BaseTabGroup v-model="activeSection" :tabs="tabs" class="mb-6">
      <template #tab="{ tab }">
        <span class="flex items-center gap-2">
          <component :is="tab.value === 'schemas' ? Database : MessageSquare" class="h-5 w-5" />
          <span>{{ tab.label }}</span>
          <StatusBadge v-if="tab.badge" color="gray" class="ml-2">{{ tab.badge }}</StatusBadge>
        </span>
      </template>
    </BaseTabGroup>

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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Database, MessageSquare } from '@lucide/vue'
import { schemasApi } from '@/services/schemasApi'
import { promptsApi } from '@/services/promptsApi'
import { useToast } from '@/composables/useToast'
import SchemaListSection from './SchemaListSection.vue'
import PromptListSection from './PromptListSection.vue'
import SchemaFormModal from './SchemaFormModal.vue'
import PromptFormModal from './PromptFormModal.vue'
import SchemaViewModal from './SchemaViewModal.vue'
import PromptViewModal from './PromptViewModal.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { extractErrorMessage } from '@/utils/errors'
import type { Schema, Prompt } from '@/types'

interface Props {
  projectId: string | number
}

const props = defineProps<Props>()

const toast = useToast()

// Tab state
const activeSection = ref<'schemas' | 'prompts'>('schemas')

// Tab config for BaseTabGroup (icons + count badges rendered via the #tab scoped
// slot to keep the Database/MessageSquare icons and StatusBadge styling).
const tabs = computed(() => [
  { label: 'JSON Schemas', value: 'schemas', badge: schemas.value.length || null },
  { label: 'Extraction Prompts', value: 'prompts', badge: prompts.value.length || null },
])

// Schema list state
const schemas = ref<Schema[]>([])
const isLoading = ref(true)
const error = ref('')

// Prompt list state
const prompts = ref<Prompt[]>([])
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
const currentSchema = ref<Schema | null>(null)
const currentPrompt = ref<Prompt | null>(null)
const schemaToDelete = ref<Schema | null>(null)
const promptToDelete = ref<Prompt | null>(null)

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

const viewSchema = (schema: Schema) => {
  currentSchema.value = schema
  showViewModal.value = true
}

const editSchema = (schema: Schema) => {
  currentSchema.value = schema
  showEditModal.value = true
}

const closeSchemaModal = () => {
  showCreateModal.value = false
  showEditModal.value = false
}

const onSchemaCreated = (schema: Schema) => {
  schemas.value.push(schema)
}

const onSchemaUpdated = (schema: Schema) => {
  const index = schemas.value.findIndex((s) => s.id === schema.id)
  if (index !== -1) {
    schemas.value[index] = schema
  }
}

const confirmDelete = (schema: Schema) => {
  schemaToDelete.value = schema
  showDeleteModal.value = true
}

const deleteSchema = async () => {
  const toDelete = schemaToDelete.value
  if (!toDelete) return
  isDeleting.value = true
  try {
    await schemasApi.delete(props.projectId, toDelete.id)
    schemas.value = schemas.value.filter((s) => s.id !== toDelete.id)
    showDeleteModal.value = false
    toast.success(`Schema "${toDelete.schema_name}" deleted successfully`)
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

const viewPrompt = (prompt: Prompt) => {
  currentPrompt.value = prompt
  showViewPromptModal.value = true
}

const editPrompt = (prompt: Prompt) => {
  currentPrompt.value = prompt
  showEditPromptModal.value = true
}

const closePromptModal = () => {
  showCreatePromptModal.value = false
  showEditPromptModal.value = false
}

const onPromptCreated = (prompt: Prompt) => {
  prompts.value.push(prompt)
}

const onPromptUpdated = (prompt: Prompt) => {
  const index = prompts.value.findIndex((p) => p.id === prompt.id)
  if (index !== -1) {
    prompts.value[index] = prompt
  }
}

const confirmDeletePrompt = (prompt: Prompt) => {
  promptToDelete.value = prompt
  showDeletePromptModal.value = true
}

const deletePrompt = async () => {
  const toDelete = promptToDelete.value
  if (!toDelete) return
  isDeleting.value = true
  try {
    await promptsApi.delete(props.projectId, toDelete.id)
    prompts.value = prompts.value.filter((p) => p.id !== toDelete.id)
    showDeletePromptModal.value = false
    toast.success(`Prompt "${toDelete.name}" deleted successfully`)
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
