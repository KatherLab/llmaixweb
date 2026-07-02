<template>
  <div class="mt-4 flex-1 flex flex-col">
    <div class="flex gap-2 mb-3">
      <SearchInput v-model="searchTerm" placeholder="Search documents (text or filename)…" />
      <BaseButton
        variant="secondary"
        size="sm"
        title="Select all matching documents"
        :disabled="isSelectingAll || isLoadingDocs"
        @click="emit('select-all')"
        >{{ isSelectingAll ? 'Selecting…' : 'Select All' }}</BaseButton
      >
      <BaseButton variant="secondary" size="sm" title="Clear selection" @click="emit('clear')"
        >Clear</BaseButton
      >
    </div>

    <div class="border rounded-md overflow-hidden flex-1 min-h-[100px] flex flex-col">
      <div v-if="docsError" class="p-4 text-center text-red-600 dark:text-red-400 text-sm">
        {{ docsError }}
      </div>

      <div v-else-if="isLoadingDocs" class="p-6 text-center text-slate-500 dark:text-slate-400">
        <LoadingSpinner />
      </div>

      <div
        v-else-if="(docsPage ?? []).length === 0"
        class="p-4 text-center text-slate-500 dark:text-slate-400"
      >
        No documents match your criteria
      </div>

      <div v-else class="max-h-[400px] overflow-y-auto">
        <div
          v-for="doc in docsPage ?? []"
          :key="doc.id"
          :class="[
            'p-3 border-b last:border-b-0 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center',
            { 'bg-blue-50 dark:bg-blue-900/20': (selectedIds ?? []).includes(doc.id) },
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
              {{ doc.document_name || doc.original_file?.file_name || `Document #${doc.id}` }}
            </div>

            <div
              v-if="
                doc.document_name &&
                doc.original_file?.file_name &&
                doc.document_name !== doc.original_file.file_name
              "
              class="text-xs text-slate-400 dark:text-slate-500 italic"
            >
              (Original: {{ doc.original_file.file_name }})
            </div>

            <div class="text-xs text-slate-500 dark:text-slate-400">
              Config: {{ doc.preprocessing_config?.name || 'N/A' }} • Created:
              {{ formatDate(doc.created_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Pager -->
      <div class="px-3 py-2 flex items-center justify-between text-sm bg-white dark:bg-slate-800">
        <div>
          <span class="font-medium">{{ totalDocs }}</span> total
          <span class="text-slate-400 dark:text-slate-500">•</span>
          page <span class="font-medium">{{ page }}</span>
          /
          {{ Math.max(1, Math.ceil((totalDocs ?? 0) / (pageSize ?? 1))) }}
        </div>
        <div class="flex items-center gap-2">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="(page ?? 1) <= 1 || isLoadingDocs"
            @click="emit('prev-page')"
            >Prev</BaseButton
          >
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="
              (page ?? 1) >= Math.ceil((totalDocs ?? 0) / (pageSize ?? 1)) || isLoadingDocs
            "
            @click="emit('next-page')"
            >Next</BaseButton
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
