<template>
  <SlideOver
    v-if="isModal"
    :open="isModal"
    aria-label="Trial results"
    body-class="!p-0 overflow-hidden"
    @close="$emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between gap-4 flex-1 min-w-0 pr-8">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="text-base font-semibold text-content truncate">
              {{ trialLabel(trial, Number(trialId)) }}
            </h3>
            <StatusBadge v-if="trial?.status" :status="trial.status" class="shadow-sm" />
            <span
              v-if="trial"
              class="text-[11px] text-content-subtle bg-surface px-2 py-0.5 rounded-full border border-default"
            >
              {{ totalCount }} results
            </span>
          </div>
          <div
            v-if="trial"
            class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-content-subtle mt-1"
          >
            <span v-if="trial.llm_model">
              <span class="font-medium text-content-muted">Model:</span>
              {{ trial.llm_model }}
            </span>
            <span v-if="trial.prompt">
              <span class="font-medium text-content-muted">Prompt:</span>
              {{ trial.prompt.name || '[unnamed]' }}
            </span>
            <span v-if="trial.document_set">
              <span class="font-medium text-content-muted">Set:</span>
              {{ trial.document_set.name || '#' + trial.document_set.id }}
            </span>
            <span v-if="totalUsage.total_tokens">
              <span class="font-medium text-content-muted">Tokens:</span>
              {{ totalUsage.total_tokens }}
            </span>
            <button
              type="button"
              class="font-medium text-primary hover:underline"
              @click="openSchemaModal"
            >
              Schema
            </button>
            <button
              type="button"
              class="font-medium text-primary hover:underline"
              @click="openPromptModal"
            >
              Prompt
            </button>
            <button
              v-if="hasFailures"
              type="button"
              class="font-medium text-red-600 dark:text-red-400 hover:underline"
              @click="showErrors = !showErrors"
            >
              {{ hasFailures ? `${errorCount} errors` : '' }}
            </button>
          </div>
        </div>
        <!-- Document nav -->
        <div class="flex items-center gap-1 shrink-0">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="!hasPrev"
            :title="hasPrev ? 'Previous document (←)' : 'First result'"
            @click="goPrev"
          >
            <ChevronLeft class="h-4 w-4" />
          </BaseButton>
          <span class="text-xs font-medium text-content-muted tabular-nums px-1 whitespace-nowrap">
            {{ activeResult ? globalIndex + 1 : 0 }} / {{ totalCount }}
          </span>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="!hasNext"
            :title="hasNext ? 'Next document (→)' : 'Last result'"
            @click="goNext"
          >
            <ChevronRight class="h-4 w-4" />
          </BaseButton>
        </div>
      </div>
    </template>

    <!-- Loading -->
    <div v-if="isLoading" class="flex flex-col items-center justify-center h-full py-16">
      <LoadingSpinner size="medium" inline label="" />
      <span class="mt-2 text-content-muted">Loading trial results…</span>
    </div>
    <!-- Error -->
    <div v-else-if="error" class="p-6">
      <ErrorBanner :message="error" class="rounded-card" />
    </div>

    <!-- Trial not found -->
    <div v-else-if="!trial" class="flex flex-col items-center justify-center h-full py-16">
      <Frown class="h-14 w-14 text-content-subtle" />
      <span class="text-content-muted mt-3">Trial not found</span>
      <BaseButton variant="secondary" class="mt-6" @click="$emit('close')">
        Return to trials
      </BaseButton>
    </div>

    <!-- No results yet (only when no filters are active — a genuinely empty
         trial. When filters yield nothing, fall through to the 2-pane layout
         so the rail (with its reset affordance) stays visible.) -->
    <div
      v-else-if="results.length === 0 && !resultsLoading && !hasActiveFilters"
      class="flex flex-col items-center justify-center h-full py-16"
    >
      <EmptyState title="No results available for this trial.">
        <p
          v-if="trial.status === 'processing' || trial.status === 'pending'"
          class="mt-1 text-sm text-content-subtle"
        >
          Please wait for the trial to complete.
        </p>
      </EmptyState>
    </div>

    <!-- Main 2-pane layout: doc list + viewer -->
    <div v-else class="flex h-full min-h-0">
      <!-- Left rail: document list -->
      <aside
        :class="[
          'flex flex-col border-r border-default bg-surface-muted/40 shrink-0',
          leftRailOpen ? 'w-64' : 'w-0 -ml-px overflow-hidden',
        ]"
      >
        <div v-show="leftRailOpen" class="flex flex-col h-full min-h-0">
          <!-- Search + status filter -->
          <div class="p-3 border-b border-default space-y-2 shrink-0">
            <SearchInput
              v-model="search"
              placeholder="Search documents…"
              @input="debouncedFetchResults"
            />
            <select
              v-model="statusFilter"
              :class="[selectClass, 'px-2 py-1.5 text-xs w-full']"
              @change="handleFilterChange"
            >
              <option value="">All statuses</option>
              <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <!-- Document list -->
          <div class="flex-1 min-h-0 overflow-y-auto p-2 space-y-0.5">
            <button
              v-for="(r, i) in results"
              :key="r.id"
              type="button"
              :class="[
                'w-full text-left px-3 py-2 rounded-card border-l-2 transition-colors',
                i === activeIndex
                  ? 'bg-primary-soft border-primary'
                  : 'border-transparent hover:bg-surface',
              ]"
              @click="selectIndex(i)"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span
                  :class="['h-1.5 w-1.5 rounded-full shrink-0', statusDotClass(r.status as string)]"
                />
                <span class="text-sm text-content truncate flex-1">{{
                  r.document_name || r.original_file_name || `Document #${r.document_id}`
                }}</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 pl-3.5">
                <span class="text-[10px] uppercase tracking-wide text-content-subtle">
                  {{ statusLabel(r.status as string) }}
                </span>
                <span
                  v-if="
                    r.additional_content?.finish_reason &&
                    r.additional_content.finish_reason !== 'stop'
                  "
                  class="text-[10px] text-content-subtle"
                >
                  · {{ r.additional_content.finish_reason }}
                </span>
              </div>
            </button>
            <div v-if="resultsLoading" class="flex justify-center py-4">
              <LoadingSpinner size="small" inline label="" />
            </div>
            <div
              v-else-if="results.length === 0"
              class="flex flex-col items-center justify-center py-8 px-3 text-center"
            >
              <p class="text-xs text-content-subtle">No results match your filters.</p>
              <button
                type="button"
                class="mt-2 text-xs font-medium text-primary hover:underline"
                @click="resetFilters"
              >
                Reset filters
              </button>
            </div>
          </div>

          <!-- Compact pagination -->
          <div class="p-2 border-t border-default flex items-center justify-between gap-1 shrink-0">
            <BaseButton
              variant="ghost"
              size="sm"
              :disabled="currentPage <= 1"
              @click="handlePageChange(currentPage - 1)"
            >
              <ChevronLeft class="h-4 w-4" />
            </BaseButton>
            <span class="text-xs text-content-muted tabular-nums">
              {{ currentPage }} / {{ totalPages }}
            </span>
            <BaseButton
              variant="ghost"
              size="sm"
              :disabled="currentPage >= totalPages"
              @click="handlePageChange(currentPage + 1)"
            >
              <ChevronRight class="h-4 w-4" />
            </BaseButton>
          </div>
        </div>
      </aside>

      <!-- Center: main viewer -->
      <div class="flex-1 min-w-0 flex flex-col">
        <!-- Rail toggle (for narrow viewports / power users) -->
        <div
          class="flex items-center justify-between px-2 py-1 border-b border-default bg-surface shrink-0"
        >
          <BaseButton
            variant="ghost"
            size="sm"
            :title="leftRailOpen ? 'Hide document list' : 'Show document list'"
            @click="leftRailOpen = !leftRailOpen"
          >
            <PanelLeft class="h-4 w-4" />
          </BaseButton>
        </div>

        <div class="flex-1 min-h-0">
          <TrialResultViewer
            v-if="activeResult"
            :result="activeResult"
            :project-id="props.projectId"
          />
          <div
            v-else
            class="flex flex-col items-center justify-center h-full py-16 text-content-subtle"
          >
            <FileText class="h-10 w-10 mb-2 opacity-40" />
            <p class="text-sm">
              {{
                hasActiveFilters ? 'No results match your filters.' : 'Select a document to view.'
              }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Collapsible error list (toggled from header) -->
    <div
      v-if="hasFailures && showErrors"
      class="border-t border-default bg-surface-muted px-6 py-4"
    >
      <TrialDocumentErrors
        :failures="trialFailures"
        :document-names="failureDocumentNames"
        @select="selectFailureDocument"
      />
    </div>

    <template #footer>
      <div class="flex items-center justify-between gap-4 w-full">
        <p class="text-xs text-content-subtle">
          Use <kbd class="px-1 py-0.5 bg-surface-sunken rounded">←</kbd> /
          <kbd class="px-1 py-0.5 bg-surface-sunken rounded">→</kbd> to move between documents.
        </p>
        <BaseButton variant="secondary" size="sm" @click="$emit('close')">
          <X class="h-4 w-4" />
          Close
        </BaseButton>
      </div>
    </template>

    <!-- Schema / Prompt snapshots (frozen at trial run) -->
    <SchemaViewModal
      :open="showSchemaModal"
      :schema="schemaForModal"
      :is-snapshot="schemaIsSnapshot"
      @close="showSchemaModal = false"
    />
    <PromptViewModal
      :open="showPromptModal"
      :prompt="promptForModal"
      :is-snapshot="promptIsSnapshot"
      @close="showPromptModal = false"
    />
  </SlideOver>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, type PropType } from 'vue'
import { useRoute } from 'vue-router'
import { debounce } from 'perfect-debounce'
import { ChevronLeft, ChevronRight, FileText, Frown, PanelLeft, X } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { schemasApi } from '@/services/schemasApi'
import { useToast } from '@/composables/useToast'
import TrialResultViewer from './TrialResultViewer.vue'
import TrialDocumentErrors from './TrialDocumentErrors.vue'
import SchemaViewModal from '@/components/schemas/SchemaViewModal.vue'
import PromptViewModal from '@/components/schemas/PromptViewModal.vue'
import SlideOver from '@/components/common/SlideOver.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import { extractErrorMessage } from '@/utils/errors'
import { selectClass } from '@/utils/formStyles'
import { trialLabel } from '@/utils/trialLabel'
import type { Trial, TrialResultItem, Schema, Prompt } from '@/types'

interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}

const props = defineProps({
  projectId: { type: [String, Number] as PropType<string | number>, required: true },
  trialId: { type: [String, Number] as PropType<string | number>, required: true },
  isModal: { type: Boolean, default: false },
})
defineEmits<{ close: [] }>()

const route = useRoute()
const toast = useToast()
const trialId = computed(() => props.trialId || parseInt(route.params.trialId as string))

// Trial-level state
const isLoading = ref(true)
const error = ref<string | null>(null)
const trial = ref<Trial | null>(null)

// Results pagination state
const results = ref<TrialResultItem[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(100)
const resultsLoading = ref(false)
const totalUsage = ref<TokenUsage>({
  prompt_tokens: 0,
  completion_tokens: 0,
  total_tokens: 0,
})

// Active document navigation
const activeIndex = ref(0)
const leftRailOpen = ref(true)
const showErrors = ref(false)

// Filters
const search = ref('')
const statusFilter = ref('')

// Schema / Prompt snapshot display
const showSchemaModal = ref(false)
const showPromptModal = ref(false)
const schemaFallback = ref<Schema | null>(null)
const schemaForModal = computed<Schema | null>(
  () => (trial.value?.schema_snapshot as Schema | null) || schemaFallback.value || null,
)
const promptForModal = computed<Prompt | null>(
  () => (trial.value?.prompt_snapshot as Prompt | null) || trial.value?.prompt || null,
)
const schemaIsSnapshot = computed(() => !!trial.value?.schema_snapshot)
const promptIsSnapshot = computed(() => !!trial.value?.prompt_snapshot)

// Failures map stored on trial.meta
const trialFailures = computed<Record<string, string>>(() => {
  const f = trial.value?.meta?.failures
  return f && typeof f === 'object' ? (f as Record<string, string>) : {}
})
const errorCount = computed(() => Object.keys(trialFailures.value).length)
const hasFailures = computed(() => errorCount.value > 0)

// Resolve document names for the error list from the results already loaded
// (failed documents that produced no result simply keep their id label).
const failureDocumentNames = computed<Record<string, string>>(() => {
  const names: Record<string, string> = {}
  for (const r of results.value) {
    const name = r.document_name || r.original_file_name
    if (name) names[String(r.document_id)] = name
  }
  return names
})

// Click on an error entry → select the corresponding result in the viewer.
function selectFailureDocument(documentId: number): void {
  const idx = results.value.findIndex((r) => r.document_id === documentId)
  if (idx !== -1) {
    activeIndex.value = idx
    showErrors.value = false
    return
  }
  toast.info(
    'No loaded result for this document — it may have failed before producing one, or is on another page.',
  )
}

const statusOptions = [
  { value: 'success', label: 'Success' },
  { value: 'failed', label: 'Failed' },
  { value: 'incomplete', label: 'Incomplete' },
  { value: 'invalid_json', label: 'Invalid JSON' },
  { value: 'schema_invalid', label: 'Schema invalid' },
  { value: 'refused', label: 'Refused' },
  { value: 'provider_error', label: 'Provider error' },
]

const STATUS_LABELS: Record<string, string> = {
  success: 'OK',
  failed: 'Error',
  incomplete: 'Incomplete',
  invalid_json: 'Invalid JSON',
  schema_invalid: 'Schema invalid',
  refused: 'Refused',
  provider_error: 'Provider error',
}

const statusLabel = (status: string): string => STATUS_LABELS[status] || (status ? status : '—')

const statusDotClass = (status: string): string => {
  if (status === 'success') return 'bg-green-500'
  if (status === 'incomplete') return 'bg-yellow-500'
  if (status === 'refused') return 'bg-orange-500'
  return 'bg-red-500'
}

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / pageSize.value)))

const activeResult = computed<TrialResultItem | null>(() => {
  if (results.value.length === 0) return null
  const idx = Math.min(activeIndex.value, results.value.length - 1)
  return results.value[idx] ?? null
})

// Global index across pages for the "x / y" indicator
const globalIndex = computed(() => (currentPage.value - 1) * pageSize.value + activeIndex.value)

const hasPrev = computed(() => !(currentPage.value === 1 && activeIndex.value === 0))
const hasNext = computed(
  () => !(currentPage.value >= totalPages.value && activeIndex.value >= results.value.length - 1),
)

// --- Fetch ---

const fetchTrial = async (): Promise<void> => {
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

const fetchResults = async (): Promise<void> => {
  resultsLoading.value = true
  try {
    const params: Record<string, unknown> = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    }
    if (search.value) params.search = search.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await trialsApi.listResults(props.projectId, trialId.value, params)
    results.value = res.data.items || []
    totalCount.value = res.data.total || 0
    if (res.data.total_usage) totalUsage.value = res.data.total_usage
    // Clamp active index + page if we paginated past the end
    const tp = Math.max(1, Math.ceil(totalCount.value / pageSize.value))
    if (currentPage.value > tp) {
      currentPage.value = tp
      await fetchResults()
      return
    }
    if (activeIndex.value > results.value.length - 1) {
      activeIndex.value = Math.max(0, results.value.length - 1)
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
  activeIndex.value = 0
  fetchResults()
}, 300)

function handleFilterChange(): void {
  currentPage.value = 1
  activeIndex.value = 0
  fetchResults()
}

// Whether any filter is currently active (drives the "Reset filters" CTA in
// the empty state, so users are never stranded with no results + no way back).
const hasActiveFilters = computed(() => !!search.value || !!statusFilter.value)

function resetFilters(): void {
  search.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  activeIndex.value = 0
  fetchResults()
}

async function handlePageChange(page: number): Promise<void> {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
  activeIndex.value = 0
  await fetchResults()
}

function selectIndex(i: number): void {
  if (i >= 0 && i < results.value.length) activeIndex.value = i
}

async function goPrev(): Promise<void> {
  if (!hasPrev.value) return
  if (activeIndex.value > 0) {
    activeIndex.value--
    return
  }
  // Cross to previous page
  if (currentPage.value > 1) {
    currentPage.value--
    await fetchResults()
    activeIndex.value = results.value.length - 1
  }
}

async function goNext(): Promise<void> {
  if (!hasNext.value) return
  if (activeIndex.value < results.value.length - 1) {
    activeIndex.value++
    return
  }
  // Cross to next page
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    await fetchResults()
    activeIndex.value = 0
  }
}

// Keyboard navigation: ← / → to move between documents (ignored when focus is
// in an editable field so users can type in search etc.)
function onKeydown(e: KeyboardEvent): void {
  if (!props.isModal) return
  const target = e.target as HTMLElement | null
  const tag = target?.tagName
  const editable =
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable
  if (editable) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    goPrev()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    goNext()
  }
}

async function openSchemaModal(): Promise<void> {
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

function openPromptModal(): void {
  showPromptModal.value = true
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  await fetchTrial()
  if (trial.value) await fetchResults()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>
