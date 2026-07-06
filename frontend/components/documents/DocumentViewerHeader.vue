<template>
  <div
    class="flex items-center justify-between p-4 border-b bg-slate-50 dark:bg-slate-800 rounded-t-lg"
  >
    <div class="flex items-center space-x-4">
      <h3 class="text-lg font-semibold text-slate-900 dark:text-white">
        {{
          document.document_name || document.original_file?.file_name || `Document #${document.id}`
        }}
      </h3>

      <p
        v-if="
          document.document_name &&
          document.original_file?.file_name &&
          document.document_name !== document.original_file.file_name
        "
        class="text-sm text-slate-500 dark:text-slate-400 mt-1"
      >
        Original File: {{ document.original_file.file_name }}
      </p>

      <!-- Extraction Method Badge -->
      <ExtractionMethodBadge :document="document" />
    </div>
    <div class="flex items-center space-x-2">
      <!-- Version History Button -->
      <BaseButton
        v-if="hasVersionHistory"
        variant="secondary"
        size="sm"
        :title="showVersionHistory ? 'Hide version history' : 'Show version history'"
        @click="$emit('toggle-version-history')"
      >
        <Clock class="h-4 w-4" />
        <StatusBadge v-if="(versionCount ?? 0) > 0" color="blue">{{ versionCount }}</StatusBadge>
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
        v-else-if="!hasDisplayableOriginalFile && hasText"
        class="inline-flex items-center px-3 py-1.5 border border-slate-200 dark:border-slate-700 text-sm font-medium rounded-card text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800"
        title="Only text view is available"
      >
        <FileText class="h-4 w-4 mr-1.5" />
        Text Only
      </span>
      <BaseButton variant="secondary" size="sm" @click="$emit('download')">
        <CloudDownload class="h-4 w-4" />
        Download
      </BaseButton>
      <button
        class="text-slate-400 hover:text-slate-500 dark:hover:text-slate-300"
        @click="$emit('close')"
      >
        <X class="h-6 w-6" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock, CloudDownload, FileText, X } from '@lucide/vue'
import ExtractionMethodBadge from './ExtractionMethodBadge.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { DocumentListItem } from '@/types'

type ViewMode = 'text' | 'pdf' | 'image' | 'compare'

// The segmented control emits "file" to let the parent resolve pdf vs image.
type EmitViewMode = ViewMode | 'file'

interface Props {
  document: DocumentListItem
  hasVersionHistory?: boolean
  showVersionHistory?: boolean
  versionCount?: number
  hasDisplayableOriginalFile?: boolean
  hasText?: boolean
  viewMode?: ViewMode
}

const props = withDefaults(defineProps<Props>(), {
  hasVersionHistory: false,
  showVersionHistory: false,
  versionCount: 0,
  hasDisplayableOriginalFile: false,
  hasText: false,
  viewMode: 'text',
})

const emit = defineEmits<{
  close: []
  'toggle-version-history': []
  'change-view': [mode: EmitViewMode]
  download: []
}>()

// Segmented control works in three logical modes: Text, File, Both (compare).
// The internal viewMode distinguishes pdf vs image, but both map to "file".
const viewOptions = [
  { label: 'Text', value: 'text' },
  { label: 'File', value: 'file' },
  { label: 'Both', value: 'both' },
]

const segmentedValue = computed(() => {
  if (props.viewMode === 'compare') return 'both'
  if (props.viewMode === 'text') return 'text'
  return 'file' // pdf or image
})

const onSegmentedChange = (value: string | number | boolean): void => {
  const v = String(value)
  if (v === 'text') {
    emit('change-view', 'text')
  } else if (v === 'both') {
    emit('change-view', 'compare')
  } else if (v === 'file') {
    // Delegate to parent which knows whether to use pdf or image
    emit('change-view', 'file')
  }
}
</script>
