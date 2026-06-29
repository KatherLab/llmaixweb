<template>
  <BaseModal
    v-if="isModal"
    :open="isModal"
    size="3xl"
    panel-class="max-w-[90rem]"
    body-class="!p-6"
    @close="$emit('close')"
  >
    <template #header>
      <h3 class="text-lg font-semibold text-slate-900">Trial Results</h3>
    </template>

    <!-- Loading -->
    <div v-if="isLoading" class="flex flex-col items-center justify-center py-16">
      <span class="mb-3">
        <LoadingSpinner size="medium" inline label="" />
      </span>
      <span class="mt-2 text-slate-500">Loading trial results…</span>
    </div>
    <!-- Error -->
    <ErrorBanner v-else-if="error" :message="error" class="mb-5 rounded-lg" />

    <!-- Content -->
    <template v-else-if="trial">
      <TrialMetaHeader
        :trial="trial"
        :total-usage="totalUsage"
        @open-schema="openSchemaModal"
        @open-prompt="openPromptModal"
      />

      <TrialDocumentErrors :failures="trial?.meta?.failures" />

      <!-- Results table -->
      <EmptyState
        v-if="results.length === 0 && !resultsLoading"
        title="No results available for this trial."
      >
        <p
          v-if="trial.status === 'processing' || trial.status === 'pending'"
          class="mt-1 text-sm text-slate-400 dark:text-slate-500"
        >
          Please wait for the trial to complete.
        </p>
      </EmptyState>

      <template v-else>
        <FilterBar
          v-model:search="search"
          :total-count="totalCount"
          item-label="results"
          search-placeholder="Search document name..."
          :active-filters="activeFilters"
          @search-input="debouncedFetchResults"
          @clear-all="clearFilters"
          @clear-filter="clearFilter"
        >
          <template #filters>
            <select
              v-model="statusFilter"
              class="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
              @change="handleFilterChange"
            >
              <option value="">All Status</option>
              <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </template>
        </FilterBar>

        <DataTable
          :columns="columns"
          :items="results"
          row-key="id"
          expandable
          :expanded-keys="expandedKeys"
          :pagination="tablePagination"
          :page-size-options="[25, 50, 100]"
          item-label="results"
          :loading="resultsLoading"
          empty-title="No results match your filters"
          @expand="toggleExpand"
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        >
          <template #cell-index="{ row }">
            <span class="text-sm font-medium text-slate-500 dark:text-slate-400">{{
              resultIndex(row)
            }}</span>
          </template>

          <template #cell-document="{ row }">
            <div class="min-w-0">
              <span class="text-sm font-medium text-slate-900 dark:text-white truncate">{{
                row.document_name || row.original_file_name || `Document #${row.document_id}`
              }}</span>
              <p
                v-if="row.original_file_name && row.original_file_name !== row.document_name"
                class="text-xs text-slate-400 dark:text-slate-500 italic truncate"
              >
                {{ row.original_file_name }}
              </p>
            </div>
          </template>

          <template #cell-status="{ row }">
            <span
              :class="[
                'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
                statusPillClass(row.status),
              ]"
            >
              {{ statusLabel(row.status) }}
            </span>
          </template>

          <template #cell-finish_reason="{ row }">
            <span
              v-if="
                row.additional_content?.finish_reason &&
                row.additional_content.finish_reason !== 'stop'
              "
              :class="[
                'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded',
                getPillClass('yellow'),
              ]"
            >
              {{ row.additional_content.finish_reason }}
            </span>
            <span v-else class="text-xs text-slate-400 dark:text-slate-500">—</span>
          </template>

          <template #cell-tokens="{ row }">
            <span class="text-sm text-slate-600 dark:text-slate-400">
              {{ row.additional_content?.usage?.total_tokens ?? '—' }}
            </span>
          </template>

          <template #cell-created_at="{ row }">
            <span class="text-sm text-slate-500 dark:text-slate-400">
              {{ formatDateSmart(row.created_at) }}
            </span>
          </template>

          <template #expanded="{ row }">
            <TrialResultDetailPanel :result="row" :project-id="props.projectId" />
          </template>
        </DataTable>
      </template>
    </template>

    <div v-else class="flex flex-col items-center justify-center py-16">
      <Frown class="h-14 w-14 text-slate-300" />
      <span class="text-slate-500 mt-3">Trial not found</span>
      <BaseButton variant="secondary" class="mt-6" @click="$emit('close')">
        Return to trials
      </BaseButton>
    </div>

    <!-- Schema / Prompt snapshots (frozen at trial run) -->
    <TrialSchemaModal
      :open="showSchemaModal"
      :schema="schemaForModal"
      :is-snapshot="schemaIsSnapshot"
      @close="showSchemaModal = false"
    />
    <TrialPromptModal
      :open="showPromptModal"
      :prompt="promptForModal"
      :is-snapshot="promptIsSnapshot"
      @close="showPromptModal = false"
    />
  </BaseModal>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { debounce } from 'perfect-debounce'
import { Frown } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { schemasApi } from '@/services/schemasApi'
import TrialMetaHeader from './TrialMetaHeader.vue'
import TrialDocumentErrors from './TrialDocumentErrors.vue'
import TrialResultDetailPanel from './TrialResultDetailPanel.vue'
import TrialSchemaModal from './TrialSchemaModal.vue'
import TrialPromptModal from './TrialPromptModal.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import DataTable from '@/components/common/DataTable.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import { getPillClass } from '@/utils/statusStyles'
import { formatDateSmart } from '@/utils/formatters'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  trialId: { type: [String, Number], required: true },
  isModal: { type: Boolean, default: false },
})
defineEmits(['close'])

const route = useRoute()
const trialId = computed(() => props.trialId || parseInt(route.params.trialId))

// Trial-level state (for the meta header + failures map)
const isLoading = ref(true)
const error = ref(null)
const trial = ref(null)

// Results pagination state
const results = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const resultsLoading = ref(false)
const expandedKeys = ref([])
const totalUsage = ref({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 })

// Filters
const search = ref('')
const statusFilter = ref('')

// Schema / Prompt snapshot display
const showSchemaModal = ref(false)
const showPromptModal = ref(false)
const schemaFallback = ref(null)
const schemaForModal = computed(() => trial.value?.schema_snapshot || schemaFallback.value || null)
const promptForModal = computed(() => trial.value?.prompt_snapshot || trial.value?.prompt || null)
const schemaIsSnapshot = computed(() => !!trial.value?.schema_snapshot)
const promptIsSnapshot = computed(() => !!trial.value?.prompt_snapshot)

const columns = [
  { key: 'index', label: '#', width: '60px' },
  { key: 'document', label: 'Document' },
  { key: 'status', label: 'Status' },
  { key: 'finish_reason', label: 'Finish' },
  { key: 'tokens', label: 'Tokens' },
  { key: 'created_at', label: 'Created' },
]

// Status → label / pill color
const statusOptions = [
  { value: 'success', label: 'Success' },
  { value: 'failed', label: 'Failed' },
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'invalid_json', label: 'Invalid JSON' },
  { value: 'schema_invalid', label: 'Schema invalid' },
  { value: 'refused', label: 'Refused' },
  { value: 'provider_error', label: 'Provider error' },
]

const STATUS_LABELS = {
  success: 'OK',
  failed: 'Error',
  incomplete: 'Incomplete',
  invalid_json: 'Invalid JSON',
  schema_invalid: 'Schema invalid',
  refused: 'Refused',
  provider_error: 'Provider error',
}

const statusLabel = (status) => STATUS_LABELS[status] || (status ? status : '—')

const statusPillClass = (status) => {
  if (status === 'success') return getPillClass('green')
  if (status === 'incomplete') return getPillClass('yellow')
  if (status === 'refused') return getPillClass('orange')
  // all other failure statuses → red
  return getPillClass('red')
}

const activeFilters = computed(() => {
  const chips = []
  if (search.value) chips.push({ key: 'search', label: `Search: "${search.value}"`, color: 'blue' })
  if (statusFilter.value)
    chips.push({
      key: 'status',
      label: `Status: ${STATUS_LABELS[statusFilter.value] || statusFilter.value}`,
      color: statusFilter.value === 'success' ? 'green' : 'red',
    })
  return chips
})

const tablePagination = computed(() => ({
  page: currentPage.value,
  page_size: pageSize.value,
  total: totalCount.value,
  total_pages: Math.max(1, Math.ceil(totalCount.value / pageSize.value)),
}))

// Global result index (stable across pages) for the "#" column
const resultIndex = (row) => {
  const idxInPage = results.value.findIndex((r) => r.id === row.id)
  if (idxInPage === -1) return ''
  return (currentPage.value - 1) * pageSize.value + idxInPage + 1
}

// --- Fetch ---

const fetchTrial = async () => {
  isLoading.value = true
  error.value = null
  try {
    const res = await trialsApi.get(props.projectId, trialId.value, {
      include_results: false,
    })
    trial.value = res.data
  } catch (err) {
    console.error('Error loading trial:', err)
    error.value = extractErrorMessage(err, 'Failed to load trial data')
  } finally {
    isLoading.value = false
  }
}

const fetchResults = async () => {
  resultsLoading.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    }
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await trialsApi.listResults(props.projectId, trialId.value, params)
    results.value = res.data.items || []
    totalCount.value = res.data.total || 0
    if (res.data.total_usage) totalUsage.value = res.data.total_usage
    // Clamp page if we paginated past the end
    const totalPages = Math.max(1, Math.ceil(totalCount.value / pageSize.value))
    if (currentPage.value > totalPages) {
      currentPage.value = totalPages
      await fetchResults()
    }
  } catch (err) {
    console.error('Error loading results:', err)
    results.value = []
    totalCount.value = 0
  } finally {
    resultsLoading.value = false
  }
}

const debouncedFetchResults = debounce(() => {
  currentPage.value = 1
  fetchResults()
}, 300)

function handleFilterChange() {
  currentPage.value = 1
  fetchResults()
}

function handlePageChange(page) {
  currentPage.value = page
  expandedKeys.value = []
  fetchResults()
}

function handlePageSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  expandedKeys.value = []
  fetchResults()
}

function toggleExpand(id) {
  const idx = expandedKeys.value.indexOf(id)
  if (idx > -1) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(id)
  }
}

function clearFilters() {
  search.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  fetchResults()
}

function clearFilter(key) {
  if (key === 'search') search.value = ''
  else if (key === 'status') statusFilter.value = ''
  currentPage.value = 1
  fetchResults()
}

async function openSchemaModal() {
  if (!trial.value?.schema_snapshot && trial.value?.schema_id && !schemaFallback.value) {
    try {
      const res = await schemasApi.get(props.projectId, trial.value.schema_id)
      schemaFallback.value = res.data
    } catch (err) {
      console.error('Failed to load schema for trial:', err)
    }
  }
  showSchemaModal.value = true
}

function openPromptModal() {
  showPromptModal.value = true
}

onMounted(async () => {
  await fetchTrial()
  if (trial.value) fetchResults()
})
</script>
