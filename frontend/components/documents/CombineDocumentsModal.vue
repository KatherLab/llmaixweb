<template>
  <BaseModal :open="open" size="lg" @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-semibold text-content">
        {{ $t('documents.combine.title') }}
      </h3>
    </template>

    <p class="mb-4 text-sm text-content-muted">
      {{ $t('documents.combine.purpose_hint') }}
    </p>

    <!-- Grouping mode -->
    <div class="mb-4">
      <label :class="labelClass">{{ $t('documents.combine.mode_label') }}</label>
      <BaseSegmentedControl
        :model-value="mode"
        :options="modeOptions"
        class="mt-1"
        @update:model-value="mode = String($event) as Mode"
      />
    </div>

    <!-- Mode: by case ID -->
    <p v-if="mode === 'case_id'" class="mb-4 text-sm text-content-muted">
      {{ $t('documents.combine.case_id_hint') }}
    </p>

    <!-- Mode: by name pattern -->
    <div v-else-if="mode === 'pattern'" class="mb-4">
      <label :class="labelClass" for="combine-pattern">
        {{ $t('documents.combine.pattern_label') }}
      </label>
      <input
        id="combine-pattern"
        v-model="pattern"
        type="text"
        :class="inputClass"
        spellcheck="false"
        :placeholder="$t('documents.combine.pattern_placeholder')"
      />
      <p class="mt-1 text-xs text-content-muted">
        {{ $t('documents.combine.pattern_hint') }}
      </p>
      <p v-if="patternError" class="mt-1 text-xs text-red-600 dark:text-red-400">
        {{ $t('documents.combine.pattern_invalid') }}
      </p>
    </div>

    <!-- Mode: manual (from table selection) -->
    <div v-else class="mb-4">
      <label :class="labelClass" for="combine-group-name">
        {{ $t('documents.combine.group_name_label') }} <span class="text-red-500">*</span>
      </label>
      <input
        id="combine-group-name"
        v-model="manualName"
        type="text"
        :class="inputClass"
        maxlength="500"
        :placeholder="$t('documents.combine.group_name_placeholder')"
      />
      <p v-if="!manualDocs.length" class="mt-2 text-sm text-content-muted">
        {{ $t('documents.combine.manual_empty_hint') }}
      </p>
    </div>

    <!-- Only-multi toggle (auto modes) -->
    <div v-if="mode !== 'manual'" class="mb-4 flex items-center">
      <input id="combine-only-multi" v-model="onlyMulti" type="checkbox" :class="checkboxClass" />
      <label for="combine-only-multi" class="ml-2 text-sm text-content-muted">
        {{ $t('documents.combine.only_multi_label') }}
      </label>
    </div>

    <!-- Preview -->
    <div class="mb-4">
      <div class="flex justify-between items-center mb-2">
        <label :class="labelClass">{{ $t('documents.combine.preview_label') }}</label>
        <span class="text-sm text-content-muted">
          {{ $t('documents.combine.preview_count', { count: groups.length }, groups.length) }}
        </span>
      </div>
      <div class="border border-default rounded-card overflow-hidden max-h-64 overflow-y-auto">
        <div v-if="documentsLoading" class="p-4 text-center text-content-muted">
          {{ $t('documents.combine.loading_documents') }}
        </div>
        <div v-else-if="groups.length === 0" class="p-4 text-center text-content-muted">
          {{ $t('documents.combine.no_groups') }}
        </div>
        <div v-else>
          <div
            v-for="group in groups"
            :key="group.name"
            class="p-3 border-b border-default last:border-b-0"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-sm text-content truncate">{{ group.name }}</span>
              <StatusBadge color="blue">
                {{
                  $t(
                    'documents.combine.group_doc_count',
                    { count: group.documents.length },
                    group.documents.length,
                  )
                }}
              </StatusBadge>
            </div>
            <p class="text-xs text-content-muted truncate mt-1">
              {{ group.documents.map(docLabel).join(' · ') }}
            </p>
          </div>
        </div>
      </div>
      <p v-if="skippedCount > 0" class="mt-1 text-xs text-content-muted">
        {{ $t('documents.combine.skipped_note', { count: skippedCount }, skippedCount) }}
      </p>
    </div>

    <!-- Document set option -->
    <div class="mb-2">
      <div class="flex items-center">
        <input id="combine-create-set" v-model="createSet" type="checkbox" :class="checkboxClass" />
        <label for="combine-create-set" class="ml-2 text-sm text-content-muted">
          {{ $t('documents.combine.create_set_label') }}
        </label>
      </div>
      <input
        v-if="createSet"
        v-model="setName"
        type="text"
        :class="[inputClass, 'mt-2']"
        maxlength="100"
        :placeholder="$t('documents.combine.set_name_placeholder')"
      />
    </div>

    <template #footer>
      <BaseButton variant="secondary" :disabled="isSubmitting" @click="$emit('close')">
        {{ $t('documents.actions.cancel') }}
      </BaseButton>
      <BaseButton
        variant="primary"
        :disabled="!canSubmit"
        :loading="isSubmitting"
        @click="handleCombine"
      >
        {{ $t('documents.combine.submit', { count: groups.length }, groups.length) }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { documentsApi } from '@/services/documentsApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSegmentedControl from '@/components/common/BaseSegmentedControl.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { inputClass, labelClass, checkboxClass } from '@/utils/formStyles'
import type { DocumentCombineResponse, DocumentListItem } from '@/types'

interface Props {
  open: boolean
  projectId: string | number
  /** All (latest) documents of the project — supplied by the host's bulk fetch. */
  documents: DocumentListItem[]
  documentsLoading?: boolean
  /** Pre-selected documents (manual mode from the table's batch bar). */
  selectedDocumentIds?: number[] | null
}

const props = withDefaults(defineProps<Props>(), {
  documentsLoading: false,
  selectedDocumentIds: null,
})

const emit = defineEmits<{
  close: []
  combined: [response: DocumentCombineResponse]
}>()

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

type Mode = 'case_id' | 'pattern' | 'manual'
const mode = ref<Mode>(props.selectedDocumentIds?.length ? 'manual' : 'case_id')
const modeOptions = computed(() => [
  { label: t('documents.combine.mode_case_id'), value: 'case_id' },
  { label: t('documents.combine.mode_pattern'), value: 'pattern' },
  { label: t('documents.combine.mode_manual'), value: 'manual' },
])

const pattern = ref<string>('')
const manualName = ref<string>('')
const onlyMulti = ref<boolean>(true)
const createSet = ref<boolean>(true)
const setName = ref<string>('')
const isSubmitting = ref<boolean>(false)

// Combined documents can't be sources again; oldest-first within a group so the
// merged text reads chronologically.
const candidateDocs = computed<DocumentListItem[]>(() =>
  props.documents
    .filter((d) => !d.meta_data?.combined)
    .slice()
    .sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime() || a.id - b.id,
    ),
)

const docLabel = (doc: DocumentListItem): string =>
  doc.document_name ||
  doc.original_file?.file_name ||
  t('documents.common.document_number', { id: doc.id })

const patternRegex = computed<RegExp | null>(() => {
  if (!pattern.value.trim()) return null
  try {
    return new RegExp(pattern.value)
  } catch {
    return null
  }
})
const patternError = computed<boolean>(() => !!pattern.value.trim() && !patternRegex.value)

const manualDocs = computed<DocumentListItem[]>(() => {
  const wanted = new Set(props.selectedDocumentIds || [])
  return candidateDocs.value.filter((d) => wanted.has(d.id))
})

interface PreviewGroup {
  name: string
  documents: DocumentListItem[]
}

// The grouping preview. Auto modes derive a key per document (case ID from
// row-by-row import metadata, or the pattern's first capture group applied to
// the document name); manual mode is one group from the table selection.
const grouped = computed<{ groups: PreviewGroup[]; skipped: number }>(() => {
  if (mode.value === 'manual') {
    const name = manualName.value.trim()
    if (!name || manualDocs.value.length === 0) return { groups: [], skipped: 0 }
    return { groups: [{ name, documents: manualDocs.value }], skipped: 0 }
  }

  const byKey = new Map<string, DocumentListItem[]>()
  let skipped = 0
  for (const doc of candidateDocs.value) {
    let key: string | null = null
    if (mode.value === 'case_id') {
      const caseId = doc.meta_data?.case_id
      key = caseId === undefined || caseId === null || caseId === '' ? null : String(caseId)
    } else {
      const re = patternRegex.value
      if (re) {
        const match = docLabel(doc).match(re)
        key = match ? (match[1] ?? match[0]) || null : null
      }
    }
    if (!key) {
      skipped++
      continue
    }
    const list = byKey.get(key) ?? []
    list.push(doc)
    byKey.set(key, list)
  }

  let groups = [...byKey.entries()].map(([name, documents]) => ({ name, documents }))
  if (onlyMulti.value) {
    const singles = groups.filter((g) => g.documents.length < 2)
    skipped += singles.reduce((n, g) => n + g.documents.length, 0)
    groups = groups.filter((g) => g.documents.length >= 2)
  }
  groups.sort((a, b) => a.name.localeCompare(b.name))
  return { groups, skipped }
})

const groups = computed(() => grouped.value.groups)
const skippedCount = computed(() => grouped.value.skipped)

const canSubmit = computed<boolean>(
  () => groups.value.length > 0 && !isSubmitting.value && !patternError.value,
)

const handleCombine = async (): Promise<void> => {
  if (!canSubmit.value) return
  isSubmitting.value = true
  try {
    const { data } = await documentsApi.combine(props.projectId, {
      groups: groups.value.map((g) => ({
        name: g.name,
        document_ids: g.documents.map((d) => d.id),
      })),
      create_document_set: createSet.value,
      document_set_name: createSet.value
        ? setName.value.trim() || t('documents.combine.default_set_name')
        : null,
    })
    emit('combined', data)
  } catch (error) {
    toast.error(extractErrorMessage(error, t('documents.combine.failed')))
    console.error(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>
