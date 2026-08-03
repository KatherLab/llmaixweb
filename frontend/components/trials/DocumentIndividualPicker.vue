<template>
  <div class="mt-4 flex-1 min-h-0 flex flex-col">
    <div class="flex gap-2 mb-3">
      <SearchInput v-model="searchTerm" :placeholder="$t('trials.individual.search_placeholder')" />
      <BaseButton
        variant="secondary"
        size="sm"
        :title="$t('trials.individual.select_all_title')"
        :disabled="isSelectingAll || isLoadingDocs"
        @click="emit('select-all')"
        >{{
          isSelectingAll ? $t('trials.individual.selecting') : $t('trials.individual.select_all')
        }}</BaseButton
      >
      <BaseButton
        variant="secondary"
        size="sm"
        :title="$t('trials.individual.clear_title')"
        @click="emit('clear')"
        >{{ $t('trials.individual.clear') }}</BaseButton
      >
    </div>

    <div class="border rounded-card overflow-hidden flex-1 min-h-[100px] flex flex-col">
      <div v-if="docsError" class="p-4 text-center text-red-600 dark:text-red-400 text-sm">
        {{ docsError }}
      </div>

      <div v-else-if="isLoadingDocs" class="p-6 text-center text-content-muted">
        <LoadingSpinner />
      </div>

      <div v-else-if="(docsPage ?? []).length === 0" class="p-4 text-center text-content-muted">
        {{ $t('trials.individual.no_match') }}
      </div>

      <!-- Fills the panel when the dialog gives it a fixed height (lg+), and
           falls back to a capped box when the columns stack and the modal body
           scrolls as one. -->
      <!-- One line per document. The list is the one part of this dialog that
           genuinely wants vertical space, so the source file, config and date
           move into the row's tooltip and only the name stays on screen —
           roughly three times as many documents visible in the same box. -->
      <div v-else class="max-h-[400px] overflow-y-auto lg:max-h-none lg:flex-1 lg:min-h-0">
        <div
          v-for="doc in docsPage ?? []"
          :key="doc.id"
          :class="[
            'px-3 py-2 border-b last:border-b-0 cursor-pointer hover:bg-surface-muted flex items-center gap-3',
            { 'bg-primary-soft': (selectedIds ?? []).includes(doc.id) },
          ]"
          :title="rowTitle(doc)"
          @click="emit('toggle', doc.id)"
        >
          <input
            :checked="(selectedIds ?? []).includes(doc.id)"
            class="shrink-0"
            type="checkbox"
            @click.stop
            @change="emit('toggle', doc.id)"
          />

          <span class="flex-1 min-w-0 truncate text-sm font-medium">
            {{ docName(doc) }}
          </span>

          <span class="shrink-0 max-w-[45%] truncate text-[11px] text-content-subtle">
            {{ docMeta(doc) }}
          </span>
        </div>
      </div>

      <!-- Pager -->
      <div class="px-3 py-2 flex items-center justify-between text-sm bg-surface">
        <div>
          <span class="font-medium">{{ totalDocs }}</span> {{ $t('trials.individual.total') }}
          <span class="text-content-subtle">•</span>
          {{ $t('trials.individual.page') }} <span class="font-medium">{{ page }}</span>
          /
          {{ Math.max(1, Math.ceil((totalDocs ?? 0) / (pageSize ?? 1))) }}
        </div>
        <div class="flex items-center gap-2">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="(page ?? 1) <= 1 || isLoadingDocs"
            @click="emit('prev-page')"
            >{{ $t('trials.individual.prev') }}</BaseButton
          >
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="
              (page ?? 1) >= Math.ceil((totalDocs ?? 0) / (pageSize ?? 1)) || isLoadingDocs
            "
            @click="emit('next-page')"
            >{{ $t('trials.individual.next') }}</BaseButton
          >
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { formatDate } from '@/utils/formatters'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import type { DocumentListItem } from '@/types'

withDefaults(
  defineProps<{
    selectedIds?: number[]
    docsPage?: DocumentListItem[]
    totalDocs?: number
    pageSize?: number
    page?: number
    isLoadingDocs?: boolean
    docsError?: string | null
    isSelectingAll?: boolean
  }>(),
  {
    selectedIds: () => [],
    docsPage: () => [],
    totalDocs: 0,
    pageSize: 50,
    page: 1,
    isLoadingDocs: false,
    docsError: null,
    isSelectingAll: false,
  },
)

const emit = defineEmits<{
  toggle: [docId: number]
  'select-all': []
  clear: []
  'prev-page': []
  'next-page': []
}>()

const searchTerm = defineModel<string>('searchTerm', { default: '' })

const { t } = useI18n({ useScope: 'global' })

function docName(doc: DocumentListItem): string {
  return (
    doc.document_name ||
    doc.original_file?.file_name ||
    t('trials.individual.doc_fallback', { id: doc.id })
  )
}

/** Trailing muted metadata — enough to tell two versions of a document apart. */
function docMeta(doc: DocumentListItem): string {
  return [doc.preprocessing_config?.name, formatDate(doc.created_at)].filter(Boolean).join(' · ')
}

/** Everything the row used to spell out, on hover. */
function rowTitle(doc: DocumentListItem): string {
  const lines = [docName(doc)]
  const original = doc.original_file?.file_name
  if (original && doc.document_name && original !== doc.document_name) {
    lines.push(t('trials.individual.original', { name: original }))
  }
  lines.push(
    t('trials.individual.config_created', {
      config: doc.preprocessing_config?.name || t('trials.individual.na'),
      date: formatDate(doc.created_at),
    }),
  )
  return lines.join('\n')
}
</script>
