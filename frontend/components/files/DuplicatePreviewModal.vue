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
            PDF Embedded Text Detected
          </template>
          <template v-else-if="hasSameConfigDuplicates">
            Existing Documents Will Be Archived
          </template>
          <template v-else> Existing Documents Found </template>
        </h3>
      </div>
    </template>

    <!-- Body -->
    <div class="space-y-4">
      <!-- Different messages based on situation -->
      <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
        <p class="text-sm text-content-muted">
          The following PDF file(s) have embedded text. Since "Force OCR" is not enabled, the
          embedded text will be extracted directly regardless of the selected OCR engine. The result
          will be identical to previous extractions.
        </p>
        <Callout :icon="CircleCheckBig" variant="info">
          <p class="text-xs">
            <strong>Tip:</strong> Enable
            <code class="bg-primary-soft px-1 rounded">Force OCR for PDFs</code>
            in Advanced Options to force OCR on all pages, ignoring embedded text.
          </p>
        </Callout>
      </template>

      <template v-else-if="hasSameConfigDuplicates">
        <p class="text-sm text-content-muted">
          The following files have existing documents with the
          <strong>same OCR configuration</strong>. Running preprocessing will create new versions
          and archive the old ones. Archived documents are hidden by default but can be viewed in
          the document history.
        </p>

        <!-- Option to skip existing -->
        <label
          class="flex items-start gap-3 p-3 bg-primary-soft border border-default rounded-card cursor-pointer hover:bg-primary-soft transition-colors"
        >
          <input v-model="skipExisting" type="checkbox" :class="[checkboxClass, 'mt-0.5']" />
          <div class="flex-1">
            <p class="text-sm font-medium text-primary">
              Only process files without existing documents
            </p>
            <p class="text-xs text-primary mt-1">
              Skip files that already have documents for this OCR configuration. Useful if you want
              to process only new files or re-process files where OCR quality was poor.
            </p>
          </div>
        </label>
      </template>

      <template v-else>
        <p class="text-sm text-content-muted">
          The following files have existing documents with a different OCR configuration. Running
          preprocessing will create additional documents (not replace existing ones). Both versions
          will be preserved.
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
                  {{ item.existing_document_count }} existing document{{
                    item.existing_document_count !== 1 ? 's' : ''
                  }}
                  with same config will be archived
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300 text-amber-700 flex-shrink-0 ml-3"
              >
                Same config
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
                  Has embedded text
                  <span v-if="pdf.existing_document_ocr_method" class="text-content-muted">
                    • Previously extracted with: {{ pdf.existing_document_ocr_method }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-primary-soft text-primary flex-shrink-0 ml-3"
              >
                Embedded text
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
                  {{ item.existing_document_count }} existing document{{
                    item.existing_document_count !== 1 ? 's' : ''
                  }}
                  with different config
                  <span v-if="item.config_name" class="text-content-subtle">
                    • Config: {{ item.config_name }}
                  </span>
                </p>
              </div>
              <span
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-surface-sunken text-content-muted flex-shrink-0 ml-3"
              >
                Different config
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
          file{{ (duplicatePreview?.files_with_duplicates?.length || 0) !== 1 ? 's' : '' }}
          with existing documents
        </span>
        <span class="text-content-muted">
          <span class="font-semibold text-content">{{
            duplicatePreview?.files_without_duplicates
          }}</span>
          new file{{ duplicatePreview?.files_without_duplicates !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Info note about document versioning (only for same-config duplicates) -->
      <Callout v-if="hasSameConfigDuplicates" variant="info">
        <p class="text-xs">
          <strong>Document versioning:</strong> Previous versions are preserved with
          <code class="bg-primary-soft px-1 rounded">is_latest=false</code> and can be restored if
          needed. Only the latest version is shown in the document list by default.
        </p>
      </Callout>
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <BaseButton variant="secondary" :disabled="submitting" @click="emit('cancel')">
        Cancel
      </BaseButton>
      <BaseButton
        class="flex items-center gap-2"
        :disabled="submitting"
        @click="emit('confirm', { skipExisting: skipExisting })"
      >
        <Check class="w-4 h-4" />
        <template v-if="skipExisting">Process New Files Only</template>
        <template v-else-if="hasSameConfigDuplicates">Archive & Continue</template>
        <template v-else>Continue</template>
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
