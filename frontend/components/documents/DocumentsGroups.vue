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
        <span class="text-sm text-slate-500 dark:text-slate-400">
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
      class="bg-slate-50 dark:bg-slate-800 rounded-lg p-12 text-center"
    >
      <Layers class="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500" />
      <h3 class="mt-2 text-sm font-medium text-slate-900 dark:text-white">No document groups</h3>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {{
          searchQuery
            ? 'Try adjusting your search'
            : 'Create your first group to organize documents'
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
            <span class="text-sm font-medium text-slate-900 dark:text-white">{{ group.name }}</span>
            <span
              v-if="group.is_auto_generated"
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
              title="Auto-generated during preprocessing"
            >
              Auto
            </span>
          </div>
          <div
            v-if="group.description"
            class="text-xs text-slate-500 dark:text-slate-400 truncate max-w-md"
          >
            {{ group.description }}
          </div>
        </div>
      </template>

      <template #cell-document_count="{ row: group }">
        <span class="text-sm text-slate-900 dark:text-white">{{ group.document_count ?? 0 }}</span>
      </template>

      <template #cell-configuration="{ row: group }">
        <span v-if="group.preprocessing_config" class="text-sm text-slate-900 dark:text-white">
          {{ group.preprocessing_config.name }}
        </span>
        <span v-else class="text-sm text-slate-500 dark:text-slate-400">Mixed</span>
      </template>

      <template #cell-tags="{ row: group }">
        <div class="flex flex-wrap gap-1">
          <span
            v-for="tag in (group.tags || []).slice(0, 5)"
            :key="tag"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
          >
            {{ tag }}
          </span>
          <span
            v-if="(group.tags || []).length > 5"
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300"
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
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
              : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300',
          ]"
        >
          {{ group.is_auto_generated ? 'Auto-generated' : 'Manual' }}
        </span>
      </template>

      <template #cell-created_at="{ row: group }">
        <span class="text-sm text-slate-500 dark:text-slate-400">
          {{ formatDate(group.created_at) }}
        </span>
      </template>

      <template #row-actions="{ row: group }">
        <BaseButton
          variant="icon"
          tone="blue"
          title="View"
          aria-label="View"
          @click.stop="viewGroup(group)"
        >
          <Eye class="w-5 h-5" aria-hidden="true" />
        </BaseButton>
        <BaseButton
          v-if="!group.is_auto_generated"
          variant="icon"
          tone="gray"
          title="Edit"
          aria-label="Edit"
          @click.stop="editGroup(group)"
        >
          <SquarePen class="w-5 h-5" aria-hidden="true" />
        </BaseButton>
        <BaseButton
          variant="icon"
          tone="red"
          :title="group.trials_count > 0 ? 'Cannot delete - used by trial' : 'Delete'"
          :aria-label="group.trials_count > 0 ? 'Cannot delete - used by trial' : 'Delete'"
          :disabled="group.trials_count > 0"
          @click.stop="deleteGroup(group)"
        >
          <Trash2 class="w-5 h-5" aria-hidden="true" />
        </BaseButton>
      </template>
    </DataTable>

    <!-- Create/Edit Group Modal -->
    <CreateDocumentGroupModal
      v-if="showCreateModal || editingGroup"
      :group="editingGroup"
      :project-id="projectId"
      @close="closeModal"
      @save="handleSaveGroup"
    />

    <!-- View Group Modal -->
    <ViewDocumentGroupModal
      :open="showViewGroup"
      :group="viewingGroup"
      :project-id="projectId"
      @close="showViewGroup = false"
      @edit="editGroup"
      @view-document="viewDocumentFromGroup"
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
      <div v-if="groupToDelete?.document_count > 0" class="flex items-center -mt-3 mb-2">
        <input
          v-model="deleteDocumentsToo"
          type="checkbox"
          class="h-4 w-4 text-red-600 focus:ring-red-500 border-slate-300 rounded"
        />
        <label class="ml-2 text-sm text-slate-700 dark:text-slate-300">
          Also delete all documents in this group (if not referenced elsewhere)
        </label>
      </div>
    </ConfirmationDialog>
  </div>
</template>

<script setup>
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
import { usePagination } from '@/composables/usePagination'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
  documentSets: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['refresh', 'view-document'])

const toast = useToast()

// State
const searchQuery = ref('')
const showCreateModal = ref(false)
const editingGroup = ref(null)
const viewingGroup = ref(null)
const showViewGroup = ref(false)
const isLoading = ref(true)
const serverItems = ref([])
const totalCount = ref(0)
const itemsPerPage = ref(20)
const pagination = usePagination({
  getTotal: () => totalCount.value,
  pageSize: itemsPerPage.value,
})
const currentPage = pagination.currentPage

// Delete modal state
const showDeleteModal = ref(false)
const groupToDelete = ref(null)
const deleteDocumentsToo = ref(false)
const isDeleting = ref(false)

// Server-side pagination
const totalPages = pagination.totalPages

// Pagination object for the DataTable (shape: { page, page_size, total, total_pages })
const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: itemsPerPage.value,
  total: totalCount.value,
  total_pages: totalPages.value,
}))

const handlePageChange = (page) => {
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

const canDeleteGroup = computed(() => !isDeleting.value)

// Message for the delete confirmation dialog (includes document count warning)
const deleteMessage = computed(() => {
  if (!groupToDelete.value) return ''
  let msg = `Are you sure you want to delete "${groupToDelete.value.name}"?`
  if (groupToDelete.value.document_count > 0) {
    msg += ` This group contains ${groupToDelete.value.document_count} document(s).`
  }
  return msg
})

// Fetch document sets with server-side pagination + search
const fetchDocumentSets = async () => {
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
const editGroup = (group) => {
  editingGroup.value = group
  showCreateModal.value = false
}

const viewGroup = (group) => {
  viewingGroup.value = group
  showViewGroup.value = true
}

const viewDocumentFromGroup = (doc) => {
  emit('view-document', doc)
}

const deleteGroup = (group) => {
  if (group.trials_count > 0) {
    toast.warning('Cannot delete group - it is used by a trial')
    return
  }

  groupToDelete.value = group
  deleteDocumentsToo.value = false
  showDeleteModal.value = true
}

const confirmDeleteGroupAction = async () => {
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
        toast.success(`Group and ${deletedDocs.length} document(s) deleted successfully`)
      } else {
        // No documents were deleted - they must all be referenced elsewhere
        toast.warning('Group deleted, but documents could not be deleted (referenced elsewhere).')
      }
    } else {
      toast.success('Document group deleted successfully')
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

const closeModal = () => {
  showCreateModal.value = false
  editingGroup.value = null
}

const handleSaveGroup = async (groupData) => {
  try {
    if (editingGroup.value) {
      await documentSetsApi.update(props.projectId, editingGroup.value.id, groupData)
      toast.success('Document group updated successfully')
    } else {
      await documentSetsApi.create(props.projectId, groupData)
      toast.success('Document group created successfully')
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
let searchDebounce = null
watch(searchQuery, () => {
  clearTimeout(searchDebounce)
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
