<template>
  <div class="bg-white border rounded-xl p-6 shadow flex flex-col h-full">
    <div class="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
      <span class="block text-sm font-semibold text-gray-700"
        >Select Documents <span class="text-red-500">*</span></span
      >
      <span class="text-xs text-gray-500">{{ selectedIds.length }} selected</span>
    </div>

    <div class="mb-4">
      <BaseTabGroup v-model="mode" :tabs="tabs" tone="blue" />
    </div>

    <!-- INDIVIDUAL (server-side pagination) -->
    <DocumentIndividualPicker
      v-if="mode === 'individual'"
      v-model:search-term="searchTerm"
      :selected-ids="selectedIds"
      :docs-page="docsPage"
      :total-docs="totalDocs"
      :page-size="pageSize"
      :page="page"
      :is-loading-docs="isLoadingDocs"
      :docs-error="docsError"
      :is-selecting-all="isSelectingAll"
      @toggle="toggleDocumentSelection"
      @select-all="selectAllDocuments"
      @clear="clearDocumentSelection"
      @prev-page="page = Math.max(1, page - 1)"
      @next-page="page = page + 1"
    />

    <!-- GROUPS -->
    <DocumentGroupPicker
      v-else-if="mode === 'groups'"
      :document-groups="documentGroups"
      :loading-groups="loadingGroups"
      :loading-group-docs="loadingGroupDocs"
      :selected-group-id="selectedGroupId"
      @toggle-group="toggleGroupSelection"
    />

    <!-- SMART -->
    <DocumentSmartPicker
      v-else-if="mode === 'smart'"
      :previous-trials="previousTrials"
      :selected-ids="selectedIds"
      :get-doc-label="getDocLabel"
      @load-from-trial="loadDocumentsFromTrial"
      @select-recent="selectRecentDocuments"
      @apply-date-range="applySmartDateRange"
      @clear="clearDocumentSelection"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { trialsApi } from '@/services/trialsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useDocumentPagination } from '@/composables/useDocumentPagination'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import DocumentIndividualPicker from './DocumentIndividualPicker.vue'
import DocumentGroupPicker from './DocumentGroupPicker.vue'
import DocumentSmartPicker from './DocumentSmartPicker.vue'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const mode = defineModel('mode', { type: String, default: 'individual' })
const selectedIds = defineModel('selectedIds', { type: Array, default: () => [] })

// Tab config for BaseTabGroup
const tabs = [
  { label: 'Individual', value: 'individual' },
  { label: 'Groups', value: 'groups' },
  { label: 'Smart', value: 'smart' },
]

const toast = useToast()

/* -------------------------------------------------------
 * Document groups / previous trials
 * -----------------------------------------------------*/
const documentGroups = ref([])
const loadingGroups = ref(false)
const loadingGroupDocs = ref(false)
const selectedGroupId = ref(null)
const previousTrials = ref([])
const isSelectingAll = ref(false)

const loadDocumentGroups = async () => {
  loadingGroups.value = true
  try {
    const response = await documentSetsApi.list(props.projectId)
    documentGroups.value = response.data.items || []
  } catch (error) {
    toast.error('Failed to load document groups')
    console.error(error)
  } finally {
    loadingGroups.value = false
  }
}

const loadPreviousTrials = async () => {
  try {
    const response = await trialsApi.list(props.projectId)
    previousTrials.value = response.data.filter(
      (trial) => trial.status === 'completed' && trial.document_ids.length > 0,
    )
  } catch (error) {
    console.error('Failed to load previous trials:', error)
  }
}

const toggleGroupSelection = async (group) => {
  if (selectedGroupId.value === group.id) {
    selectedGroupId.value = null
    selectedIds.value = []
    return
  }
  selectedGroupId.value = group.id
  loadingGroupDocs.value = true
  try {
    // Document-set list returns summaries (no member documents), so fetch the
    // member IDs via the documents endpoint's `document_set_id` membership filter.
    const ids = await fetchAllDocumentIds({ document_set_id: group.id })
    selectedIds.value = ids
    if (ids.length === 0) {
      toast.warning(`"${group.name}" has no documents`)
    }
  } catch (error) {
    console.error(error)
    toast.error('Failed to load documents for this group')
    selectedIds.value = []
  } finally {
    loadingGroupDocs.value = false
  }
}

const loadDocumentsFromTrial = (trialId) => {
  if (!trialId) return
  const trial = previousTrials.value.find((t) => t.id === parseInt(trialId))
  if (trial) {
    selectedIds.value = [...trial.document_ids]
    toast.success(`Loaded ${trial.document_ids.length} documents from previous trial`)
  }
}

/* -------------------------------------------------------
 * Server-side pagination (Individual) + bulk fetch (Smart)
 * -----------------------------------------------------*/
const {
  docsPage,
  totalDocs,
  pageSize,
  page,
  isLoadingDocs,
  docsError,
  fetchDocuments,
  fetchAllDocumentIds,
  getDocLabel,
  toISODateStart,
  toISODateEndExclusive,
} = useDocumentPagination({
  getProjectId: () => props.projectId,
  getMode: () => mode.value,
  getSearchTerm: () => searchTerm.value,
})

const searchTerm = ref('')

const toggleDocumentSelection = (docId) => {
  const i = selectedIds.value.indexOf(docId)
  if (i === -1) selectedIds.value.push(docId)
  else selectedIds.value.splice(i, 1)
}

const selectAllDocuments = async () => {
  if (isSelectingAll.value) return
  isSelectingAll.value = true
  try {
    // Use the backend to fetch ALL matching IDs (ignores pagination)
    const ids = await fetchAllDocumentIds({ search: searchTerm.value })
    selectedIds.value = Array.from(new Set([...selectedIds.value, ...ids]))
    toast.success(`Selected all ${ids.length} matching documents`)
  } catch (e) {
    console.error(e)
    toast.error('Could not select all documents')
  } finally {
    isSelectingAll.value = false
  }
}

const clearDocumentSelection = () => {
  selectedIds.value = []
}

const selectRecentDocuments = async (days) => {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const ids = await fetchAllDocumentIds({ date_from: cutoff.toISOString() })
  selectedIds.value = ids
  toast.success(`Selected ${ids.length} documents from the last ${days} days`)
}

const applySmartDateRange = async ({ start, end }) => {
  const fromISO = toISODateStart(start)
  const toISO = toISODateEndExclusive(end)
  const ids = await fetchAllDocumentIds({ date_from: fromISO, date_to: toISO })
  selectedIds.value = ids
  toast.success(`Selected ${ids.length} documents in date range`)
}

/* -------------------------------------------------------
 * Debounced search + watchers
 * -----------------------------------------------------*/
let debounceTimer
const debounce = (fn, ms = 350) => {
  return (...args) => {
    if (debounceTimer) window.clearTimeout(debounceTimer)
    debounceTimer = window.setTimeout(() => fn(...args), ms)
  }
}

// when switching tabs
watch(mode, (newMode) => {
  if (newMode === 'individual') fetchDocuments({ reset: true })
  if (newMode === 'groups' && documentGroups.value.length === 0) loadDocumentGroups()
  if (newMode === 'smart' && previousTrials.value.length === 0) loadPreviousTrials()
})

// debounced search for Individual tab
const debouncedSearch = debounce(() => fetchDocuments({ reset: true }), 400)
watch(
  () => searchTerm.value,
  () => {
    if (mode.value === 'individual') debouncedSearch()
  },
)

// react to page changes
watch(
  () => page.value,
  () => {
    if (mode.value === 'individual') fetchDocuments()
  },
)

onMounted(() => {
  if (mode.value === 'individual') fetchDocuments({ reset: true })
})
</script>
