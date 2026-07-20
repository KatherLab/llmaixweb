<template>
  <div class="mt-4 flex-1 flex flex-col">
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

      <div v-else class="max-h-[400px] overflow-y-auto">
        <div
          v-for="doc in docsPage ?? []"
          :key="doc.id"
          :class="[
            'p-3 border-b last:border-b-0 cursor-pointer hover:bg-surface-muted flex items-center',
            { 'bg-primary-soft': (selectedIds ?? []).includes(doc.id) },
          ]"
          @click="emit('toggle', doc.id)"
        >
          <input
            :checked="(selectedIds ?? []).includes(doc.id)"
            class="mr-3"
            type="checkbox"
            @click.stop
            @change="emit('toggle', doc.id)"
          />

          <div class="flex-1">
            <div class="font-medium">
              {{
                doc.document_name ||
                doc.original_file?.file_name ||
                $t('trials.individual.doc_fallback', { id: doc.id })
              }}
            </div>

            <div
              v-if="
                doc.document_name &&
                doc.original_file?.file_name &&
                doc.document_name !== doc.original_file.file_name
              "
              class="text-xs text-content-subtle italic"
            >
              {{ $t('trials.individual.original', { name: doc.original_file.file_name }) }}
            </div>

            <div class="text-xs text-content-muted">
              {{
                $t('trials.individual.config_created', {
                  config: doc.preprocessing_config?.name || $t('trials.individual.na'),
                  date: formatDate(doc.created_at),
                })
              }}
            </div>
          </div>
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
</script>
