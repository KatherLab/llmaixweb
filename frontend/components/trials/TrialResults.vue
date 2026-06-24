<template>
  <teleport to="body">
    <transition name="fade">
      <div
        v-if="isModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
        @click="$emit('close')"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div
          class="relative bg-white rounded-3xl shadow-2xl max-w-8xl w-full max-h-[95vh] flex flex-col ring-1 ring-blue-100 overflow-hidden"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between gap-4 px-8 py-6 border-b rounded-t-3xl bg-white/90"
          >
            <h3 class="text-2xl font-bold tracking-tight text-gray-800">Trial Results</h3>
            <button
              class="text-gray-400 hover:text-blue-700 hover:bg-blue-50 rounded-full p-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close"
              autofocus
              @click="$emit('close')"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-8 bg-white/70">
            <!-- Loading -->
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-16">
              <span class="mb-3">
                <LoadingSpinner size="medium" inline label="" />
              </span>
              <span class="mt-2 text-gray-500">Loading trial results…</span>
            </div>
            <!-- Error -->
            <div
              v-else-if="error"
              class="bg-red-50 border-l-4 border-red-400 p-5 mb-5 rounded-lg flex items-start gap-2"
            >
              <svg class="h-6 w-6 mt-1 text-red-400" fill="none" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 00-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 101.4 1.4L10 11.4l1.3 1.3a1 1 0 001.4-1.4L11.4 10l1.3-1.3a1 1 0 00-1.4-1.4L10 8.6 8.7 7.3z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="text-sm text-red-700">{{ error }}</span>
            </div>

            <!-- Content -->
            <template v-else-if="trial">
              <TrialMetaHeader
                :trial="trial"
                :total-usage="totalUsage"
                @open-schema="openSchemaModal"
                @open-prompt="openPromptModal"
              />

              <TrialDocumentErrors :failures="trial?.meta?.failures" />

              <!-- Results list -->
              <div
                v-if="!trial.results || trial.results.length === 0"
                class="flex flex-col items-center justify-center py-16 bg-gray-50 rounded-lg border border-gray-200"
              >
                <svg
                  class="h-14 w-14 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span class="text-gray-500 mt-3">No results available for this trial.</span>
                <span
                  v-if="trial.status === 'processing' || trial.status === 'pending'"
                  class="text-sm mt-2 text-gray-400"
                  >Please wait for the trial to complete.</span
                >
              </div>

              <div v-else class="grid grid-cols-1 gap-5">
                <TrialResultCard
                  v-for="(res, index) in trial.results"
                  :key="index"
                  :res="res"
                  :index="index"
                  :label="documentLabels[index]"
                  :expanded="!!expandedResults[index]"
                  :document-content="documentContents[index] || ''"
                  :view-mode="viewMode[index] || 'horizontal'"
                  :document-pdf-url="documentPdfUrls[index] || ''"
                  :document-pdf-loading="!!documentPdfLoading[index]"
                  :show-document-panel="!!showDocumentPanel[index]"
                  :document-meta="documentMeta[index]"
                  :show-reasoning-panel="!!showReasoningPanel[index]"
                  :reasoning-content="getReasoningContent(index) || ''"
                  :additional-content="getAdditionalContent(index)"
                  @toggle-expansion="toggleResultExpansion(index)"
                  @toggle-view-mode="toggleViewMode(index)"
                  @toggle-document-panel="toggleDocumentPanel(index)"
                  @toggle-reasoning="toggleReasoning(index)"
                />
              </div>
            </template>

            <div v-else class="flex flex-col items-center justify-center py-16">
              <svg
                class="h-14 w-14 text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="1.5"
                  d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span class="text-gray-500 mt-3">Trial not found</span>
              <button
                class="mt-6 inline-block px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors duration-150 shadow"
                @click="$emit('close')"
              >
                Return to trials
              </button>
            </div>
          </div>
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
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { trialsApi } from '@/services/trialsApi'
import { schemasApi } from '@/services/schemasApi'
import { documentsApi } from '@/services/documentsApi'
import { filesApi } from '@/services/filesApi'
import { useToast } from 'vue-toastification'
import TrialMetaHeader from './TrialMetaHeader.vue'
import TrialDocumentErrors from './TrialDocumentErrors.vue'
import TrialResultCard from './TrialResultCard.vue'
import TrialSchemaModal from './TrialSchemaModal.vue'
import TrialPromptModal from './TrialPromptModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  trialId: { type: [String, Number], required: true },
  isModal: { type: Boolean, default: false },
})
defineEmits(['close'])

const route = useRoute()
const toast = useToast()

const trialId = computed(() => props.trialId || parseInt(route.params.trialId))
const isLoading = ref(true)
const error = ref(null)
const trial = ref(null)

const expandedResults = ref({})
const documentContents = ref({})
const documentLabels = ref({})
const viewMode = ref({})
const documentPdfUrls = ref({})
const documentPdfLoading = ref({})
const showDocumentPanel = ref({})
// per-result: { previewable, fileId } — drives whether the "View Original
// Document" button is shown at all (hidden when there's nothing to render)
const documentMeta = ref({})
const showReasoningPanel = ref({}) // reasoning accordion

// Schema / Prompt snapshot display (frozen at trial run; fallback to live for
// trials created before snapshots existed)
const showSchemaModal = ref(false)
const showPromptModal = ref(false)
const schemaFallback = ref(null) // live schema fetched for legacy trials
const schemaForModal = computed(() => trial.value?.schema_snapshot || schemaFallback.value || null)
const promptForModal = computed(() => trial.value?.prompt_snapshot || trial.value?.prompt || null)
const schemaIsSnapshot = computed(() => !!trial.value?.schema_snapshot)
const promptIsSnapshot = computed(() => !!trial.value?.prompt_snapshot)

async function openSchemaModal() {
  // Legacy trials have no snapshot — fetch the live schema as a best-effort fallback.
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

// Helpers to parse/inspect additional_content
const parseAdditional = (ac) => {
  if (!ac) return null
  if (typeof ac === 'string') {
    try {
      return JSON.parse(ac)
    } catch {
      return null
    }
  }
  return ac
}
const getAdditionalContent = (i) => {
  const r = trial.value?.results?.[i]
  return r ? parseAdditional(r.additional_content) : null
}
const getReasoningContent = (i) => getAdditionalContent(i)?.reasoning_content || null

const docIdForIndex = (i) => {
  const r = trial.value?.results?.[i]
  // Prefer the document_id embedded in the result; fall back to legacy array if present
  return r?.document_id ?? trial.value?.document_ids?.[i] ?? null
}

const totalUsage = computed(() => {
  const totals = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
  if (!trial.value?.results?.length) return totals
  for (const r of trial.value.results) {
    const ac = parseAdditional(r?.additional_content)
    if (!ac?.usage) continue
    totals.prompt_tokens += Number(ac.usage.prompt_tokens ?? 0) || 0
    totals.completion_tokens += Number(ac.usage.completion_tokens ?? 0) || 0
    totals.total_tokens += Number(ac.usage.total_tokens ?? 0) || 0
  }
  return totals
})

// Fetch the full trial (with results)
const fetchData = async () => {
  isLoading.value = true
  error.value = null
  try {
    const res = await trialsApi.get(props.projectId, trialId.value)
    trial.value = res.data
    if (trial.value?.results?.length) loadDocumentNames()
  } catch (err) {
    console.error('Error loading trial:', err)
    error.value = extractErrorMessage(err, 'Failed to load trial data')
  } finally {
    isLoading.value = false
  }
}

// Load per-document display labels + original-file previewability
const loadDocumentNames = async () => {
  if (!trial.value?.results?.length) return
  for (let i = 0; i < trial.value.results.length; i++) {
    try {
      const docId = docIdForIndex(i)
      if (!docId) {
        documentMeta.value[i] = { previewable: false, fileId: null }
        continue
      }
      const r = await documentsApi.get(props.projectId, docId)
      const d = r.data
      documentLabels.value[i] = {
        name: d.document_name || d.original_file?.file_name || `Document ${docId}`,
        original: d.original_file?.file_name || '',
      }
      // Only PDFs/images can be shown inline; the "View Original Document"
      // button is hidden for everything else (txt, csv, xlsx, …) so no split
      // screen is offered when there's nothing to render.
      const { previewable } = analyzeOriginalFile(d)
      const fileId =
        d.preprocessed_file_id && d.preprocessed_file?.file_type === 'application/pdf'
          ? d.preprocessed_file_id
          : d.original_file_id
      documentMeta.value[i] = { previewable, fileId: previewable ? fileId : null }
    } catch (err) {
      console.error(`Label load failed index ${i}:`, err)
      const fallbackId = docIdForIndex(i)
      documentLabels.value[i] = { name: `Document (ID: ${fallbackId ?? 'unknown'})`, original: '' }
      documentMeta.value[i] = { previewable: false, fileId: null }
    }
  }
}

// Toggles
const toggleResultExpansion = async (i) => {
  expandedResults.value[i] = !expandedResults.value[i]
  if (viewMode.value[i] === undefined) viewMode.value[i] = 'horizontal'
  if (expandedResults.value[i] && !documentContents.value[i]) {
    try {
      const docId = docIdForIndex(i)
      if (!docId) throw new Error('Missing document_id for this result')
      const r = await documentsApi.get(props.projectId, docId)
      documentContents.value[i] = r.data.text || 'No text content available'
    } catch (err) {
      documentContents.value[i] = 'Error loading document content'
      console.error(err)
    }
  }
}

const toggleViewMode = (i) => {
  viewMode.value[i] = viewMode.value[i] === 'vertical' ? 'horizontal' : 'vertical'
}
// Decide whether the original file can be rendered as an inline preview.
// Mirrors DocumentViewer.vue's detection (hasDisplayableOriginalFile +
// originalFileType): only PDFs and images are previewable. TXT files and
// row-by-row CSV/XLSX have no separate original (the extracted text IS the
// content); other types (CSV/XLSX full-document, DOCX, …) can't be shown
// inline. The caller hides the "View Original Document" button for these.
const analyzeOriginalFile = (d) => {
  const fileType = d?.original_file?.file_type
  if (!fileType) return { previewable: false }
  if (fileType === 'application/pdf' || fileType.startsWith('image/')) return { previewable: true }
  return { previewable: false }
}

const toggleDocumentPanel = async (i) => {
  showDocumentPanel.value[i] = !showDocumentPanel.value[i]
  if (!showDocumentPanel.value[i]) return
  // Already resolved — just show the existing preview
  if (documentPdfUrls.value[i] || documentPdfLoading.value[i]) return
  const meta = documentMeta.value[i]
  // No inline-previewable original (txt/csv/xlsx/…) → button is hidden, so this
  // should not be reachable; bail out defensively.
  if (!meta?.previewable || !meta?.fileId) return
  documentPdfLoading.value[i] = true
  try {
    const fr = await filesApi.getContent(props.projectId, meta.fileId, { preview: true })
    const blob = new Blob([fr.data], { type: fr.headers['content-type'] })
    documentPdfUrls.value[i] = URL.createObjectURL(blob)
  } catch (err) {
    console.error(err)
    toast.error('Failed to load document')
  } finally {
    documentPdfLoading.value[i] = false
  }
}

// Reasoning accordion toggle (pure UI state, no side effects)
const toggleReasoning = (i) => {
  showReasoningPanel.value[i] = !showReasoningPanel.value[i]
}

watch(
  () => props.isModal,
  (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
  },
)
onMounted(() => {
  fetchData()
  if (props.isModal) document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  try {
    Object.values(documentPdfUrls.value || {}).forEach((url) => {
      if (url) URL.revokeObjectURL(url)
    })
  } catch {
    // ignore cleanup errors
  }
  document.body.style.overflow = ''
})
</script>
