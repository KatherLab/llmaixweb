<template>
  <div class="w-80 border-l bg-surface dark:border-default overflow-auto">
    <div class="p-4 space-y-4">
      <!-- Version Badge -->
      <div
        v-if="selectedVersion"
        class="flex items-center justify-between p-3 bg-surface rounded-card border dark:border-default"
      >
        <span class="text-sm font-medium text-content-muted">{{
          $t('documents.info.version_status')
        }}</span>
        <span
          :class="[
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
            selectedVersion.is_latest
              ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
              : 'bg-surface-sunken text-content-muted',
          ]"
        >
          {{
            selectedVersion.is_latest
              ? $t('documents.info.current_version')
              : $t('documents.info.archived_version')
          }}
        </span>
      </div>

      <!-- Document Info -->
      <div>
        <h4 class="font-medium text-content mb-2">{{ $t('documents.info.document_info') }}</h4>
        <dl class="space-y-2 text-sm">
          <div>
            <dt class="text-content-muted">{{ $t('documents.info.created') }}</dt>
            <dd class="text-content">
              {{ formatDateFull(selectedVersion?.created_at || document.created_at) }}
            </dd>
          </div>
          <div>
            <dt class="text-content-muted">{{ $t('documents.info.file_size') }}</dt>
            <dd class="text-content">
              {{ formatFileSize(document.original_file?.file_size, $t('documents.info.unknown')) }}
            </dd>
          </div>
          <div>
            <dt class="text-content-muted">{{ $t('documents.info.text_length') }}</dt>
            <dd class="text-content">
              {{
                $t(
                  'documents.info.characters',
                  { count: fullText?.length || 0 },
                  fullText?.length || 0,
                )
              }}
            </dd>
          </div>
          <div v-if="selectedVersion && !selectedVersion.is_latest">
            <dt class="text-content-muted">{{ $t('documents.info.archived') }}</dt>
            <dd class="text-content">
              {{ formatDateFull(selectedVersion.updated_at) }}
            </dd>
          </div>
        </dl>
      </div>
      <!-- Preprocessing Info -->
      <div>
        <h4 class="font-medium text-content mb-2">
          {{ $t('documents.info.preprocessing_config') }}
        </h4>
        <dl class="space-y-2 text-sm">
          <div>
            <dt class="text-content-muted">{{ $t('documents.info.configuration') }}</dt>
            <dd class="text-content">
              {{
                (selectedVersion?.preprocessing_config || document.preprocessing_config)?.name ||
                $t('documents.info.custom')
              }}
            </dd>
          </div>
          <div>
            <dt class="text-content-muted">{{ $t('documents.info.ocr_engine') }}</dt>
            <dd class="text-content">
              {{
                getEngineLabelWithKey(
                  (selectedVersion?.preprocessing_config || document.preprocessing_config)
                    ?.additional_settings?.ocr_engine as string | null | undefined,
                )
              }}
            </dd>
          </div>
          <div v-if="getModelName(selectedVersion || document)">
            <dt class="text-content-muted">{{ $t('documents.info.model') }}</dt>
            <dd class="text-content">
              {{ getModelName(selectedVersion || document) }}
            </dd>
          </div>
        </dl>
      </div>
      <!-- Metadata -->
      <div
        v-if="
          (selectedVersion?.meta_data || document.meta_data) &&
          Object.keys(selectedVersion?.meta_data || document.meta_data || {}).length > 0
        "
      >
        <h4 class="font-medium text-content mb-2">{{ $t('documents.info.metadata') }}</h4>
        <div class="bg-surface rounded-card p-3 text-xs">
          <JsonViewer :data="selectedVersion?.meta_data || document.meta_data" />
        </div>
      </div>
      <!-- Actions -->
      <div class="pt-4 border-t space-y-2">
        <!-- Restore button for archived versions -->
        <BaseButton
          v-if="selectedVersion && !selectedVersion.is_latest"
          variant="success"
          class="w-full"
          @click="$emit('restore-version', selectedVersion)"
        >
          <RefreshCw class="h-4 w-4" />
          {{ $t('documents.info.restore_this_version') }}
        </BaseButton>
        <BaseButton variant="primary" class="w-full" @click="$emit('reprocess', document)">
          <RefreshCw class="h-4 w-4" />
          {{ $t('documents.info.reprocess_document') }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RefreshCw } from '@lucide/vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { getEngineLabelWithKey } from '@/utils/ocrLabels'
import { formatDateFull, formatFileSize } from '@/utils/formatters'
import type { DocumentListItem, DocumentMetaData } from '@/types'

interface Props {
  document: DocumentListItem
  selectedVersion?: DocumentListItem | null
  fullText?: string | null
}

withDefaults(defineProps<Props>(), {
  selectedVersion: null,
  fullText: null,
})

defineEmits<{
  'restore-version': [version: DocumentListItem]
  reprocess: [document: DocumentListItem]
}>()

interface DocWithMetaData {
  meta_data?: DocumentMetaData | null
}

const getModelName = (doc: DocWithMetaData | null | undefined): string => {
  if (!doc) return ''
  const metaData = doc.meta_data || {}
  // Check for specific model fields first
  if (metaData.mistral_model) return String(metaData.mistral_model)
  if (metaData.vision_model) return String(metaData.vision_model)
  // Fallback to generic model field
  if (metaData.model) return String(metaData.model)
  // No model for local OCR
  return ''
}
</script>
