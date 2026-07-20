<template>
  <BaseModal :open="open" size="lg" :close-on-backdrop="false" @close="emit('cancel')">
    <!-- Header -->
    <template #header>
      <div class="flex items-center gap-3">
        <!-- Dynamic icon based on situation -->
        <Info
          v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates"
          class="w-6 h-6 text-primary"
        />
        <AlertTriangle v-else class="w-6 h-6 text-amber-600 dark:text-amber-400" />
        <h3 class="text-lg font-semibold text-content">
          <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
            {{ $t('files.duplicate.title_embedded') }}
          </template>
          <template v-else-if="hasSameConfigDuplicates">
            {{ $t('files.duplicate.title_archived') }}
          </template>
          <template v-else> {{ $t('files.duplicate.title_found') }} </template>
        </h3>
      </div>
    </template>

    <!-- Body -->
    <div class="space-y-4">
      <!-- Different messages based on situation -->
      <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
        <p class="text-sm text-content-muted">
          {{ $t('files.duplicate.embedded_desc') }}
        </p>
        <Callout :icon="CircleCheckBig" variant="info">
          <p class="text-xs">
            <strong>{{ $t('files.duplicate.tip_label') }}</strong>
            {{ $t('files.duplicate.tip_before') }}
            <code class="bg-primary-soft px-1 rounded">Force OCR for PDFs</code>
            {{ $t('files.duplicate.tip_after') }}
          </p>
        </Callout>
      </template>

      <template v-else-if="hasSameConfigDuplicates">
        <p class="text-sm text-content-muted">
          {{ $t('files.duplicate.same_config_before') }}
          <strong>{{ $t('files.duplicate.same_config_emphasis') }}</strong
          >{{ $t('files.duplicate.same_config_after') }}
        </p>

        <!-- Option to skip existing -->
        <label
          class="flex items-start gap-3 p-3 bg-primary-soft border border-default rounded-card cursor-pointer hover:bg-primary-soft transition-colors"
        >
          <input v-model="skipExisting" type="checkbox" :class="[checkboxClass, 'mt-0.5']" />
          <div class="flex-1">
            <p class="text-sm font-medium text-primary">
              {{ $t('files.duplicate.skip_existing_label') }}
            </p>
            <p class="text-xs text-primary mt-1">
              {{ $t('files.duplicate.skip_existing_desc') }}
            </p>
          </div>
        </label>
      </template>

      <template v-else>
        <p class="text-sm text-content-muted">
          {{ $t('files.duplicate.diff_config_desc') }}
        </p>
      </template>

      <!-- Files with duplicates list -->
      <div class="max-h-80 overflow-y-auto border border-default rounded-card">
        <!-- Show same-config duplicates first (if any) -->
        <template v-if="hasSameConfigDuplicates">
          <div
            v-for="item in duplicatePreview?.same_config_duplicates"
            :key="item.file_id"
            class="px-4 py-3 border-b border-default hover:bg-amber-50 dark:hover:bg-amber-900/20"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-content truncate">
                  {{ item.file_name }}
                </p>
                <p
                  class="text-xs text-amber-700 dark:text-amber-300 mt-1 inline-flex items-center gap-1"
                >
                  <AlertTriangle class="w-3 h-3 inline" />
                  {{
                    $t(
                      'files.duplicate.existing_same_config',
                      { count: item.existing_document_count },
                      item.existing_document_count,
                    )
                  }}
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300 text-amber-700 flex-shrink-0 ml-3"
              >
                {{ $t('files.duplicate.badge_same_config') }}
              </span>
            </div>
          </div>
        </template>

        <!-- Show PDFs with embedded text -->
        <template v-if="hasPdfsWithEmbeddedText">
          <div
            v-for="pdf in duplicatePreview?.pdfs_with_embedded_text"
            :key="pdf.file_id"
            class="px-4 py-3 border-b border-default hover:bg-primary-soft"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-content truncate">
                  {{ pdf.file_name }}
                </p>
                <p class="text-xs text-primary mt-1 inline-flex items-center gap-1">
                  <Info class="w-3 h-3 inline" />
                  {{ $t('files.duplicate.has_embedded_text') }}
                  <span v-if="pdf.existing_document_ocr_method" class="text-content-muted">
                    •
                    {{
                      $t('files.duplicate.previously_extracted', {
                        method: pdf.existing_document_ocr_method,
                      })
                    }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-primary-soft text-primary flex-shrink-0 ml-3"
              >
                {{ $t('files.duplicate.badge_embedded_text') }}
              </span>
            </div>
          </div>
        </template>

        <!-- Show different-config duplicates (if any, and no same-config) -->
        <template v-if="!hasSameConfigDuplicates && !hasPdfsWithEmbeddedText">
          <div
            v-for="item in duplicatePreview?.files_with_duplicates"
            :key="item.file_id"
            class="px-4 py-3 border-b border-default last:border-b-0 hover:bg-surface-muted"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-content truncate">
                  {{ item.file_name }}
                </p>
                <p class="text-xs text-content-muted mt-1">
                  {{
                    $t(
                      'files.duplicate.existing_diff_config',
                      { count: item.existing_document_count },
                      item.existing_document_count,
                    )
                  }}
                  <span v-if="item.config_name" class="text-content-subtle">
                    • {{ $t('files.duplicate.config_name', { name: item.config_name }) }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-surface-sunken text-content-muted flex-shrink-0 ml-3"
              >
                {{ $t('files.duplicate.badge_diff_config') }}
              </span>
            </div>
          </div>
        </template>
      </div>

      <!-- Summary -->
      <div class="bg-surface-muted rounded-card p-3 flex items-center justify-between text-sm">
        <span class="text-content-muted">
          <span class="font-semibold text-content">{{
            duplicatePreview?.files_with_duplicates?.length || 0
          }}</span>
          {{
            $t(
              'files.duplicate.summary_existing',
              duplicatePreview?.files_with_duplicates?.length || 0,
            )
          }}
        </span>
        <span class="text-content-muted">
          <span class="font-semibold text-content">{{
            duplicatePreview?.files_without_duplicates
          }}</span>
          {{ $t('files.duplicate.summary_new', duplicatePreview?.files_without_duplicates || 0) }}
        </span>
      </div>

      <!-- Info note about document versioning (only for same-config duplicates) -->
      <Callout v-if="hasSameConfigDuplicates" variant="info">
        <p class="text-xs">
          <strong>{{ $t('files.duplicate.versioning_label') }}</strong>
          {{ $t('files.duplicate.versioning_before') }}
          <code class="bg-primary-soft px-1 rounded">is_latest=false</code>
          {{ $t('files.duplicate.versioning_after') }}
        </p>
      </Callout>
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('cancel')">
        {{ $t('files.actions.cancel') }}
      </BaseButton>
      <BaseButton
        class="flex items-center gap-2"
        :disabled="submitting"
        @click="emit('confirm', { skipExisting: skipExisting })"
      >
        <Check class="w-4 h-4" />
        <template v-if="skipExisting">{{ $t('files.duplicate.process_new_only') }}</template>
        <template v-else-if="hasSameConfigDuplicates">{{
          $t('files.duplicate.archive_continue')
        }}</template>
        <template v-else>{{ $t('files.duplicate.continue') }}</template>
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { AlertTriangle, Check, CircleCheckBig, Info } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { checkboxClass } from '@/utils/formStyles'
import type { PreprocessingDuplicatePreview } from '@/types'

interface Props {
  open: boolean
  duplicatePreview?: PreprocessingDuplicatePreview | null
  /** Disables the action buttons while the confirmed action is in flight. */
  submitting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  duplicatePreview: null,
  submitting: false,
})

const emit = defineEmits<{
  confirm: [payload: { skipExisting: boolean }]
  cancel: []
}>()

// Owned UI state — reset to unchecked each time the modal opens.
const skipExisting = ref(false)
watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) skipExisting.value = false
  },
)

const hasSameConfigDuplicates = computed(() => {
  return (
    !!props.duplicatePreview?.same_config_duplicates &&
    props.duplicatePreview.same_config_duplicates.length > 0
  )
})

const hasPdfsWithEmbeddedText = computed(() => {
  return (
    !!props.duplicatePreview?.pdfs_with_embedded_text &&
    props.duplicatePreview.pdfs_with_embedded_text.length > 0
  )
})
</script>
