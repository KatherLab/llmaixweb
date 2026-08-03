<template>
  <div class="flex flex-col h-full min-h-0 bg-surface">
    <!-- Document header bar -->
    <div
      class="flex items-center justify-between gap-3 px-5 py-3 border-b border-default bg-surface-muted/60 shrink-0"
    >
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <h3 class="text-sm font-semibold text-content truncate">
            {{ documentLabel }}
          </h3>
          <span
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded shrink-0',
              statusPillClass(activeResult.status as string),
            ]"
          >
            {{ statusLabel(activeResult.status as string) }}
          </span>
          <span
            v-if="additionalContent?.finish_reason && additionalContent.finish_reason !== 'stop'"
            :class="[
              'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded shrink-0',
              getPillClass('yellow'),
            ]"
          >
            {{ additionalContent.finish_reason }}
          </span>
        </div>
        <div class="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-content-subtle mt-1">
          <span v-if="tokenUsage !== '—'">
            <span class="font-medium text-content-muted">{{
              $t('trials.viewer.tokens_label')
            }}</span>
            {{ tokenUsage }}
          </span>
          <span>
            <span class="font-medium text-content-muted">{{
              $t('trials.viewer.created_label')
            }}</span>
            {{ formatDateSmart(activeResult.created_at) }}
          </span>
          <span v-if="activeResult.original_file_name" class="truncate max-w-[24rem]">
            <span class="font-medium text-content-muted">{{ $t('trials.viewer.file_label') }}</span>
            {{ activeResult.original_file_name }}
          </span>
        </div>
      </div>
    </div>

    <!-- Error banner (failed docs — shown above the split, replaces Result tab) -->
    <div v-if="!activeResult.result || additionalContent?.json_error" class="px-5 pt-4 shrink-0">
      <ErrorBanner class="rounded-card text-sm">
        <div class="font-semibold mb-1">{{ $t('trials.viewer.no_structured_result') }}</div>
        <div v-if="additionalContent?.user_guidance?.user_message" class="mb-1">
          {{ additionalContent.user_guidance.user_message }}
        </div>
        <div v-else-if="additionalContent?.json_error" class="mb-1">
          {{ $t('trials.viewer.parser_error', { error: additionalContent.json_error }) }}
        </div>
        <details v-if="additionalContent?.tuning_advice" class="mt-2">
          <summary class="cursor-pointer text-content-muted">
            {{ $t('trials.viewer.tuning_advice') }}
          </summary>
          <ul class="list-disc list-inside mt-1 text-content-muted">
            <li v-for="(rec, i) in additionalContent.tuning_advice.recommendations" :key="i">
              <span class="font-medium">{{ rec.action }}</span>
              <span v-if="rec.suggested_value">
                → <code>{{ rec.suggested_value }}</code></span
              >
              <span v-if="rec.rationale"> — {{ rec.rationale }}</span>
            </li>
          </ul>
        </details>
      </ErrorBanner>
    </div>

    <!-- Panel layout: toggle chips add/remove panes (Source, Result, Reasoning, Metadata) -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <PanelLayout
        :panels="availablePanels"
        :model-value="activePanels"
        :max-visible="3"
        @update:model-value="activePanels = $event"
      >
        <!-- Source document (original file or extracted text) -->
        <template #pane-source>
          <div class="flex flex-col h-full min-h-0">
            <div
              class="flex items-center justify-between gap-2 px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <h4 class="flex items-center gap-2 text-sm font-semibold text-content-muted">
                <FileText class="h-4 w-4" /> {{ $t('trials.viewer.source_document') }}
              </h4>
              <div class="flex items-center gap-2">
                <BaseSegmentedControl
                  v-if="hasProvenance"
                  v-model="highlightMode"
                  size="sm"
                  :options="highlightModeOptions"
                  :aria-label="$t('trials.provenance.mode_label')"
                />
                <button
                  v-if="hasPreviewableFile"
                  class="text-xs text-primary hover:underline"
                  @click="toggleOriginalView"
                >
                  {{
                    showOriginal
                      ? $t('trials.viewer.show_extracted')
                      : $t('trials.viewer.show_original')
                  }}
                </button>
              </div>
            </div>

            <!-- Selection bar: which value is being traced, how it was found,
                 and a stepper when the value occurs more than once. -->
            <div
              v-if="selectedLeaf && highlightMode !== 'off'"
              class="flex items-center gap-2 px-3 py-1.5 border-b border-default bg-surface text-xs shrink-0"
            >
              <span class="font-medium text-content truncate">{{ selectedLeaf.label }}</span>
              <span
                v-if="selectedKind"
                class="inline-flex items-center gap-1 shrink-0 text-content-muted"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="selectedDotClass" />
                {{ $t(PROVENANCE_STYLES[selectedKind].labelKey) }}
              </span>
              <!-- Nothing is shown for a value the search could not place: see
                   jsonAnnotations. The model's own note, when there is one, is
                   labelled as a note — it is a claim, not a citation. -->
              <span v-if="selectedNote" class="min-w-0 truncate text-content-muted">
                <span class="text-content-subtle">{{ $t('trials.provenance.note_label') }}:</span>
                {{ selectedNote }}
              </span>
              <div
                v-if="selectedMatches.length > 1"
                class="flex items-center gap-1 ml-auto shrink-0"
              >
                <span class="tabular-nums text-content-muted">
                  {{ activeMatchIndex + 1 }} / {{ selectedMatches.length }}
                </span>
                <BaseButton
                  variant="icon"
                  size="sm"
                  :title="$t('trials.provenance.prev_match')"
                  @click="stepMatch(-1)"
                >
                  <ChevronUp class="h-3.5 w-3.5" />
                </BaseButton>
                <BaseButton
                  variant="icon"
                  size="sm"
                  :title="$t('trials.provenance.next_match')"
                  @click="stepMatch(1)"
                >
                  <ChevronDown class="h-3.5 w-3.5" />
                </BaseButton>
              </div>
              <BaseButton
                variant="icon"
                size="sm"
                :class="selectedMatches.length > 1 ? '' : 'ml-auto'"
                :title="$t('trials.provenance.clear_selection')"
                @click="clearSelection"
              >
                <X class="h-3.5 w-3.5" />
              </BaseButton>
            </div>

            <!-- Highlights live in the extracted text; the PDF is an embedded
                 viewer with no text layer we can annotate. Say so rather than
                 silently doing nothing. -->
            <div
              v-if="showOriginal && documentPdfUrl && highlightMode !== 'off' && hasProvenance"
              class="flex items-center gap-2 px-3 py-1.5 border-b border-default bg-surface-muted text-xs text-content-muted shrink-0"
            >
              <Info class="h-3.5 w-3.5 shrink-0" />
              <span class="min-w-0">{{ $t('trials.provenance.pdf_note') }}</span>
              <button class="text-primary hover:underline shrink-0" @click="showOriginal = false">
                {{ $t('trials.provenance.pdf_note_switch') }}
              </button>
            </div>

            <div class="flex-1 min-h-0 bg-surface-muted">
              <div
                v-if="documentPdfLoading"
                class="flex flex-col items-center justify-center h-full"
              >
                <LoadingSpinner size="medium" inline label="" />
                <span class="mt-2 text-sm text-content-muted">{{
                  $t('trials.viewer.loading_preview')
                }}</span>
              </div>
              <DocumentFilePreview
                v-else-if="showOriginal && documentPdfUrl"
                view-mode="pdf"
                :original-pdf-url="documentPdfUrl"
              />
              <div v-else-if="docLoading" class="flex items-center justify-center h-full">
                <LoadingSpinner size="medium" inline label="" />
              </div>
              <HighlightedText
                v-else-if="documentContent"
                :text="documentContent"
                :ranges="highlightRanges"
                :active-id="activeRangeId"
                @select="onRangeSelect"
              />
              <div
                v-else
                class="flex items-center justify-center h-full p-6 text-sm text-content-subtle italic"
              >
                {{ $t('trials.viewer.no_source') }}
              </div>
            </div>
          </div>
        </template>

        <!-- Result JSON -->
        <template #pane-result>
          <div class="flex flex-col h-full min-h-0">
            <div
              class="flex items-center justify-between gap-2 px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <h4 class="flex items-center gap-2 text-sm font-semibold text-content-muted">
                <Braces class="h-4 w-4" /> {{ $t('trials.viewer.result') }}
              </h4>
              <!-- Coverage: how many extracted values could be traced back to
                   the document. A low number is the signal worth surfacing. -->
              <Tooltip
                v-if="hasProvenance"
                :title="$t('trials.provenance.coverage_title')"
                :text="coverageTooltip"
              >
                <span
                  class="inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full border border-default bg-surface text-content-muted tabular-nums"
                >
                  <MapPin class="h-3 w-3" />
                  {{
                    $t('trials.provenance.coverage', {
                      found: coverage.found,
                      total: coverage.total,
                    })
                  }}
                </span>
              </Tooltip>
            </div>
            <div class="relative flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <!-- Copy JSON — floats top-right so it doesn't affect header height -->
              <BaseButton
                v-if="activeResult.result"
                variant="ghost"
                size="sm"
                class="absolute top-2 right-2 shadow-sm"
                :title="copied ? $t('trials.viewer.copied') : $t('trials.viewer.copy_json')"
                @click="copyResult"
              >
                <component :is="copied ? Check : Copy" class="h-4 w-4" />
              </BaseButton>
              <JsonViewer
                v-if="activeResult.result"
                :data="activeResult.result as Record<string, unknown>"
                :annotations="jsonAnnotations"
                :selected-path="selectedPath"
                @select="onValueSelect"
              />
              <div v-else class="text-sm text-content-muted italic">
                {{ $t('trials.viewer.no_output') }}
              </div>
            </div>
          </div>
        </template>

        <!-- Reasoning -->
        <template #pane-reasoning>
          <div class="flex flex-col h-full min-h-0">
            <h4
              class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <MessageSquare class="h-4 w-4" /> {{ $t('trials.viewer.reasoning') }}
            </h4>
            <div class="flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <div
                v-if="reasoningContent"
                class="markdown-content"
                v-html="renderMarkdown(reasoningContent)"
              ></div>
              <div v-else class="text-sm text-content-muted italic">
                {{ $t('trials.viewer.no_reasoning') }}
              </div>
            </div>
          </div>
        </template>

        <!-- Metadata -->
        <template #pane-metadata>
          <div class="flex flex-col h-full min-h-0">
            <h4
              class="flex items-center gap-2 text-sm font-semibold text-content-muted px-3 py-2 border-b border-default bg-surface-muted/60 shrink-0"
            >
              <Info class="h-4 w-4" /> {{ $t('trials.viewer.metadata') }}
            </h4>
            <div class="flex-1 min-h-0 overflow-y-auto bg-surface p-5">
              <dl class="space-y-3 text-sm">
                <div v-if="additionalContent?.usage">
                  <dt class="font-semibold text-content mb-1">
                    {{ $t('trials.viewer.token_usage') }}
                  </dt>
                  <ul class="text-xs text-content-muted ml-2 space-y-0.5">
                    <li v-for="(v, k) in additionalContent.usage" :key="k">
                      <span class="font-medium">{{ formatKey(k as string) }}:</span> {{ v }}
                    </li>
                  </ul>
                </div>
                <div v-if="additionalContent?.finish_reason">
                  <dt class="font-semibold text-content">
                    {{ $t('trials.viewer.finish_reason') }}
                  </dt>
                  <dd class="text-xs text-content-muted">
                    {{ additionalContent.finish_reason }}
                  </dd>
                </div>
                <div v-if="additionalContent?.json_error">
                  <dt class="font-semibold text-content">{{ $t('trials.viewer.json_error') }}</dt>
                  <dd class="text-xs text-red-600 dark:text-red-400">
                    {{ additionalContent.json_error }}
                  </dd>
                </div>
                <div
                  v-if="
                    !additionalContent?.usage &&
                    !additionalContent?.finish_reason &&
                    !additionalContent?.json_error
                  "
                  class="text-sm text-content-muted italic"
                >
                  {{ $t('trials.viewer.no_metadata') }}
                </div>
              </dl>
            </div>
          </div>
        </template>
      </PanelLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Braces,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  FileText,
  Info,
  MapPin,
  MessageSquare,
  X,
} from '@lucide/vue'
import JsonViewer, { type JsonAnnotation } from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import HighlightedText, { type HighlightRange } from '@/components/common/HighlightedText.vue'
import PanelLayout, { type PanelOption } from '@/components/common/PanelLayout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Tooltip from '@/components/common/Tooltip.vue'
import DocumentFilePreview from '@/components/documents/DocumentFilePreview.vue'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from '@/composables/useToast'
import { renderMarkdown } from '@/utils/markdown'
import { getPillClass } from '@/utils/statusStyles'
import { formatDateSmart } from '@/utils/formatters'
import {
  bestMatch,
  flattenResultLeaves,
  locateValue,
  type ProvenanceKind,
  type ProvenanceMatch,
  type ResultLeaf,
} from '@/utils/provenance'
import { PROVENANCE_NOTE_ONLY, PROVENANCE_STYLES } from '@/utils/provenanceStyles'
import type { TrialResultItem } from '@/types'

interface AdditionalContent {
  reasoning_content?: string
  usage?: Record<string, unknown>
  finish_reason?: string
  json_error?: string
  /** Evidence mode: {json path → verbatim quote the model cited}. */
  evidence?: Record<string, string>
  /** Evidence mode: {json path → the model's short note where it had no quote}. */
  evidence_notes?: Record<string, string>
  evidence_mode?: boolean
  user_guidance?: { user_message?: string }
  tuning_advice?: {
    recommendations: Array<{
      action: string
      suggested_value?: string
      rationale?: string
    }>
  }
  [key: string]: unknown
}

type HighlightMode = 'off' | 'selected' | 'all'

interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}

const props = defineProps<{
  result: TrialResultItem
  projectId: string | number
}>()

const toast = useToast()
const { t } = useI18n({ useScope: 'global' })

const documentContent = ref('')
// Whether documentContent is real extracted text (vs. the "no text" placeholder).
// Provenance must never be matched against a placeholder string.
const documentHasText = ref(false)
const docLoading = ref(false)
const documentPreviewable = ref(false)
const documentFileId = ref<number | null>(null)
const documentPdfUrl = ref('')
const documentPdfLoading = ref(false)
const copied = ref(false)
// Show the original file when available, else fall back to extracted text.
const showOriginal = ref(true)
// Active panels in the PanelLayout (order = left-to-right). 'source' is added
// by default when there's original content; 'result' is always present.
const activePanels = ref<string[]>(['result'])

const activeResult = computed(() => props.result)

// Whether the source pane has anything to show (previewable original file OR
// extracted text). Drives whether the Source chip appears at all.
const hasOriginalContent = computed(
  () => documentPreviewable.value || !!documentContent.value || docLoading.value,
)
const hasPreviewableFile = computed(() => documentPreviewable.value && !!documentPdfUrl.value)

// The chip menu. Source is only offered when there's original content;
// Reasoning / Metadata only when they exist. Result is always available.
const availablePanels = computed<PanelOption[]>(() => {
  const panels: PanelOption[] = []
  if (hasOriginalContent.value) {
    panels.push({ key: 'source', label: t('trials.viewer.panel_source'), icon: FileText })
  }
  panels.push({ key: 'result', label: t('trials.viewer.panel_result'), icon: Braces })
  if (reasoningContent.value) {
    panels.push({
      key: 'reasoning',
      label: t('trials.viewer.panel_reasoning'),
      icon: MessageSquare,
    })
  }
  if (
    additionalContent.value?.usage ||
    additionalContent.value?.finish_reason ||
    additionalContent.value?.json_error
  ) {
    panels.push({ key: 'metadata', label: t('trials.viewer.panel_metadata'), icon: Info })
  }
  return panels
})

function toggleOriginalView(): void {
  showOriginal.value = !showOriginal.value
}

const additionalContent = computed<AdditionalContent | null>(() => {
  const ac = props.result.additional_content
  if (!ac) return null
  if (typeof ac === 'string') {
    try {
      return JSON.parse(ac) as AdditionalContent
    } catch {
      return null
    }
  }
  return ac as AdditionalContent
})

const reasoningContent = computed(() => additionalContent.value?.reasoning_content || '')

// ---------------------------------------------------------------------------
// Provenance — where each extracted value came from in the source text
// ---------------------------------------------------------------------------

const highlightMode = ref<HighlightMode>('selected')
const selectedPath = ref('')
const activeMatchIndex = ref(0)

const highlightModeOptions = computed(() => [
  { label: t('trials.provenance.mode_off'), value: 'off' },
  { label: t('trials.provenance.mode_selected'), value: 'selected' },
  { label: t('trials.provenance.mode_all'), value: 'all' },
])

/** Quotes the model itself cited, when the trial ran with evidence mode on. */
const evidenceQuotes = computed<Record<string, string>>(
  () => additionalContent.value?.evidence || {},
)

/**
 * The model's one-liner for values it could not quote. This is the only thing
 * that separates "the document says no" from "the document never says" — a
 * distinction no amount of text matching can recover.
 */
const evidenceNotes = computed<Record<string, string>>(
  () => additionalContent.value?.evidence_notes || {},
)

const resultLeaves = computed<ResultLeaf[]>(() =>
  activeResult.value.result ? flattenResultLeaves(activeResult.value.result) : [],
)

/**
 * Every leaf's matches, keyed by path. Computed once per (document, result)
 * pair and cached by Vue — the fuzzy tier is the expensive one and only runs
 * for values the cheap tiers could not place.
 */
const provenance = computed<Map<string, ProvenanceMatch[]>>(() => {
  const map = new Map<string, ProvenanceMatch[]>()
  const text = documentHasText.value ? documentContent.value : ''
  if (!text) return map
  for (const leaf of resultLeaves.value) {
    if (leaf.isEmpty) continue
    map.set(
      leaf.path,
      locateValue(text, leaf.value, {
        quote: evidenceQuotes.value[leaf.path],
        label: leaf.label,
      }),
    )
  }
  return map
})

const traceableLeaves = computed(() => resultLeaves.value.filter((l) => !l.isEmpty))

/** Provenance is only meaningful when there is text to trace values back to. */
const hasProvenance = computed(() => provenance.value.size > 0)

const coverage = computed(() => {
  let found = 0
  for (const leaf of traceableLeaves.value) {
    if ((provenance.value.get(leaf.path) || []).length) found++
  }
  return { found, total: traceableLeaves.value.length }
})

const coverageTooltip = computed(() => {
  // Where the model explained itself, show that alongside the field — this list
  // is exactly where someone asks "why is this one ungrounded?".
  const missing = traceableLeaves.value
    .filter((l) => !(provenance.value.get(l.path) || []).length)
    .map((l) => {
      const note = evidenceNotes.value[l.path]
      return note ? `${l.label} (${note})` : l.label
    })
  const lines = [t('trials.provenance.coverage_help')]
  if (additionalContent.value?.evidence_mode) {
    lines.push(t('trials.provenance.coverage_evidence_mode'))
  }
  if (missing.length) {
    lines.push(
      t('trials.provenance.coverage_missing', {
        fields: missing.slice(0, 12).join(', ') + (missing.length > 12 ? ' …' : ''),
      }),
    )
  }
  return lines.join('\n')
})

/**
 * Per-leaf dot + hover text for the JSON tree.
 *
 * Only values with something real to say get an annotation: a citation, or the
 * model's own note. A value the text search could not place gets nothing —
 * "not found in the text" is a fact about the search, and reads as a verdict on
 * the extraction, which for a correctly-derived boolean it is not.
 */
const jsonAnnotations = computed<Record<string, JsonAnnotation>>(() => {
  const out: Record<string, JsonAnnotation> = {}
  if (!hasProvenance.value) return out
  for (const leaf of traceableLeaves.value) {
    const matches = provenance.value.get(leaf.path) || []
    const best = bestMatch(matches)
    const note = evidenceNotes.value[leaf.path]
    const noteLine = note ? `${t('trials.provenance.note_label')}: ${note}` : ''
    if (!best && !noteLine) continue
    const style = best ? PROVENANCE_STYLES[best.kind] : null
    out[leaf.path] = {
      dotClass: style ? style.dot : PROVENANCE_NOTE_ONLY,
      title: style
        ? `${t(style.labelKey)} — ${t(style.descKey)}` + (noteLine ? `\n${noteLine}` : '')
        : noteLine,
      count: matches.length,
    }
  }
  return out
})

const selectedLeaf = computed(
  () => traceableLeaves.value.find((l) => l.path === selectedPath.value) || null,
)
const selectedMatches = computed(() =>
  selectedPath.value ? provenance.value.get(selectedPath.value) || [] : [],
)
const selectedKind = computed<ProvenanceKind | null>(
  () => bestMatch(selectedMatches.value)?.kind ?? null,
)
const selectedNote = computed(() =>
  selectedPath.value ? evidenceNotes.value[selectedPath.value] || '' : '',
)
const selectedDotClass = computed(() =>
  selectedKind.value ? PROVENANCE_STYLES[selectedKind.value].dot : PROVENANCE_NOTE_ONLY,
)

const rangeId = (path: string, index: number): string => `${path}#${index}`

const highlightRanges = computed<HighlightRange[]>(() => {
  if (highlightMode.value === 'off' || !hasProvenance.value) return []
  const toRanges = (leaf: ResultLeaf): HighlightRange[] =>
    (provenance.value.get(leaf.path) || []).map((m, i) => ({
      id: rangeId(leaf.path, i),
      label: leaf.label,
      start: m.start,
      end: m.end,
      kind: m.kind,
    }))

  if (highlightMode.value === 'selected') {
    return selectedLeaf.value ? toRanges(selectedLeaf.value) : []
  }
  return traceableLeaves.value.flatMap(toRanges)
})

const activeRangeId = computed(() =>
  selectedPath.value ? rangeId(selectedPath.value, activeMatchIndex.value) : '',
)

/** Jump to the strongest match first — that is the one worth looking at. */
function bestMatchIndex(matches: ProvenanceMatch[]): number {
  const best = bestMatch(matches)
  const idx = best ? matches.indexOf(best) : 0
  return idx < 0 ? 0 : idx
}

function onValueSelect(path: string): void {
  selectedPath.value = path
  activeMatchIndex.value = bestMatchIndex(provenance.value.get(path) || [])
  if (highlightMode.value === 'off') highlightMode.value = 'selected'
  // Make sure the answer is actually visible: open the source pane, and leave
  // the PDF for the extracted text, which is both what the model saw and the
  // only view that can carry highlights.
  if (!activePanels.value.includes('source') && hasOriginalContent.value) {
    activePanels.value = ['source', ...activePanels.value]
  }
  if (showOriginal.value) showOriginal.value = false
}

/** Reverse link: clicking a highlight selects the value it supports. */
function onRangeSelect(id: string): void {
  const hash = id.lastIndexOf('#')
  if (hash === -1) return
  selectedPath.value = id.slice(0, hash)
  activeMatchIndex.value = Number(id.slice(hash + 1)) || 0
}

function stepMatch(delta: number): void {
  const total = selectedMatches.value.length
  if (total < 2) return
  activeMatchIndex.value = (activeMatchIndex.value + delta + total) % total
}

function clearSelection(): void {
  selectedPath.value = ''
  activeMatchIndex.value = 0
}

const documentLabel = computed(
  () =>
    props.result.document_name ||
    props.result.original_file_name ||
    `Document #${props.result.document_id}`,
)

const tokenUsage = computed(() => {
  const usage = additionalContent.value?.usage as TokenUsage | undefined
  return usage?.total_tokens ?? '—'
})

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

const statusPillClass = (status: string): string => {
  if (status === 'success') return getPillClass('green')
  if (status === 'incomplete') return getPillClass('yellow')
  if (status === 'refused') return getPillClass('orange')
  return getPillClass('red')
}

const analyzeOriginalFile = (fileType: string | undefined | null): boolean => {
  if (!fileType) return false
  return fileType === 'application/pdf' || fileType.startsWith('image/')
}

const formatKey = (key: string): string => key.replace(/_/g, ' ')

async function copyResult(): Promise<void> {
  if (!props.result.result) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(props.result.result, null, 2))
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    toast.error(t('trials.viewer.toast.copy_failed'))
  }
}

// Monotonic load counter: rapid prev/next through results fires the loaders
// again before earlier responses land; a stale response must not overwrite
// the newer document's state (or create an object URL nothing revokes).
let loadSeq = 0

async function loadDocumentTextAndMeta(seq: number): Promise<void> {
  const docId = props.result.document_id
  if (!docId) return
  docLoading.value = true
  try {
    const r = await documentsApi.get(props.projectId, docId)
    if (seq !== loadSeq) return // superseded by a newer result selection
    const d = r.data
    documentHasText.value = !!d.text
    documentContent.value = d.text || t('trials.viewer.no_text_content')
    const previewable = analyzeOriginalFile(d.original_file?.file_type)
    documentPreviewable.value = previewable
    documentFileId.value = previewable
      ? d.preprocessed_file_id && d.preprocessed_file?.file_type === 'application/pdf'
        ? d.preprocessed_file_id
        : d.original_file_id
      : null
    // Default to Source + Result side-by-side when there's original content.
    if (hasOriginalContent.value && !activePanels.value.includes('source')) {
      activePanels.value = ['source', ...activePanels.value]
    }
  } catch (err) {
    if (seq !== loadSeq) return
    documentContent.value = t('trials.viewer.load_content_error')
    console.error(err)
  } finally {
    if (seq === loadSeq) docLoading.value = false
  }
}

async function loadOriginalFilePreview(seq: number): Promise<void> {
  if (documentPdfUrl.value || documentPdfLoading.value) return
  if (!documentPreviewable.value || !documentFileId.value) return
  documentPdfLoading.value = true
  try {
    const fr = await filesApi.getContent(props.projectId, documentFileId.value, {
      preview: true,
    })
    // Bail BEFORE creating the object URL — creating it and then dropping the
    // reference would leak one full-file blob per superseded load.
    if (seq !== loadSeq) return
    const blob = new Blob([fr.data], {
      type: (fr.headers['content-type'] as string) || undefined,
    })
    documentPdfUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    if (seq !== loadSeq) return
    console.error(err)
    toast.error(t('trials.viewer.toast.load_document_failed'))
  } finally {
    if (seq === loadSeq) documentPdfLoading.value = false
  }
}

function resetDocState(): void {
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
  documentPdfUrl.value = ''
  documentPdfLoading.value = false
  documentContent.value = ''
  documentHasText.value = false
  clearSelection()
  documentPreviewable.value = false
  documentFileId.value = null
  showOriginal.value = true
  // Reset to just Result; loadDocumentTextAndMeta() will prepend Source once it
  // confirms there's original content to show.
  activePanels.value = ['result']
}

// When the active result changes, reset state and prefetch the new doc's text
// + file preview so pane switches feel instant. The preview load must run
// AFTER the text/meta load resolves — it depends on documentPreviewable /
// documentFileId set there.
watch(
  () => props.result.id,
  async () => {
    const seq = ++loadSeq
    resetDocState()
    await loadDocumentTextAndMeta(seq)
    if (seq !== loadSeq) return
    await loadOriginalFilePreview(seq)
  },
  { immediate: true },
)

onUnmounted(() => {
  // Invalidate any in-flight load so it can't create an object URL after
  // this final revoke (which would leak it).
  loadSeq++
  if (documentPdfUrl.value) URL.revokeObjectURL(documentPdfUrl.value)
})
</script>
