<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-slate-900 dark:text-white">Extraction Prompts</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Configure how the LLM extracts information from documents
        </p>
      </div>
      <BaseButton @click="emit('create')">
        <Plus class="h-5 w-5" />
        Create Prompt
      </BaseButton>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>

    <EmptyState
      v-else-if="prompts.length === 0"
      title="No prompts created yet"
      description="Create a prompt to guide the LLM in extracting information"
      action-text="Create Prompt"
      @action="emit('create')"
    />

    <template v-else>
      <FilterBar
        v-model:search="searchQuery"
        :total-count="prompts.length"
        item-label="prompts"
        search-placeholder="Search prompts..."
        :active-filters="activeFilters"
        class="mb-4"
        @clear-filter="clearSearch"
      />

      <DataTable
        :columns="columns"
        :items="filteredPrompts"
        row-key="id"
        expandable
        :expanded-keys="expandedKeys"
        empty-title="No prompts match your search"
        @expand="toggleExpand"
      >
        <template #cell-name="{ row: prompt }">
          <div class="min-w-0">
            <span class="text-sm font-medium text-slate-900 dark:text-white">{{
              prompt.name
            }}</span>
            <p v-if="prompt.description" class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {{ prompt.description }}
            </p>
          </div>
        </template>

        <template #cell-placeholder="{ row: prompt }">
          <StatusBadge v-if="hasPlaceholder(prompt as Prompt)" color="green" class="font-medium">
            Contains placeholder
          </StatusBadge>
          <span v-else class="text-sm text-slate-400 dark:text-slate-500">—</span>
        </template>

        <template #cell-created_at="{ row: prompt }">
          <span class="text-sm text-slate-500 dark:text-slate-400">
            {{ formatDate(prompt.created_at) }}
          </span>
        </template>

        <template #row-actions="{ row: prompt }">
          <BaseButton
            variant="icon"
            tone="blue"
            title="View Prompt"
            aria-label="View Prompt"
            @click.stop="emit('view', prompt as Prompt)"
          >
            <Eye class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="gray"
            title="Edit Prompt"
            aria-label="Edit Prompt"
            @click.stop="emit('edit', prompt as Prompt)"
          >
            <Pencil class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="red"
            title="Delete Prompt"
            aria-label="Delete Prompt"
            @click.stop="emit('delete', prompt as Prompt)"
          >
            <Trash2 class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
        </template>

        <template #expanded="{ row: prompt }">
          <div class="p-4 space-y-3">
            <div v-if="prompt.system_prompt" class="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider"
                  >System Prompt</span
                >
                <StatusBadge
                  v-if="prompt.system_prompt.includes('{document_content}')"
                  color="green"
                  label="Contains placeholder"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                {{ truncateText(prompt.system_prompt, 200) }}
              </p>
            </div>
            <div v-if="prompt.user_prompt" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider"
                  >User Prompt</span
                >
                <StatusBadge
                  v-if="prompt.user_prompt.includes('{document_content}')"
                  color="green"
                  label="Contains placeholder"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                {{ truncateText(prompt.user_prompt, 200) }}
              </p>
            </div>
          </div>
        </template>
      </DataTable>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { formatDate, truncateText } from '@/utils/formatters'
import { Eye, Pencil, Plus, Trash2 } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import DataTable from '@/components/common/DataTable.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import type { Prompt } from '@/types'

interface Props {
  prompts: Prompt[]
  isLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
})

const emit = defineEmits<{
  create: []
  view: [prompt: Prompt]
  edit: [prompt: Prompt]
  delete: [prompt: Prompt]
}>()

const expandedKeys = ref<number[]>([])
const searchQuery = ref('')

const filteredPrompts = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return props.prompts
  return props.prompts.filter(
    (p) =>
      (p.name || '').toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q),
  )
})

const activeFilters = computed(() =>
  searchQuery.value
    ? [{ key: 'search', label: `Search: "${searchQuery.value}"`, color: 'blue' }]
    : [],
)

const clearSearch = () => {
  searchQuery.value = ''
}

const toggleExpand = (id: number) => {
  const idx = expandedKeys.value.indexOf(id)
  if (idx > -1) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(id)
  }
}

const hasPlaceholder = (prompt: Prompt): boolean =>
  (!!prompt.system_prompt && prompt.system_prompt.includes('{document_content}')) ||
  (!!prompt.user_prompt && prompt.user_prompt.includes('{document_content}'))

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'placeholder', label: 'Placeholder' },
  { key: 'created_at', label: 'Created' },
]
</script>
