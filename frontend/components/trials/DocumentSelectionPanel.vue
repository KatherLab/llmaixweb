<template>
  <div
    class="bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-xl p-6 shadow flex flex-col h-full"
  >
    <div class="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
      <span class="block text-sm font-semibold text-slate-700 dark:text-slate-200"
        >Select Documents <span class="text-red-500">*</span></span
      >
      <span class="text-xs text-slate-500 dark:text-slate-400"
        >{{ selectedIds.length }} selected</span
      >
    </div>

    <div class="mb-4">
      <BaseTabGroup v-model="mode" :tabs="tabs" />
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

<script setup lang="ts">
import { onMounted, ref, watch, type PropType } from 'vue'
import { useToast } from '@/composables/useToast'
import { trialsApi } from '@/services/trialsApi'
import { documentSetsApi } from '@/services/documentSetsApi'
import { useDocumentPagination } from '@/composables/useDocumentPagination'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import DocumentIndividualPicker from './DocumentIndividualPicker.vue'
import DocumentGroupPicker from './DocumentGroupPicker.vue'
import DocumentSmartPicker from './DocumentSmartPicker.vue'
import type { DocumentSetSummary, TrialSummary } from '@/types'

/** A previous trial with a guaranteed non-null document_ids list (only
 *  completed trials with documents are forwarded to the Smart picker). */
interface PreviousTrial extends TrialSummary {
  document_ids: number[]
}

type SelectionMode = 'individual' | 'groups' | 'smart'

interface DateRangePayload {
  start: string
  end: string
}

const props = defineProps({
  projectId: {
    type: [String, Number] as PropType<string | number>,
    required: true,
  },
})

const mode = defineModel<SelectionMode>('mode', { default: 'individual' })
const selectedIds = defineModel<number[]>('selectedIds', { default: () => [] })

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
const documentGroups = ref<DocumentSetSummary[]>([])
const loadingGroups = ref(false)
const loadingGroupDocs = ref(false)
const selectedGroupId = ref<number | null>(null)
const previousTrials = ref<PreviousTrial[]>([])
const isSelectingAll = ref(false)

const loadDocumentGroups = async (): Promise<void> => {
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

const loadPreviousTrials = async (): Promise<void> => {
  try {
    const response = await trialsApi.list(props.projectId)
    previousTrials.value = response.data.items.filter(
      (trial: TrialSummary) =>
        trial.status === 'completed' && (trial.document_ids?.length ?? 0) > 0,
    ) as PreviousTrial[]
  } catch (error) {
    console.error('Failed to load previous trials:', error)
  }
}

const toggleGroupSelection = async (group: DocumentSetSummary): Promise<void> => {
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

const loadDocumentsFromTrial = (trialId: string | number): void => {
  if (!trialId) return
  const trial = previousTrials.value.find((t) => t.id === Number(trialId))
  if (trial && trial.document_ids) {
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

const toggleDocumentSelection = (docId: number): void => {
  const i = selectedIds.value.indexOf(docId)
  if (i === -1) selectedIds.value.push(docId)
  else selectedIds.value.splice(i, 1)
}

const selectAllDocuments = async (): Promise<void> => {
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

const clearDocumentSelection = (): void => {
  selectedIds.value = []
}

const selectRecentDocuments = async (days: number): Promise<void> => {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const ids = await fetchAllDocumentIds({ date_from: cutoff.toISOString() })
  selectedIds.value = ids
  toast.success(`Selected ${ids.length} documents from the last ${days} days`)
}

const applySmartDateRange = async ({ start, end }: DateRangePayload): Promise<void> => {
  const fromISO = toISODateStart(start)
  const toISO = toISODateEndExclusive(end)
  const ids = await fetchAllDocumentIds({
    date_from: fromISO,
    date_to: toISO,
  })
  selectedIds.value = ids
  toast.success(`Selected ${ids.length} documents in date range`)
}

/* -------------------------------------------------------
 * Debounced search + watchers
 * -----------------------------------------------------*/
let debounceTimer: ReturnType<typeof setTimeout> | undefined
const debounce = <T extends (...args: never[]) => void>(fn: T, ms = 350): T => {
  return ((...args: never[]) => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => fn(...args), ms)
  }) as T
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
