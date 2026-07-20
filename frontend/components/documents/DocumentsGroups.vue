<!-- DocumentsGroups.vue -->
<template>
  <div class="space-y-4">
    <!-- Actions Bar -->
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-4">
        <BaseButton variant="primary" @click="showCreateModal = true">
          <Plus class="w-5 h-5" />
          Create Group
        </BaseButton>

        <SearchInput v-model="searchQuery" placeholder="Search groups..." />
      </div>

      <div class="flex items-center space-x-2">
        <span class="text-sm text-content-muted">
          {{ totalCount }} group{{ totalCount !== 1 ? 's' : '' }}
        </span>
      </div>
    </div>

    <!-- Document Groups Table -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="large" />
    </div>

    <div
      v-else-if="serverItems.length === 0"
      class="bg-surface-muted rounded-card p-12 text-center"
    >
      <Layers class="mx-auto h-12 w-12 text-content-subtle" />
      <h3 class="mt-2 text-sm font-medium text-content">No document groups</h3>
      <p class="mt-1 text-sm text-content-muted max-w-md mx-auto">
        {{
          searchQuery
            ? 'Try adjusting your search'
            : 'A group is a named set of documents you can run a trial against. Create one to run an extraction on a specific selection of documents.'
        }}
      </p>
    </div>

    <DataTable
      v-else
      :columns="columns"
      :items="serverItems"
      row-key="id"
      :pagination="tablePagination"
      :show-page-size-selector="false"
      item-label="groups"
      empty-title="No document groups"
      @page-change="handlePageChange"
    >
      <template #cell-name="{ row: group }">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-content">{{ group.name }}</span>
            <span
              v-if="group.is_auto_generated"
              class="inline-flex items-center px-2 py-0.5 rounded-card text-xs font-medium bg-primary-soft text-primary"
              title="Auto-generated during preprocessing"
            >
              Auto
            </span>
          </div>
          <div v-if="group.description" class="text-xs text-content-muted truncate max-w-md">
            {{ group.description }}
          </div>
        </div>
      </template>

      <template #cell-document_count="{ row: group }">
        <span class="text-sm text-content">{{ group.document_count ?? 0 }}</span>
      </template>

      <template #cell-configuration="{ row: group }">
        <span v-if="group.preprocessing_config" class="text-sm text-content">
          {{ group.preprocessing_config.name }}
        </span>
        <span v-else class="text-sm text-content-muted">Mixed</span>
      </template>

      <template #cell-tags="{ row: group }">
        <div class="flex flex-wrap gap-1">
          <span
            v-for="tag in (group.tags || []).slice(0, 5)"
            :key="tag"
            class="inline-flex items-center px-2 py-0.5 rounded-card text-xs font-medium bg-primary-soft text-primary"
          >
            {{ tag }}
          </span>
          <span
            v-if="(group.tags || []).length > 5"
            class="inline-flex items-center px-2 py-0.5 rounded-card text-xs font-medium bg-surface-sunken text-content-muted"
          >
            +{{ group.tags.length - 5 }}
          </span>
        </div>
      </template>

      <template #cell-type="{ row: group }">
        <span
          :class="[
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
            group.is_auto_generated
              ? 'bg-primary-soft text-primary'
              : 'bg-surface-sunken text-content-muted',
          ]"
        >
          {{ group.is_auto_generated ? 'Auto-generated' : 'Manual' }}
        </span>
      </template>

      <template #cell-created_at="{ row: group }">
        <span class="text-sm text-content-muted">
          {{ formatDate(group.created_at) }}
        </span>
      </template>

      <template #row-actions="{ row: group }">
        <BaseButton
          variant="icon"
          tone="blue"
          title="View"
          aria-label="View"
          @click.stop="viewGroup(group as DocumentSetSummary)"
        >
          <Eye class="w-5 h-5" aria-hidden="true" />
        </BaseButton>
        <BaseButton
          v-if="!group.is_auto_generated"
          variant="icon"
          tone="gray"
          title="Edit"
          aria-label="Edit"
          @click.stop="editGroup(group as DocumentSetSummary)"
        >
          <SquarePen class="w-5 h-5" aria-hidden="true" />
        </BaseButton>
        <Tooltip
          :text="
            group.trials_count > 0 ? 'Cannot delete — this group is used by a trial' : 'Delete'
          "
        >
          <BaseButton
            variant="icon"
            tone="red"
            :aria-label="group.trials_count > 0 ? 'Cannot delete - used by trial' : 'Delete'"
            :disabled="group.trials_count > 0"
            @click.stop="deleteGroup(group as DocumentSetSummary)"
          >
            <Trash2 class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
        </Tooltip>
      </template>
    </DataTable>

    <!-- Create/Edit Group Modal -->
    <CreateDocumentGroupModal
      v-if="showCreateModal || editingGroup"
      :open="showCreateModal || !!editingGroup"
      :group="editingGroup"
      :project-id="projectId"
      @close="closeModal"
      @save="handleSaveGroup"
    />

    <!-- View Group Modal -->
    <ViewDocumentGroupModal
      :open="showViewGroup"
      :group="viewingGroup!"
      :project-id="projectId"
      @close="showViewGroup = false"
      @edit="editGroup"
    />

    <!-- Delete Group Confirmation Modal -->
    <ConfirmationDialog
      :open="showDeleteModal"
      title="Delete Document Group"
      :message="deleteMessage"
      confirm-text="Delete"
      :loading="isDeleting"
      @confirm="confirmDeleteGroupAction"
      @cancel="showDeleteModal = false"
    >
      <div v-if="(groupToDelete?.document_count ?? 0) > 0" class="flex items-center -mt-3 mb-2">
        <input
          v-model="deleteDocumentsToo"
          type="checkbox"
          :class="[checkboxClass, 'text-red-600 focus:ring-red-500']"
        />
        <label class="ml-2 text-sm text-content-muted">
          Also delete all documents in this group (if not referenced elsewhere)
        </label>
      </div>
    </ConfirmationDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Eye, Layers, Plus, SquarePen, Trash2 } from '@lucide/vue'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useToast } from '@/composables/useToast'
import { formatDate } from '@/utils/formatters'
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue'
import ViewDocumentGroupModal from './ViewDocumentGroupModal.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'
import DataTable from '@/components/common/DataTable.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import { usePagination } from '@/composables/usePagination'
import { extractErrorMessage } from '@/utils/errors'
import { checkboxClass } from '@/utils/formStyles'
import type { DocumentSetCreate, DocumentSetSummary } from '@/types'

interface Props {
  projectId: string | number
  // Declared for API parity but unused — the component fetches its own sets.
  documentSets?: DocumentSetSummary[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

const toast = useToast()

// State
const searchQuery = ref<string>('')
const showCreateModal = ref<boolean>(false)
const editingGroup = ref<DocumentSetSummary | null>(null)
const viewingGroup = ref<DocumentSetSummary | null>(null)
const showViewGroup = ref<boolean>(false)
const isLoading = ref<boolean>(true)
const serverItems = ref<DocumentSetSummary[]>([])
const totalCount = ref<number>(0)
const itemsPerPage = ref<number>(20)
const pagination = usePagination({
  getTotal: () => totalCount.value,
  pageSize: itemsPerPage.value,
})
const currentPage = pagination.currentPage

// Delete modal state
const showDeleteModal = ref<boolean>(false)
const groupToDelete = ref<DocumentSetSummary | null>(null)
const deleteDocumentsToo = ref<boolean>(false)
const isDeleting = ref<boolean>(false)

// Server-side pagination
const totalPages = pagination.totalPages

// Pagination object for the DataTable (shape: { page, page_size, total, total_pages })
const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: itemsPerPage.value,
  total: totalCount.value,
  total_pages: totalPages.value,
}))

const handlePageChange = (page: number): void => {
  currentPage.value = page
}

const columns = [
  { key: 'name', label: 'Group Name' },
  { key: 'document_count', label: 'Documents' },
  { key: 'configuration', label: 'Configuration' },
  { key: 'tags', label: 'Tags' },
  { key: 'type', label: 'Type' },
  { key: 'created_at', label: 'Created' },
]

const canDeleteGroup = computed<boolean>(() => !isDeleting.value)

// Message for the delete confirmation dialog (includes document count warning)
const deleteMessage = computed<string>(() => {
  if (!groupToDelete.value) return ''
  let msg = `Are you sure you want to delete "${groupToDelete.value.name}"?`
  if (groupToDelete.value.document_count > 0) {
    msg += ` This group contains ${groupToDelete.value.document_count} document(s).`
  }
  return msg
})

// Fetch document sets with server-side pagination + search
const fetchDocumentSets = async (): Promise<void> => {
  isLoading.value = true
  try {
    const { data } = await documentSetsApi.list(props.projectId, {
      include_auto_generated: true,
      search: searchQuery.value || undefined,
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value,
    })

    serverItems.value = data.items || []
    totalCount.value = data.total ?? serverItems.value.length

    // Safety: if we're on a page that no longer exists, pull back to the last page
    if (
      serverItems.value.length === 0 &&
      totalCount.value > 0 &&
      currentPage.value > totalPages.value
    ) {
      currentPage.value = totalPages.value
      await fetchDocumentSets()
    }
  } catch (error) {
    toast.error('Failed to load document groups')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// Methods
const editGroup = (group: DocumentSetSummary): void => {
  editingGroup.value = group
  showCreateModal.value = false
}

const viewGroup = (group: DocumentSetSummary): void => {
  viewingGroup.value = group
  showViewGroup.value = true
}

const deleteGroup = (group: DocumentSetSummary): void => {
  if (group.trials_count > 0) {
    toast.warning('Cannot delete group - it is used by a trial')
    return
  }

  groupToDelete.value = group
  deleteDocumentsToo.value = false
  showDeleteModal.value = true
}

const confirmDeleteGroupAction = async (): Promise<void> => {
  if (!canDeleteGroup.value || !groupToDelete.value) return

  isDeleting.value = true

  try {
    // Use backend cascade delete with query parameter
    const response = await documentSetsApi.delete(
      props.projectId,
      groupToDelete.value.id,
      deleteDocumentsToo.value,
    )

    // Parse response - handle both 200 OK with body and 204 No Content
    const deletedDocs = response.data?.deleted_document_ids || []

    if (deleteDocumentsToo.value) {
      if (deletedDocs.length > 0) {
        toast.success(`Group and ${deletedDocs.length} document(s) deleted`)
      } else {
        // No documents were deleted - they must all be referenced elsewhere
        toast.warning('Group deleted, but documents could not be deleted (referenced elsewhere).')
      }
    } else {
      toast.success('Document group deleted')
    }

    showDeleteModal.value = false
    groupToDelete.value = null
    deleteDocumentsToo.value = false
    emit('refresh')
    currentPage.value = 1
    fetchDocumentSets()
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to delete document group'))
    console.error(error)
  } finally {
    isDeleting.value = false
  }
}

const closeModal = (): void => {
  showCreateModal.value = false
  editingGroup.value = null
}

const handleSaveGroup = async (groupData: DocumentSetCreate): Promise<void> => {
  try {
    if (editingGroup.value) {
      await documentSetsApi.update(props.projectId, editingGroup.value.id, groupData)
      toast.success('Document group updated')
    } else {
      await documentSetsApi.create(props.projectId, groupData)
      toast.success('Document group created')
    }
    closeModal()
    emit('refresh')
    currentPage.value = 1
    fetchDocumentSets()
  } catch (error) {
    toast.error('Failed to save document group')
    console.error(error)
  }
}

// Watch for search query changes (debounced → server-side search)
let searchDebounce: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    currentPage.value = 1
    fetchDocumentSets()
  }, 300)
})

// Watch for page changes
watch([currentPage, itemsPerPage], fetchDocumentSets)

// Lifecycle
onMounted(() => {
  fetchDocumentSets()
})
</script>
