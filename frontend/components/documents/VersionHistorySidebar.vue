<template>
  <div
    class="absolute right-80 top-0 bottom-0 w-64 bg-surface border-l dark:border-default shadow-lg z-10 overflow-auto"
  >
    <div class="p-4">
      <div class="flex items-center justify-between mb-4">
        <h4 class="font-semibold text-content">Version History</h4>
        <button class="text-content-subtle hover:text-content" @click="$emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loadingVersions" class="text-center py-8">
        <LoadingSpinner size="small" />
        <p class="text-xs text-content-muted mt-2">Loading versions...</p>
      </div>

      <!-- Versions List -->
      <div v-else-if="(versions ?? []).length > 0" class="space-y-2">
        <div
          v-for="version in versions ?? []"
          :key="version.id"
          :class="[
            'p-3 rounded-card border cursor-pointer transition-all',
            selectedVersion?.id === version.id
              ? 'border-primary bg-primary-soft'
              : 'border-default hover:border-strong hover:bg-surface-muted',
          ]"
          @click="$emit('select-version', version)"
        >
          <div class="flex items-center justify-between mb-1">
            <span
              :class="[
                'text-xs font-medium px-1.5 py-0.5 rounded',
                version.is_latest
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-surface-sunken text-content-muted',
              ]"
            >
              {{ version.is_latest ? 'Current' : 'Archived' }}
            </span>
            <span class="text-xs text-content-muted"
              >v{{ (versionCount ?? 0) - (versions ?? []).indexOf(version) }}</span
            >
          </div>
          <p class="text-xs text-content-muted">
            {{ formatRelativeTime(version.created_at) }}
          </p>
          <p
            v-if="version.meta_data?.extraction_method"
            class="text-xs text-content-subtle truncate mt-1"
          >
            {{ getShortExtractionMethod(version.meta_data.extraction_method) }}
          </p>
        </div>
      </div>

      <!-- No Versions -->
      <div v-else class="text-center py-8">
        <FileText class="w-10 h-10 text-content-subtle mx-auto" />
        <p class="text-sm text-content-muted mt-2">Only one version exists</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileText, X } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { formatRelativeTime as sharedFormatRelativeTime } from '@/utils/formatters'
import type { DocumentListItem } from '@/types'

interface Props {
  loadingVersions?: boolean
  versions?: DocumentListItem[]
  selectedVersion?: DocumentListItem | null
  versionCount?: number
}

withDefaults(defineProps<Props>(), {
  loadingVersions: false,
  versions: () => [],
  selectedVersion: null,
  versionCount: 0,
})

defineEmits<{
  close: []
  'select-version': [version: DocumentListItem]
}>()

// Format relative time (e.g., "2 hours ago"). Delegates the just-now/m/h/d
// tiers to the shared formatter; versions older than a week fall back to a
// locale date (preserves the original 7-day cutoff vs the shared 30-day one).
const formatRelativeTime = (dateString: string | null | undefined): string => {
  if (!dateString) return ''
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  if (Date.now() - date.getTime() >= 604800000) return date.toLocaleDateString()
  return sharedFormatRelativeTime(dateString)
}

// Get short extraction method label
const getShortExtractionMethod = (method: string | null | undefined): string => {
  if (!method) return ''
  if (method.includes('no_ocr')) return 'Text Extraction'
  if (method.includes('tesseract')) return 'Local OCR'
  if (method.includes('mistral')) return 'Mistral OCR'
  if (method.includes('llm_vision')) return 'Vision LLM'
  if (method.includes('force_ocr')) return 'Force OCR'
  return method.replace(/_/g, ' ').replace('docling serve', 'Docling')
}
</script>
