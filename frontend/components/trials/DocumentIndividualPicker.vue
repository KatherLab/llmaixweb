<template>
  <div class="mt-4 flex-1 flex flex-col">
    <div class="flex gap-2 mb-3">
      <input
        v-model="searchTerm"
        class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        placeholder="Search documents (text or filename)…"
        type="text"
      />
      <button
        class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
        title="Select all matching documents"
        :disabled="isSelectingAll || isLoadingDocs"
        @click="emit('select-all')"
      >
        {{ isSelectingAll ? 'Selecting…' : 'Select All' }}
      </button>
      <button
        class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
        title="Clear selection"
        @click="emit('clear')"
      >
        Clear
      </button>
    </div>

    <div class="border rounded-md overflow-hidden flex-1 min-h-[100px] flex flex-col">
      <div v-if="docsError" class="p-4 text-center text-red-600 text-sm">
        {{ docsError }}
      </div>

      <div v-else-if="isLoadingDocs" class="p-6 text-center text-gray-500">
        <LoadingSpinner />
      </div>

      <div v-else-if="docsPage.length === 0" class="p-4 text-center text-gray-500">
        No documents match your criteria
      </div>

      <div v-else class="max-h-[400px] overflow-y-auto">
        <div
          v-for="doc in docsPage"
          :key="doc.id"
          :class="[
            'p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 flex items-center',
            { 'bg-blue-50': selectedIds.includes(doc.id) },
          ]"
          @click="emit('toggle', doc.id)"
        >
          <input
            :checked="selectedIds.includes(doc.id)"
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
              class="text-xs text-gray-400 italic"
            >
              (Original: {{ doc.original_file.file_name }})
            </div>

            <div class="text-xs text-gray-500">
              Config: {{ doc.preprocessing_config?.name || 'N/A' }} • Created:
              {{ formatDate(doc.created_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Pager -->
      <div class="px-3 py-2 flex items-center justify-between text-sm bg-white">
        <div>
          <span class="font-medium">{{ totalDocs }}</span> total
          <span class="text-gray-400">•</span>
          page <span class="font-medium">{{ page }}</span>
          /
          {{ Math.max(1, Math.ceil(totalDocs / pageSize)) }}
        </div>
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1 rounded-md bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
            :disabled="page <= 1 || isLoadingDocs"
            @click="emit('prev-page')"
          >
            Prev
          </button>
          <button
            class="px-3 py-1 rounded-md bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
            :disabled="page >= Math.ceil(totalDocs / pageSize) || isLoadingDocs"
            @click="emit('next-page')"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from '@/utils/formatters.js'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

defineProps({
  selectedIds: {
    type: Array,
    default: () => [],
  },
  docsPage: {
    type: Array,
    default: () => [],
  },
  totalDocs: {
    type: Number,
    default: 0,
  },
  pageSize: {
    type: Number,
    default: 50,
  },
  page: {
    type: Number,
    default: 1,
  },
  isLoadingDocs: {
    type: Boolean,
    default: false,
  },
  docsError: {
    type: String,
    default: null,
  },
  isSelectingAll: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle', 'select-all', 'clear', 'prev-page', 'next-page'])

const searchTerm = defineModel('searchTerm', { type: String, default: '' })
</script>
