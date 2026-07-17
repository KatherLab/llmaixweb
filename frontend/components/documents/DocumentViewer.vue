<template>
  <SlideOver
    :open="open"
    aria-label="Document viewer"
    body-class="!p-0 overflow-hidden"
    @close="$emit('close')"
  >
    <template #header>
      <div class="flex items-center justify-between gap-4 flex-1 min-w-0 pr-8">
        <div class="flex items-center gap-3 min-w-0">
          <div class="min-w-0">
            <h3 class="text-base font-semibold text-content truncate">
              {{
                document.document_name ||
                document.original_file?.file_name ||
                `Document #${document.id}`
              }}
            </h3>
            <p
              v-if="
                document.document_name &&
                document.original_file?.file_name &&
                document.document_name !== document.original_file.file_name
              "
              class="text-xs text-content-subtle truncate"
            >
              {{ document.original_file.file_name }}
            </p>
          </div>
          <ExtractionMethodBadge :document="document" class="shrink-0" />
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <BaseButton
            v-if="hasVersionHistory"
            variant="secondary"
            size="sm"
            :title="showVersionHistory ? 'Hide version history' : 'Show version history'"
            @click="showVersionHistory = !showVersionHistory"
          >
            <Clock class="h-4 w-4" />
            <StatusBadge v-if="(versionCount ?? 0) > 0" color="blue">{{
              versionCount
            }}</StatusBadge>
            History
          </BaseButton>
          <BaseSegmentedControl
            v-if="hasDisplayableOriginalFile"
            :model-value="segmentedValue"
            :options="viewOptions"
            size="sm"
            @update:model-value="onSegmentedChange"
          />
          <span
            v-else
            class="inline-flex items-center px-3 py-1.5 border border-default text-sm font-medium rounded-card text-content-muted bg-surface-muted"
            title="Only text view is available"
          >
            <FileText class="h-4 w-4 mr-1.5" />
            Text Only
          </span>
          <BaseButton variant="secondary" size="sm" @click="bodyRef?.downloadDocument()">
            <CloudDownload class="h-4 w-4" />
            Download
          </BaseButton>
          <!-- Document nav -->
          <template v-if="showNav">
            <BaseButton
              variant="secondary"
              size="sm"
              :disabled="!hasPrev"
              :title="hasPrev ? 'Previous document (←)' : 'First document'"
              @click="$emit('prev')"
            >
              <ChevronLeft class="h-4 w-4" />
            </BaseButton>
            <span
              class="text-xs font-medium text-content-muted tabular-nums px-1 whitespace-nowrap"
            >
              {{ props.index + 1 }} / {{ props.total }}
            </span>
            <BaseButton
              variant="secondary"
              size="sm"
              :disabled="!hasNext"
              :title="hasNext ? 'Next document (→)' : 'Last document'"
              @click="$emit('next')"
            >
              <ChevronRight class="h-4 w-4" />
            </BaseButton>
          </template>
        </div>
      </div>
    </template>

    <DocumentViewerBody
      ref="bodyRef"
      v-model:show-version-history="showVersionHistory"
      :document="document"
      :project-id="projectId"
      :open="open"
      @reprocess="(payload) => emit('reprocess', payload)"
      @restored="(id) => emit('restored', id)"
      @update-document="(version) => emit('update-document', version)"
      @update:version-count="(count) => (versionCount = count)"
    />
  </SlideOver>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ChevronLeft, ChevronRight, Clock, CloudDownload, FileText } from '@lucide/vue'
import SlideOver from '@/components/common/SlideOver.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DocumentViewerBody from './DocumentViewerBody.vue'
import ExtractionMethodBadge from './ExtractionMethodBadge.vue'
import type { DocumentListItem } from '@/types'

interface Props {
  open: boolean
  document: DocumentListItem
  projectId: string | number
  // Document navigation through the host list. Omit for single-doc contexts.
  index?: number
  total?: number
  hasPrev?: boolean
  hasNext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  index: 0,
  total: undefined,
  hasPrev: false,
  hasNext: false,
})

const emit = defineEmits<{
  close: []
  reprocess: [payload: Partial<DocumentListItem>]
  restored: [documentId: number]
  'update-document': [version: DocumentListItem]
  prev: []
  next: []
}>()

const bodyRef = ref<InstanceType<typeof DocumentViewerBody> | null>(null)

// Version-history sidebar visibility — owned by the header toggle, passed down.
const showVersionHistory = ref<boolean>(false)

const showNav = computed(() => props.total !== undefined)

// Header needs to know whether to show the History button + the view segmented
// control. These mirror the body's computeds; we re-derive them here from the
// passed document so the header renders correctly before/after the body loads.
const hasDisplayableOriginalFile = computed<boolean>(() => {
  if (!props.document.original_file?.id) return false
  if (!props.document.original_file?.file_type) return false
  const fileType = props.document.original_file.file_type
  if (fileType === 'text/plain') return false
  if (props.document.meta_data?.preprocessing_strategy === 'row_by_row') return false
  return true
})

const hasVersionHistory = computed<boolean>(() => {
  return (
    !!props.document.version_of ||
    !!props.document.meta_data?.version_of ||
    !!props.document.meta_data?.replaced_document_id
  )
})

// Real archived-version count, pushed up from the body once its versions
// fetch resolves. Defaults to 1 (the current version) until then.
const versionCount = ref<number>(1)

type SegmentedView = 'text' | 'file' | 'both'
const segmentedValue = ref<SegmentedView>('both')

const viewOptions = [
  { label: 'Text', value: 'text' },
  { label: 'File', value: 'file' },
  { label: 'Both', value: 'both' },
]

function onSegmentedChange(value: string | number | boolean): void {
  segmentedValue.value = String(value) as SegmentedView
  bodyRef.value?.onSegmentedChange(value)
}

// Keyboard navigation: ← / → to move between documents (ignored when focus is
// in an editable field so users can type elsewhere).
function onKeydown(e: KeyboardEvent): void {
  if (!props.open || !showNav.value) return
  const target = e.target as HTMLElement | null
  const tag = target?.tagName
  const editable =
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable
  if (editable) return
  if (e.key === 'ArrowLeft') {
    e.preventDefault()
    emit('prev')
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    emit('next')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      showVersionHistory.value = false
    }
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>
