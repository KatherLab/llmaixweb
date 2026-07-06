<template>
  <BaseModal :open="open" size="lg" @close="tryClose">
    <template #header>
      <h3 class="text-lg font-semibold text-content">
        {{ group ? 'Edit Document Group' : 'Create Document Group' }}
      </h3>
    </template>

    <!-- Body -->
    <!-- Group Name -->
    <div class="mb-4">
      <label :class="labelClass"> Group Name <span class="text-red-500">*</span> </label>
      <input
        v-model="formData.name"
        type="text"
        :class="inputClass"
        maxlength="100"
        placeholder="e.g., Q4 Financial Reports"
      />
    </div>

    <!-- Description -->
    <div class="mb-4">
      <label :class="labelClass">Description</label>
      <textarea
        v-model="formData.description"
        rows="3"
        :class="textareaClass"
        maxlength="500"
        placeholder="Describe the purpose of this document group..."
      />
    </div>

    <!-- Tags -->
    <div class="mb-4">
      <label :class="labelClass">Tags</label>
      <div class="flex flex-wrap gap-2 mb-2">
        <StatusBadge
          v-for="(tag, index) in formData.tags"
          :key="index"
          color="blue"
          class="px-3 py-1 text-sm"
        >
          {{ tag }}
          <BaseButton
            variant="link"
            tone="blue"
            class="ml-2"
            aria-label="Remove tag"
            @click="removeTag(index)"
          >
            <X class="h-3 w-3" aria-hidden="true" />
          </BaseButton>
        </StatusBadge>
      </div>
      <div class="flex gap-2">
        <input
          v-model="newTag"
          type="text"
          :class="[inputClass, 'flex-1']"
          placeholder="Add a tag..."
          @keyup.enter="addTag"
        />
        <BaseButton :disabled="!newTag.trim()" variant="primary" @click="addTag"> Add </BaseButton>
      </div>
    </div>

    <!-- Document Selection -->
    <div class="mb-4">
      <div class="flex justify-between items-center mb-2">
        <label :class="labelClass"> Select Documents <span class="text-red-500">*</span> </label>
        <span class="text-sm text-content-muted">
          {{ selectedCount }} selected
          <span v-if="loadingExisting" class="text-content-subtle">(loading existing…)</span>
        </span>
      </div>

      <!-- Search (server-side) -->
      <div class="flex gap-2 mb-2">
        <SearchInput
          v-model="searchTerm"
          placeholder="Search documents..."
          @input="onSearchInput"
        />
      </div>

      <!-- Document List -->
      <div class="border border-default rounded-card overflow-hidden max-h-64 overflow-y-auto">
        <div v-if="searchLoading" class="p-4 text-center text-content-muted">Searching…</div>
        <div v-else-if="searchResults.length === 0" class="p-4 text-center text-content-muted">
          No documents found
        </div>
        <div v-else>
          <div
            v-for="doc in searchResults"
            :key="doc.id"
            :class="[
              'p-3 border-b border-default last:border-b-0 cursor-pointer hover:bg-surface-muted flex items-center',
              { 'bg-primary-soft': isSelected(doc.id) },
            ]"
            @click="toggleDocument(doc.id)"
          >
            <input
              type="checkbox"
              :checked="isSelected(doc.id)"
              :class="[checkboxClass, 'mr-3']"
              readonly
              @click.stop
            />
            <div class="flex-1">
              <div class="font-medium text-sm">
                {{ doc.original_file?.file_name || `Document #${doc.id}` }}
              </div>
              <div class="text-xs text-content-muted">
                Config: {{ doc.preprocessing_config?.name || 'N/A' }} • Created:
                {{ formatDate(doc.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination + bulk actions -->
      <div class="flex items-center justify-between gap-2 mt-2">
        <div class="flex gap-2">
          <BaseButton variant="link" tone="blue" class="text-sm" @click="selectAll">
            Select All Visible
          </BaseButton>
          <span class="text-content-subtle">|</span>
          <BaseButton variant="link" tone="blue" class="text-sm" @click="clearSelection">
            Clear Selection
          </BaseButton>
        </div>
        <div v-if="searchTotalPages > 1" class="flex items-center gap-2">
          <span class="text-xs text-content-muted"> {{ searchPage }}/{{ searchTotalPages }} </span>
          <button
            class="px-2 py-1 text-sm border border-strong text-content rounded-card disabled:opacity-50"
            :disabled="searchPage <= 1"
            @click="prevSearchPage"
          >
            Prev
          </button>
          <button
            class="px-2 py-1 text-sm border border-strong text-content rounded-card disabled:opacity-50"
            :disabled="searchPage >= searchTotalPages"
            @click="nextSearchPage"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <BaseButton variant="secondary" @click="tryClose">Cancel</BaseButton>
      <BaseButton :disabled="!isFormValid" variant="primary" @click="handleSave">
        {{ group ? 'Update' : 'Create' }} Group
      </BaseButton>
    </template>

    <!-- Discard unsaved changes confirmation -->
    <ConfirmationDialog
      :open="showConfirm"
      title="Discard unsaved changes?"
      message="Your changes to this document group will be lost."
      confirm-text="Discard"
      cancel-text="Keep editing"
      confirm-variant="danger"
      @confirm="confirmDiscard"
      @cancel="showConfirm = false"
    />
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { X } from '@lucide/vue'
import { documentsApi } from '@/services/documentsApi'
import { formatDate } from '@/utils/formatters'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { inputClass, textareaClass, labelClass, checkboxClass } from '@/utils/formStyles'
import type { DocumentListItem, DocumentSetSummary, DocumentSetCreate } from '@/types'

interface Props {
  group?: DocumentSetSummary | null
  projectId: string | number
  open: boolean
  selectedDocumentIds?: number[] | null
}

const props = withDefaults(defineProps<Props>(), {
  group: null,
  selectedDocumentIds: null,
})

const emit = defineEmits<{
  close: []
  save: [payload: DocumentSetCreate]
}>()

interface FormData {
  name: string
  description: string
  tags: string[]
}

const formData = ref<FormData>({
  name: '',
  description: '',
  tags: [],
})

const initialFormState = ref<string>('')
const newTag = ref<string>('')

// Selection is held as a Set of document ids so it persists across search pages.
const selectedIds = ref<Set<number>>(new Set())
const selectedCount = computed(() => selectedIds.value.size)

// Server-side paginated search (replaces loading every document into memory).
const searchTerm = ref<string>('')
const searchResults = ref<DocumentListItem[]>([])
const searchTotal = ref<number>(0)
const searchPage = ref<number>(1)
const searchPageSize = ref<number>(50)
const searchLoading = ref<boolean>(false)
const loadingExisting = ref<boolean>(false)

const searchTotalPages = computed<number>(() =>
  searchPageSize.value ? Math.ceil(searchTotal.value / searchPageSize.value) : 1,
)

// Serialize form for dirty check
function serializeForm(data: FormData): string {
  return JSON.stringify({
    name: data.name,
    description: data.description,
    tags: [...data.tags].sort(),
    document_ids: [...selectedIds.value].sort((a, b) => a - b),
  })
}

let searchDebounce: ReturnType<typeof setTimeout> | null = null
const onSearchInput = (): void => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    searchPage.value = 1
    fetchSearch()
  }, 300)
}

const fetchSearch = async (): Promise<void> => {
  searchLoading.value = true
  try {
    const { data } = await documentsApi.list(props.projectId, {
      search: searchTerm.value || undefined,
      limit: searchPageSize.value,
      offset: (searchPage.value - 1) * searchPageSize.value,
      compute_stats: false,
    })
    searchResults.value = data.items || []
    searchTotal.value = data.total ?? searchResults.value.length
  } catch (error) {
    console.error('Failed to search documents:', error)
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const prevSearchPage = (): void => {
  if (searchPage.value > 1) {
    searchPage.value--
    fetchSearch()
  }
}

const nextSearchPage = (): void => {
  if (searchPage.value < searchTotalPages.value) {
    searchPage.value++
    fetchSearch()
  }
}

// In edit mode, pre-select the documents already in this set. Fetched by
// document_set_id (ids only — list items carry no `text`), accumulated across
// pages so selection survives regardless of set size.
const loadExistingSelection = async (): Promise<void> => {
  if (!props.group) return
  loadingExisting.value = true
  try {
    const PAGE = 500
    let offset = 0
    let hasMore = true
    while (hasMore) {
      const { data } = await documentsApi.list(props.projectId, {
        document_set_id: props.group.id,
        limit: PAGE,
        offset,
        compute_stats: false,
      })
      const items = data.items || []
      const next = new Set(selectedIds.value)
      for (const d of items) next.add(d.id)
      selectedIds.value = next
      hasMore = items.length === PAGE
      offset += PAGE
    }
  } catch (error) {
    console.error('Failed to load existing selection:', error)
  } finally {
    loadingExisting.value = false
  }
}

// Setup initial data and save initial state for dirty check
onMounted(async () => {
  if (props.group) {
    formData.value = {
      name: props.group.name,
      description: props.group.description || '',
      tags: [...(props.group.tags || [])],
    }
    await loadExistingSelection()
  } else if (props.selectedDocumentIds && props.selectedDocumentIds.length > 0) {
    const next = new Set(selectedIds.value)
    props.selectedDocumentIds.forEach((id) => next.add(id))
    selectedIds.value = next
  }
  initialFormState.value = serializeForm(formData.value)
  await fetchSearch()
})

// Computed
const isFormValid = computed<boolean>(() => {
  return !!formData.value.name.trim() && selectedIds.value.size > 0
})

const isDirty = computed<boolean>(() => {
  return serializeForm(formData.value) !== initialFormState.value
})

const isSelected = (id: number): boolean => selectedIds.value.has(id)

// Methods
const addTag = (): void => {
  const tag = newTag.value.trim()
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
    newTag.value = ''
  }
}
const removeTag = (index: number): void => {
  formData.value.tags.splice(index, 1)
}
const toggleDocument = (docId: number): void => {
  const next = new Set(selectedIds.value)
  if (next.has(docId)) {
    next.delete(docId)
  } else {
    next.add(docId)
  }
  selectedIds.value = next
}
const selectAll = (): void => {
  const next = new Set(selectedIds.value)
  searchResults.value.forEach((d) => next.add(d.id))
  selectedIds.value = next
}
const clearSelection = (): void => {
  selectedIds.value = new Set()
}

// Close handlers with confirmation if dirty
const showConfirm = ref<boolean>(false)
const tryClose = (): void => {
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
const handleSave = (): void => {
  emit('save', {
    name: formData.value.name.trim(),
    description: formData.value.description.trim(),
    tags: formData.value.tags,
    document_ids: [...selectedIds.value],
  })
}
</script>
