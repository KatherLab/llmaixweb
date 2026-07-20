<template>
  <BaseModal
    :open="open"
    size="lg"
    :closeable="!isProcessing"
    :close-on-backdrop="!isProcessing"
    :close-on-esc="!isProcessing"
    @close="requestClose"
  >
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-content">
          {{ actionTitle }}
        </h3>
        <p class="mt-1 text-sm text-content-muted">
          {{ $t('documents.batch.selected', { count: documents.length, entity: entityNoun }) }}
        </p>
      </div>
    </template>

    <!-- Reprocess Action -->
    <div v-if="action === 'reprocess'" class="space-y-4">
      <div class="flex items-center">
        <input
          id="batch-force-reprocess"
          v-model="forceReprocess"
          type="checkbox"
          :class="checkboxClass"
        />
        <label for="batch-force-reprocess" class="ml-2 text-sm text-content-muted">
          {{ $t('documents.batch.force_reprocess') }}
        </label>
      </div>
      <Callout variant="info">
        <p class="text-sm">
          {{ $t('documents.batch.reprocess_note') }}
        </p>
      </Callout>
    </div>

    <!-- Export Action -->
    <div v-else-if="action === 'export'" class="space-y-4">
      <p class="text-sm text-content-muted">{{ $t('documents.batch.export_choose') }}</p>
      <div>
        <label for="batch-export-format" :class="labelClass">
          {{ $t('documents.batch.export_format_label') }}
        </label>
        <select id="batch-export-format" v-model="exportFormat" :class="selectClass">
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="txt">{{ $t('documents.batch.export_format_txt') }}</option>
          <option value="pdf">{{ $t('documents.batch.export_format_pdf') }}</option>
        </select>
      </div>
      <div class="space-y-2">
        <label class="flex items-center">
          <input v-model="includeMetadata" type="checkbox" :class="checkboxClass" />
          <span class="ml-2 text-sm text-content-muted">{{
            $t('documents.batch.include_metadata')
          }}</span>
        </label>
        <label class="flex items-center">
          <input v-model="includePreprocessingInfo" type="checkbox" :class="checkboxClass" />
          <span class="ml-2 text-sm text-content-muted">{{
            $t('documents.batch.include_preprocessing')
          }}</span>
        </label>
      </div>
    </div>

    <!-- Delete Action -->
    <div v-else-if="action === 'delete'" class="space-y-4">
      <Callout variant="danger" :title="$t('documents.batch.warning_title')">
        <p class="mt-1">{{ deleteWarningText }}</p>
      </Callout>

      <!-- Cascade option (documents & files) -->
      <div v-if="supportsCascade" class="rounded-md border border-default p-3">
        <label class="flex items-start">
          <input
            v-model="cascadeDelete"
            type="checkbox"
            :class="[checkboxClass, 'mt-0.5 text-red-600 focus:ring-red-500']"
          />
          <span class="ml-2 text-sm text-content-muted">{{ cascadeLabel }}</span>
        </label>
        <p v-if="loadingDeps" class="mt-2 text-xs text-content-subtle">
          {{ $t('documents.batch.checking_usage') }}
        </p>
        <p v-else-if="depsPreviewUnavailable" class="mt-2 text-xs text-content-muted">
          {{
            $t('documents.batch.deps_preview_unavailable', {
              limit: DEPS_PREVIEW_LIMIT.toLocaleString(),
              entity: entityPlural,
            })
          }}
        </p>
        <p v-else-if="cascadeDelete && dependencyImpact" class="mt-2 text-xs text-red-600">
          {{ $t('documents.batch.will_also_delete', { impact: dependencyImpact }) }}
        </p>
        <p
          v-else-if="cascadeDelete && dependencies && !dependencyImpact"
          class="mt-2 text-xs text-content-subtle"
        >
          {{ $t('documents.batch.not_used_elsewhere', { entity: entityPlural }) }}
        </p>
        <p v-else-if="!cascadeDelete && dependencyImpact" class="mt-2 text-xs text-content-subtle">
          {{ $t('documents.batch.in_use_by', { impact: dependencyImpact }) }}
        </p>
      </div>

      <div class="flex items-center">
        <input
          id="batch-confirm-delete"
          v-model="confirmDelete"
          type="checkbox"
          :class="[checkboxClass, 'text-red-600 focus:ring-red-500']"
        />
        <label for="batch-confirm-delete" class="ml-2 text-sm text-content-muted">
          {{ $t('documents.batch.confirm_permanent') }}
        </label>
      </div>
    </div>

    <template #footer>
      <p
        v-if="isProcessing && progress"
        class="mr-auto self-center text-sm text-content-muted"
        role="status"
      >
        {{
          $t('documents.batch.progress', {
            verb: progressVerb,
            done: progress.done.toLocaleString(),
            total: progress.total.toLocaleString(),
          })
        }}
      </p>
      <BaseButton variant="secondary" :disabled="isProcessing" @click="requestClose">
        {{ $t('documents.actions.cancel') }}
      </BaseButton>
      <BaseButton
        :variant="action === 'delete' ? 'danger' : 'primary'"
        :disabled="!canPerformAction"
        :loading="isProcessing"
        @click="performAction"
      >
        {{ isProcessing ? $t('documents.batch.processing') : actionButtonText }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { checkboxClass, selectClass, labelClass } from '@/utils/formStyles'
import { documentsApi } from '@/services/documentsApi'
import { trialsApi } from '@/services/trialsApi'
import { filesApi } from '@/services/filesApi'
import { preprocessingApi } from '@/services/preprocessingApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import type { DocumentDependencies, FileDependencies, PreprocessingTaskCreate } from '@/types'

interface Props {
  open: boolean
  action: string
  documents: number[]
  projectId: string | number
  // 'documents' (default) operates on documents via documentsApi;
  // 'trials' operates on trials via trialsApi (delete only);
  // 'files' operates on files via filesApi (delete only).
  mode?: 'documents' | 'trials' | 'files'
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'documents',
})

const emit = defineEmits<{
  close: []
  complete: []
  deleted: [ids: number[]]
}>()
const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

// Count-aware entity noun keyed by mode; used across titles, counts, and toasts.
const entityKey = computed(() =>
  props.mode === 'trials'
    ? 'documents.batch.entity_trial'
    : props.mode === 'files'
      ? 'documents.batch.entity_file'
      : 'documents.batch.entity_document',
)
// Noun agreeing with the current selection size, plus fixed singular/plural.
const entityNoun = computed(() => t(entityKey.value, props.documents.length))
const entityPlural = computed(() => t(entityKey.value, 2))
const capitalize = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)

// Form state
const forceReprocess = ref<boolean>(false)
const exportFormat = ref<string>('json')
const includeMetadata = ref<boolean>(true)
const includePreprocessingInfo = ref<boolean>(true)
const confirmDelete = ref<boolean>(false)
const isProcessing = ref<boolean>(false)
// Live progress while a batch runs ("Deleting/Resolving X of Y…").
const progress = ref<{ done: number; total: number } | null>(null)
// Verb for the footer progress counter — deletes delete, reprocess first
// resolves each document to its source file.
const progressVerb = computed(() =>
  props.action === 'reprocess'
    ? t('documents.batch.verb_resolving')
    : t('documents.batch.verb_deleting'),
)

// Cascade-delete state (documents & files modes)
const cascadeDelete = ref<boolean>(false)
const dependencies = ref<DocumentDependencies | FileDependencies | null>(null)
const loadingDeps = ref<boolean>(false)
// The dependency-preview endpoints cap the id list; past that we skip the call
// and say so instead of silently swallowing a 422.
const DEPS_PREVIEW_LIMIT = 1000
const depsPreviewUnavailable = computed(
  () => props.action === 'delete' && props.documents.length > DEPS_PREVIEW_LIMIT,
)

// The backend batch endpoint caps ids per call; larger selections are chunked.
const BATCH_DELETE_CHUNK = 200

// Only documents and files fan out to trials/groups/evaluations; trials don't.
const supportsCascade = computed(() => props.mode === 'documents' || props.mode === 'files')

// While a delete batch is running the modal must not be dismissable — the
// requests would keep running invisibly behind a refetching parent.
const requestClose = (): void => {
  if (isProcessing.value) return
  emit('close')
}

// Reset per-open state and fetch the cascade impact preview whenever the
// delete modal opens for a cascade-capable resource.
watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    // Reset per-open state — otherwise the permanent-action confirmation (and
    // force-reprocess) stays armed from the previous use of this modal.
    confirmDelete.value = false
    forceReprocess.value = false
    progress.value = null
    cascadeDelete.value = false
    dependencies.value = null
    if (props.action !== 'delete' || !supportsCascade.value) return
    if (props.documents.length === 0 || depsPreviewUnavailable.value) return
    loadingDeps.value = true
    try {
      const { data } =
        props.mode === 'files'
          ? await filesApi.checkDependencies(props.projectId, props.documents)
          : await documentsApi.checkDependencies(props.projectId, props.documents)
      dependencies.value = data
    } catch (error) {
      // Non-fatal: the checkbox still works, just without a preview.
      console.error(
        extractErrorMessage(error, t('documents.batch.toast_check_usage_failed')),
        error,
      )
    } finally {
      loadingDeps.value = false
    }
  },
  { immediate: true },
)

// Human-readable impact summary, e.g. "3 documents, 2 trials, 1 group, 5 extraction results".
const dependencyImpact = computed<string>(() => {
  const d = dependencies.value
  if (!d) return ''
  const parts: string[] = []
  const impact = (n: number, key: string) => t(`documents.batch.${key}`, { count: n }, n)
  // Files delete their produced documents too; show that first.
  if ('documents' in d && d.documents) parts.push(impact(d.documents, 'impact_document'))
  if (d.trials.count) parts.push(impact(d.trials.count, 'impact_trial'))
  // Groups lose the deleted documents (and are removed only if left empty).
  if (d.document_sets.count) parts.push(impact(d.document_sets.count, 'impact_group_membership'))
  if (d.trial_results) parts.push(impact(d.trial_results, 'impact_extraction_result'))
  if (d.evaluation_metrics) parts.push(impact(d.evaluation_metrics, 'impact_evaluation_metric'))
  return parts.join(', ')
})

// Computed
const cascadeLabel = computed(() =>
  props.mode === 'files'
    ? t('documents.batch.cascade_files')
    : t('documents.batch.cascade_default'),
)

const deleteWarningText = computed(() => {
  switch (props.mode) {
    case 'trials':
      return t('documents.batch.warn_trials')
    case 'files':
      return t('documents.batch.warn_files')
    default:
      return t('documents.batch.warn_documents')
  }
})

const actionTitle = computed(() => {
  const entity = capitalize(entityPlural.value)
  switch (props.action) {
    case 'reprocess':
      return t('documents.batch.title_reprocess', { entity })
    case 'export':
      return t('documents.batch.title_export', { entity })
    case 'delete':
      return t('documents.batch.title_delete', { entity })
    default:
      return t('documents.batch.title_default')
  }
})

const actionButtonText = computed(() => {
  const entity = capitalize(entityPlural.value)
  switch (props.action) {
    case 'reprocess':
      return t('documents.batch.button_start_reprocessing')
    case 'export':
      return t('documents.batch.button_export')
    case 'delete':
      return t('documents.batch.button_delete', { entity })
    default:
      return t('documents.batch.button_confirm')
  }
})

const canPerformAction = computed(() => {
  if (isProcessing.value) return false
  switch (props.action) {
    case 'reprocess':
      return true
    case 'export':
      return true
    case 'delete':
      return confirmDelete.value
    default:
      return false
  }
})

// Methods
const performAction = async (): Promise<void> => {
  if (!canPerformAction.value) return
  isProcessing.value = true
  try {
    switch (props.action) {
      case 'reprocess':
        await reprocessDocuments()
        break
      case 'export':
        await exportDocuments()
        break
      case 'delete':
        await deleteDocuments()
        // Always close modal after delete - specific errors already shown
        emit('complete')
        return
    }
    emit('complete')
  } catch (error) {
    // Don't show generic error for delete - specific errors already shown
    if (props.action !== 'delete') {
      toast.error(t('documents.batch.toast_action_failed', { entity: entityPlural.value }))
      console.error(error)
    }
  } finally {
    isProcessing.value = false
    // Close modal after action completes (for delete, this happens after all attempts)
    if (props.action === 'delete') {
      emit('close')
    }
  }
}

const reprocessDocuments = async (): Promise<void> => {
  // `props.documents` are *document* IDs, but a preprocessing task needs the
  // underlying *file* IDs. Resolve each selected document to its
  // original_file_id (deduped — row-by-row CSVs share one file) AND reuse its
  // original preprocessing configuration, so the reprocess runs with the same
  // OCR engine/settings instead of silently falling back to defaults. Documents
  // are grouped by config so a mixed selection produces one task per config.
  type Group = { fileIds: Set<number>; settings: Record<string, unknown> }
  const byConfig = new Map<number | 'inline', Group>()
  // Resolve with a live counter and modest concurrency — a big selection would
  // otherwise sit behind a static "Processing..." label doing sequential GETs.
  progress.value = { done: 0, total: props.documents.length }
  const CONCURRENCY = 5
  let nextIndex = 0
  const worker = async (): Promise<void> => {
    while (true) {
      const i = nextIndex++
      if (i >= props.documents.length) return
      const docId = props.documents[i]!
      try {
        const { data } = await documentsApi.get(props.projectId, docId)
        if (data?.original_file_id) {
          const key = data.preprocessing_config_id ?? 'inline'
          const group = byConfig.get(key) ?? {
            fileIds: new Set<number>(),
            settings:
              (data.preprocessing_config?.additional_settings as Record<string, unknown>) ?? {},
          }
          group.fileIds.add(data.original_file_id)
          byConfig.set(key, group)
        }
      } catch (error) {
        console.error(`Failed to resolve document #${docId} to a file:`, error)
      }
      progress.value = {
        done: (progress.value?.done ?? 0) + 1,
        total: props.documents.length,
      }
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(CONCURRENCY, props.documents.length) }, () => worker()),
  )
  const totalFiles = new Set<number>()
  byConfig.forEach((g) => g.fileIds.forEach((id) => totalFiles.add(id)))
  if (totalFiles.size === 0) {
    toast.error(t('documents.batch.toast_no_files'))
    return
  }
  const stamp = new Date().toISOString().slice(0, 16).replace('T', ' ')
  for (const group of byConfig.values()) {
    const taskData: PreprocessingTaskCreate = {
      inline_config: {
        name: `Reprocess ${stamp}`,
        additional_settings: group.settings,
      },
      file_ids: Array.from(group.fileIds),
      force_reprocess: forceReprocess.value,
    }
    await preprocessingApi.create(props.projectId, taskData)
  }
  toast.success(
    t('documents.batch.toast_reprocess_started', { count: totalFiles.size }, totalFiles.size),
  )
}

const exportDocuments = async (): Promise<void> => {
  toast.info(t('documents.batch.toast_export_stub'))
}

interface FailedDoc {
  docId: number
  error: string
}

// Normalize a batch-endpoint error entry (string or `{ message, links }`) to text.
const batchErrorText = (err: unknown, fallback: string): string => {
  if (typeof err === 'string') return err
  if (err && typeof err === 'object' && 'message' in err) {
    return String((err as { message: unknown }).message)
  }
  return fallback
}

const deleteDocuments = async (): Promise<number[]> => {
  const failedDocs: FailedDoc[] = []
  const successDocs: number[] = []
  const useCascade = supportsCascade.value && cascadeDelete.value
  const entityOne = t(entityKey.value, 1)
  progress.value = { done: 0, total: props.documents.length }

  if (props.mode === 'files') {
    // Files use the batch endpoint (one request per 200 ids) — select-all can
    // hold tens of thousands of ids, and one DELETE per file doesn't scale.
    for (let i = 0; i < props.documents.length; i += BATCH_DELETE_CHUNK) {
      const chunk = props.documents.slice(i, i + BATCH_DELETE_CHUNK)
      try {
        const { data } = await filesApi.batchDelete(props.projectId, chunk, useCascade)
        successDocs.push(...data.deleted)
        for (const err of data.errors) {
          failedDocs.push({
            docId: err.file_id,
            error: batchErrorText(
              err.error,
              t('documents.batch.delete_failed_fallback', { entity: entityOne }),
            ),
          })
        }
      } catch (error) {
        // Whole-chunk failure (network, 4xx before any delete ran).
        const message = extractErrorMessage(
          error,
          t('documents.batch.delete_failed_fallback', { entity: entityPlural.value }),
        )
        failedDocs.push(...chunk.map((docId) => ({ docId, error: message })))
      }
      progress.value = {
        done: Math.min(i + chunk.length, props.documents.length),
        total: props.documents.length,
      }
    }
  } else {
    for (const docId of props.documents) {
      try {
        if (props.mode === 'trials') {
          await trialsApi.delete(props.projectId, docId)
        } else {
          await documentsApi.delete(props.projectId, docId, useCascade)
        }
        successDocs.push(docId)
      } catch (error) {
        failedDocs.push({
          docId,
          error: extractErrorMessage(
            error,
            t('documents.batch.delete_failed_fallback', { entity: entityOne }),
          ),
        })
      }
      progress.value = {
        done: progress.value ? progress.value.done + 1 : 1,
        total: props.documents.length,
      }
    }
  }

  const successCount = successDocs.length
  if (successCount > 0) {
    toast.success(
      t(
        'documents.batch.deleted_success',
        { count: successCount, entity: t(entityKey.value, successCount) },
        successCount,
      ),
    )
    // Emit successfully deleted IDs so parent can update selection
    emit('deleted', successDocs)
  }

  if (failedDocs.length > 0) {
    console.error('Failed to delete items:', failedDocs)
    // One summary toast instead of one per failed item. Surface the first
    // error verbatim, note how many more, and add the document-set hint if any
    // failure was caused by a set membership.
    const first = failedDocs[0]
    const more =
      failedDocs.length > 1
        ? ' ' + t('documents.batch.more_count', { count: failedDocs.length - 1 })
        : ''
    const hint = failedDocs.some((f) => f.error.includes('document sets'))
      ? ' ' + t('documents.batch.hint_manage')
      : ''
    // The backend error text says "document sets"; the UI-facing term is
    // "document groups" — normalize so one toast doesn't mix both.
    const firstError = first.error.replace(/document set(s?)/gi, 'document group$1')
    toast.error(
      t('documents.batch.delete_failed_summary', {
        count: failedDocs.length,
        entity: t(entityKey.value, failedDocs.length),
        id: first.docId,
        error: firstError,
      }) +
        more +
        '.' +
        hint,
    )
    // Don't throw - close modal anyway but parent will know what was deleted
  }

  return successDocs
}
</script>
