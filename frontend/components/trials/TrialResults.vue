<template>
  <SlideOver
    v-if="isModal"
    :open="isModal"
    :aria-label="$t('trials.results.aria')"
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
              {{ $t('trials.results.n_results', { count: totalCount }) }}
            </span>
          </div>
          <div
            v-if="trial"
            class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-content-subtle mt-1"
          >
            <span v-if="trial.llm_model">
              <span class="font-medium text-content-muted">{{
                $t('trials.results.model_label')
              }}</span>
              {{ trial.llm_model }}
            </span>
            <span v-if="trial.prompt">
              <span class="font-medium text-content-muted">{{
                $t('trials.results.prompt_label')
              }}</span>
              {{ trial.prompt.name || $t('trials.results.unnamed') }}
            </span>
            <span v-if="trial.document_set">
              <span class="font-medium text-content-muted">{{
                $t('trials.results.set_label')
              }}</span>
              {{ trial.document_set.name || '#' + trial.document_set.id }}
            </span>
            <span v-if="totalUsage.total_tokens">
              <span class="font-medium text-content-muted">{{
                $t('trials.results.tokens_label')
              }}</span>
              {{ totalUsage.total_tokens }}
            </span>
            <button
              type="button"
              class="font-medium text-primary hover:underline"
              @click="openSchemaModal"
            >
              {{ $t('trials.results.schema_button') }}
            </button>
            <button
              type="button"
              class="font-medium text-primary hover:underline"
              @click="openPromptModal"
            >
              {{ $t('trials.results.prompt_button') }}
            </button>
            <button
              v-if="hasFailures"
              type="button"
              class="font-medium text-red-600 dark:text-red-400 hover:underline"
              @click="showErrors = !showErrors"
            >
              {{ hasFailures ? $t('trials.results.n_errors', { count: errorCount }) : '' }}
            </button>
          </div>
        </div>
        <!-- Document / Table view toggle -->
        <BaseSegmentedControl v-if="trial" v-model="viewMode" :options="viewOptions" size="sm" />
        <!-- Document nav -->
        <div v-if="viewMode === 'document'" class="flex items-center gap-1 shrink-0">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="!hasPrev"
            :title="hasPrev ? $t('trials.results.prev_title') : $t('trials.results.first_result')"
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
            :title="hasNext ? $t('trials.results.next_title') : $t('trials.results.last_result')"
            @click="goNext"
          >
            <ChevronRight class="h-4 w-4" />
          </BaseButton>
        </div>
      </div>
    </template>

    <div class="flex flex-col h-full min-h-0">
      <!-- Live progress strip (run still executing) — mirrors TrialDetailPanel -->
      <div v-if="isTrialActive" class="px-6 py-3 border-b border-default bg-surface shrink-0">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2 text-xs" aria-live="polite">
            <span class="font-medium text-content">{{ $t('trials.results.running') }}</span>
            <span class="font-medium text-primary">{{
              $t('trials.detail.docs_progress', { done: docsDone, total: progressTotalDocs })
            }}</span>
            <span class="text-content-muted">{{
              $t('trials.detail.elapsed', { duration: formatDuration(elapsedSeconds) })
            }}</span>
            <span v-if="etaSeconds && etaSeconds > 0" class="text-content-muted">{{
              $t('trials.detail.eta', { duration: formatDuration(etaSeconds) })
            }}</span>
          </div>
          <div
            class="w-full h-1 bg-surface-sunken rounded-full overflow-hidden"
            role="progressbar"
            :aria-label="$t('trials.detail.progress_aria')"
            :aria-valuenow="progressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              class="h-full bg-primary transition-all duration-500"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center flex-1 py-16">
        <LoadingSpinner size="medium" inline label="" />
        <span class="mt-2 text-content-muted">{{ $t('trials.results.loading') }}</span>
      </div>
      <!-- Error -->
      <div v-else-if="error" class="p-6">
        <ErrorBanner :message="error" class="rounded-card" />
      </div>

      <!-- Trial not found -->
      <div v-else-if="!trial" class="flex flex-col items-center justify-center flex-1 py-16">
        <Frown class="h-14 w-14 text-content-subtle" />
        <span class="text-content-muted mt-3">{{ $t('trials.results.not_found') }}</span>
        <BaseButton variant="secondary" class="mt-6" @click="$emit('close')">
          {{ $t('trials.results.return') }}
        </BaseButton>
      </div>

      <!-- No results yet (only when no filters are active — a genuinely empty
           trial. When filters yield nothing, fall through to the 2-pane layout
           so the rail (with its reset affordance) stays visible.) -->
      <div
        v-else-if="results.length === 0 && !resultsLoading && !hasActiveFilters"
        class="flex flex-col items-center justify-center flex-1 py-16"
      >
        <EmptyState :title="$t('trials.results.no_results_title')">
          <p v-if="isTrialActive" class="mt-1 text-sm text-content-subtle">
            {{ $t('trials.results.wait') }}
          </p>
        </EmptyState>
      </div>

      <!-- Main results area: 2-pane document view, or cross-document table view -->
      <div v-else class="flex flex-1 min-h-0">
        <!-- Cross-document table: rows = documents, columns = schema leaf fields -->
        <TrialResultsTable
          v-if="viewMode === 'table'"
          class="flex-1 min-w-0"
          :results="results"
          :schema-definition="schemaDefinitionForTable"
          :current-page="currentPage"
          :total-pages="totalPages"
          :status-label="statusLabel"
          @open-document="openDocumentFromTable"
          @page-change="handlePageChange"
          @reset-filters="resetFilters"
        />
        <!-- Left rail: document list -->
        <aside
          v-if="viewMode === 'document'"
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
                :placeholder="$t('trials.results.search_placeholder')"
                @input="debouncedFetchResults"
              />
              <select
                v-model="statusFilter"
                :class="[selectClass, 'px-2 py-1.5 text-xs w-full']"
                @change="handleFilterChange"
              >
                <option value="">{{ $t('trials.results.all_statuses') }}</option>
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
                    :class="[
                      'h-1.5 w-1.5 rounded-full shrink-0',
                      statusDotClass(r.status as string),
                    ]"
                  />
                  <span class="text-sm text-content truncate flex-1">{{
                    r.document_name ||
                    r.original_file_name ||
                    $t('trials.results.doc_fallback', { id: r.document_id })
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
                <p class="text-xs text-content-subtle">{{ $t('trials.results.no_match') }}</p>
                <button
                  type="button"
                  class="mt-2 text-xs font-medium text-primary hover:underline"
                  @click="resetFilters"
                >
                  {{ $t('trials.results.reset_filters') }}
                </button>
              </div>
            </div>

            <!-- Compact pagination -->
            <div
              class="p-2 border-t border-default flex items-center justify-between gap-1 shrink-0"
            >
              <BaseButton
                variant="ghost"
                size="sm"
                :disabled="currentPage <= 1"
                :aria-label="$t('common.pagination.previous')"
                :title="$t('common.pagination.previous')"
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
                :aria-label="$t('common.pagination.next')"
                :title="$t('common.pagination.next')"
                @click="handlePageChange(currentPage + 1)"
              >
                <ChevronRight class="h-4 w-4" />
              </BaseButton>
            </div>
          </div>
        </aside>

        <!-- Center: main viewer -->
        <div v-if="viewMode === 'document'" class="flex-1 min-w-0 flex flex-col">
          <!-- Rail toggle (for narrow viewports / power users) -->
          <div
            class="flex items-center justify-between px-2 py-1 border-b border-default bg-surface shrink-0"
          >
            <BaseButton
              variant="ghost"
              size="sm"
              :title="
                leftRailOpen ? $t('trials.results.hide_list') : $t('trials.results.show_list')
              "
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
                  hasActiveFilters ? $t('trials.results.no_match') : $t('trials.results.select_doc')
                }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Collapsible error list (toggled from header) -->
      <div
        v-if="hasFailures && showErrors"
        class="border-t border-default bg-surface-muted px-6 py-4 shrink-0"
      >
        <TrialDocumentErrors
          :failures="trialFailures"
          :document-names="failureDocumentNames"
          @select="selectFailureDocument"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between gap-4 w-full">
        <!-- ←/→ hint only applies to the document view; invisible (not removed)
             so the close button keeps its right-aligned position. -->
        <p :class="['text-xs text-content-subtle', viewMode === 'table' ? 'invisible' : '']">
          {{ $t('trials.results.kbd_use') }}
          <kbd class="px-1 py-0.5 bg-surface-sunken rounded">←</kbd> /
          <kbd class="px-1 py-0.5 bg-surface-sunken rounded">→</kbd>
          {{ $t('trials.results.kbd_move') }}
        </p>
        <BaseButton variant="secondary" size="sm" @click="$emit('close')">
          <X class="h-4 w-4" />
          {{ $t('trials.results.close') }}
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
import { ref, onMounted, onUnmounted, computed, watch, type PropType } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { debounce } from 'perfect-debounce'
import { ChevronLeft, ChevronRight, FileText, Frown, PanelLeft, X } from '@lucide/vue'
import { trialsApi } from '@/services/trialsApi'
import { schemasApi } from '@/services/schemasApi'
import { useToast } from '@/composables/useToast'
import { websocketService } from '@/services/websocket'
import { isForProject, mergeWsEntity } from '@/composables/useWsEntityUpdates'
import TrialResultViewer from './TrialResultViewer.vue'
import TrialResultsTable from './TrialResultsTable.vue'
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
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import { extractErrorMessage } from '@/utils/errors'
import { formatDuration } from '@/utils/formatters'
import { selectClass } from '@/utils/formStyles'
import { trialLabel } from '@/utils/trialLabel'
import type {
  Trial,
  TrialResultItem,
  Schema,
  SchemaDefinition,
  Prompt,
  WsTrialUpdate,
  WsMessage,
} from '@/types'

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
const { t } = useI18n({ useScope: 'global' })
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

// --- View mode: one-document viewer vs cross-document table ---
// Persisted per project (mirrors the `llmaix.lastModel.*` pattern).
type ResultsViewMode = 'document' | 'table'
const viewModeKey = computed(() => `llmaix.trialResultsView.${props.projectId}`)

function loadViewMode(): ResultsViewMode {
  try {
    return localStorage.getItem(viewModeKey.value) === 'table' ? 'table' : 'document'
  } catch {
    return 'document'
  }
}

const viewMode = ref<ResultsViewMode>(loadViewMode())

watch(viewMode, (mode) => {
  try {
    localStorage.setItem(viewModeKey.value, mode)
  } catch {
    /* storage disabled — persistence is a convenience, not a requirement */
  }
  // Table columns come from the schema; fetch it if there is no snapshot.
  if (mode === 'table') ensureSchemaLoaded()
})

const viewOptions = computed(() => [
  { label: t('trials.results.view_document'), value: 'document' },
  { label: t('trials.results.view_table'), value: 'table' },
])

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

// Schema definition driving the table view's columns (snapshot preferred, so
// the columns match what the run actually extracted).
const schemaDefinitionForTable = computed<SchemaDefinition | null>(
  () => schemaForModal.value?.schema_definition ?? null,
)

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
  toast.info(t('trials.results.toast.no_loaded_result'))
}

const statusOptions = computed(() => [
  { value: 'success', label: t('trials.results.status_option.success') },
  { value: 'failed', label: t('trials.results.status_option.failed') },
  { value: 'incomplete', label: t('trials.results.status_option.incomplete') },
  { value: 'invalid_json', label: t('trials.results.status_option.invalid_json') },
  { value: 'schema_invalid', label: t('trials.results.status_option.schema_invalid') },
  { value: 'refused', label: t('trials.results.status_option.refused') },
  { value: 'provider_error', label: t('trials.results.status_option.provider_error') },
])

const statusLabels = (): Record<string, string> => ({
  success: t('trials.results.status_label.success'),
  failed: t('trials.results.status_label.failed'),
  incomplete: t('trials.results.status_label.incomplete'),
  invalid_json: t('trials.results.status_label.invalid_json'),
  schema_invalid: t('trials.results.status_label.schema_invalid'),
  refused: t('trials.results.status_label.refused'),
  provider_error: t('trials.results.status_label.provider_error'),
})

const statusLabel = (status: string): string => statusLabels()[status] || (status ? status : '—')

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
    error.value = extractErrorMessage(err, t('trials.results.errors.load_trial'))
  } finally {
    isLoading.value = false
  }
}

// `silent` (live WS-driven refreshes) skips the loading flag so background
// refetches don't flicker the empty state / rail spinner.
const fetchResults = async (silent = false): Promise<void> => {
  if (!silent) resultsLoading.value = true
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
      await fetchResults(silent)
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
    if (!silent) resultsLoading.value = false
  }
}

// --- Live updates (run still executing) ---

const TERMINAL_STATES = ['completed', 'failed', 'cancelled']
// Throttle WS-driven refetches so a fast run doesn't hammer the API.
const LIVE_REFRESH_MS = 2500

const isTrialActive = computed(
  () => !!trial.value && !TERMINAL_STATES.includes(String(trial.value.status)),
)

// Total docs from the WS payload (len(document_ids); 0 for set-based trials).
const wsDocsTotal = ref(0)

// Mirrors TrialDetailPanel's progress presentation.
const progressTotalDocs = computed(() => {
  const t = trial.value
  if (!t) return 0
  if (t.document_ids?.length) return t.document_ids.length
  if (wsDocsTotal.value) return wsDocsTotal.value
  // Set-based trials: estimate from progress, else fall back to results so far.
  if (t.docs_done != null && t.progress) return Math.round(t.docs_done / t.progress)
  return totalCount.value
})
const docsDone = computed(() => {
  const t = trial.value
  if (!t) return 0
  if (t.docs_done != null) return t.docs_done
  if (t.progress != null) return Math.round((t.progress || 0) * progressTotalDocs.value)
  return 0
})
const progressPercent = computed(() =>
  trial.value?.progress != null ? Math.round((trial.value.progress || 0) * 100) : 0,
)
// Re-evaluates on each WS tick (trial.value is reassigned), like TrialDetailPanel.
const elapsedSeconds = computed(() =>
  trial.value?.started_at ? (Date.now() - Date.parse(trial.value.started_at)) / 1000 : 0,
)
const etaSeconds = computed(() => trial.value?.meta?.eta_seconds ?? 0)

let wsTrialUnsubscribe: (() => void) | null = null
let wsConnectedUnsubscribe: (() => void) | null = null
let liveRefreshTimer: ReturnType<typeof setTimeout> | null = null
let lastLiveRefreshAt = 0

// Leading+trailing throttle: refetch at most once per LIVE_REFRESH_MS.
// Preserves currentPage/activeIndex, so the open result isn't yanked away —
// new results simply appear in the rail/pagination.
function refreshResultsThrottled(): void {
  if (liveRefreshTimer) return
  const wait = Math.max(0, lastLiveRefreshAt + LIVE_REFRESH_MS - Date.now())
  liveRefreshTimer = setTimeout(() => {
    liveRefreshTimer = null
    lastLiveRefreshAt = Date.now()
    fetchResults(true)
  }, wait)
}

function stopLiveRefresh(): void {
  if (liveRefreshTimer) {
    clearTimeout(liveRefreshTimer)
    liveRefreshTimer = null
  }
}

// Silent re-fetch of the trial (no full-screen spinner) for authoritative
// status/meta on terminal states and after a WS reconnect.
async function refreshTrialSilently(): Promise<void> {
  try {
    const res = await trialsApi.get(props.projectId, trialId.value, { include_results: false })
    trial.value = res.data
  } catch (err) {
    console.error('Error refreshing trial:', err)
  }
}

function handleTrialUpdate(data: WsMessage): void {
  const update = data as WsTrialUpdate
  if (!isForProject(update, props.projectId)) return
  if (String(update.trial_id) !== String(trialId.value)) return

  if (typeof update.documents_count === 'number' && update.documents_count > 0) {
    wsDocsTotal.value = update.documents_count
  }

  // Merge progress/status into the loaded trial so the header badge and the
  // progress strip update live.
  if (trial.value) {
    trial.value = mergeWsEntity(
      trial.value as unknown as Record<string, unknown>,
      update as Record<string, unknown>,
      trial.value.id,
      'trial_id',
    ) as unknown as Trial
  }

  const isTerminal =
    TERMINAL_STATES.includes(String(update.event || '')) ||
    TERMINAL_STATES.includes(String(update.status || '').toLowerCase())
  if (isTerminal) {
    // Final refetch: authoritative trial (status, failures map) + full results.
    stopLiveRefresh()
    refreshTrialSilently()
    fetchResults(true)
  } else {
    refreshResultsThrottled()
  }
}

function startLiveUpdates(): void {
  wsTrialUnsubscribe = websocketService.onTrialUpdate(handleTrialUpdate)
  // Resync after a WS reconnect — updates emitted while disconnected were missed.
  wsConnectedUnsubscribe = websocketService.subscribe('connected', () => {
    if (!isTrialActive.value) return
    refreshTrialSilently()
    fetchResults(true)
  })
}

function stopLiveUpdates(): void {
  if (wsTrialUnsubscribe) {
    wsTrialUnsubscribe()
    wsTrialUnsubscribe = null
  }
  if (wsConnectedUnsubscribe) {
    wsConnectedUnsubscribe()
    wsConnectedUnsubscribe = null
  }
  stopLiveRefresh()
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
  // In table mode the arrow keys belong to the (scrollable) table.
  if (viewMode.value !== 'document') return
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

// Load the live schema as a fallback when the trial carries no snapshot
// (needed by both the schema modal and the table view's columns).
async function ensureSchemaLoaded(): Promise<void> {
  if (!trial.value?.schema_snapshot && trial.value?.schema_id && !schemaFallback.value) {
    try {
      const res = await schemasApi.get(props.projectId, trial.value.schema_id)
      schemaFallback.value = res.data
    } catch (err) {
      console.error('Failed to load schema for trial:', err)
    }
  }
}

async function openSchemaModal(): Promise<void> {
  await ensureSchemaLoaded()
  showSchemaModal.value = true
}

// Table row click → jump to the document view with that document open.
function openDocumentFromTable(result: TrialResultItem): void {
  const idx = results.value.findIndex((r) => r.id === result.id)
  if (idx !== -1) activeIndex.value = idx
  viewMode.value = 'document'
}

function openPromptModal(): void {
  showPromptModal.value = true
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  startLiveUpdates()
  await fetchTrial()
  if (trial.value) {
    if (viewMode.value === 'table') ensureSchemaLoaded()
    await fetchResults()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  stopLiveUpdates()
})
</script>
