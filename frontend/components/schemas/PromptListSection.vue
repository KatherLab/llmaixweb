<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-content">{{ $t('prompt.list.title') }}</h2>
        <p class="mt-1 text-sm text-content-muted">
          {{ $t('prompt.list.subtitle') }}
        </p>
      </div>
      <BaseButton data-testid="create-prompt-open" @click="emit('create')">
        <Plus class="h-5 w-5" />
        {{ $t('prompt.list.create') }}
      </BaseButton>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>

    <EmptyState
      v-else-if="prompts.length === 0"
      :title="$t('prompt.list.empty_title')"
      :description="$t('prompt.list.empty_description')"
      :action-text="$t('prompt.list.create')"
      @action="emit('create')"
    />

    <template v-else>
      <FilterBar
        v-model:search="searchQuery"
        :total-count="prompts.length"
        :item-label="$t('prompt.list.item_label')"
        :search-placeholder="$t('prompt.list.search_placeholder')"
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
        :empty-title="$t('prompt.list.no_match')"
        @expand="toggleExpand"
      >
        <template #cell-name="{ row: prompt }">
          <div class="min-w-0">
            <span class="text-sm font-medium text-content">{{ prompt.name }}</span>
            <p v-if="prompt.description" class="mt-0.5 text-xs text-content-muted">
              {{ prompt.description }}
            </p>
          </div>
        </template>

        <template #cell-placeholder="{ row: prompt }">
          <StatusBadge v-if="hasPlaceholder(prompt as Prompt)" color="green" class="font-medium">
            {{ $t('prompt.common.contains_placeholder') }}
          </StatusBadge>
          <Tooltip
            v-else
            :text="$t('prompt.list.auto_injected_tooltip', { ph: '{document_content}' })"
          >
            <span
              class="text-sm text-content-subtle cursor-help border-b border-dotted border-default"
            >
              {{ $t('prompt.list.auto_injected') }}
            </span>
          </Tooltip>
        </template>

        <template #cell-created_at="{ row: prompt }">
          <span class="text-sm text-content-muted">
            {{ formatDate(prompt.created_at) }}
          </span>
        </template>

        <template #row-actions="{ row: prompt }">
          <BaseButton
            variant="icon"
            tone="blue"
            :title="$t('prompt.list.view')"
            :aria-label="$t('prompt.list.view')"
            @click.stop="emit('view', prompt as Prompt)"
          >
            <Eye class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="gray"
            :title="$t('prompt.list.edit')"
            :aria-label="$t('prompt.list.edit')"
            @click.stop="emit('edit', prompt as Prompt)"
          >
            <Pencil class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="red"
            :title="$t('prompt.list.delete')"
            :aria-label="$t('prompt.list.delete')"
            @click.stop="emit('delete', prompt as Prompt)"
          >
            <Trash2 class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
        </template>

        <template #expanded="{ row: prompt }">
          <div class="p-4 space-y-3">
            <div v-if="prompt.system_prompt" class="bg-surface-muted rounded-card p-4">
              <div class="flex items-center mb-2">
                <span class="text-xs font-medium text-content-muted uppercase tracking-wider">{{
                  $t('prompt.fields.system_prompt')
                }}</span>
                <StatusBadge
                  v-if="prompt.system_prompt.includes('{document_content}')"
                  color="green"
                  :label="$t('prompt.common.contains_placeholder')"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-content-muted whitespace-pre-wrap">
                {{ truncateText(prompt.system_prompt, 200) }}
              </p>
            </div>
            <div v-if="prompt.user_prompt" class="bg-primary-soft rounded-card p-4">
              <div class="flex items-center mb-2">
                <span class="text-xs font-medium text-primary uppercase tracking-wider">{{
                  $t('prompt.fields.user_prompt')
                }}</span>
                <StatusBadge
                  v-if="prompt.user_prompt.includes('{document_content}')"
                  color="green"
                  :label="$t('prompt.common.contains_placeholder')"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-content-muted whitespace-pre-wrap">
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
import { useI18n } from 'vue-i18n'
import { formatDate, truncateText } from '@/utils/formatters'
import { Eye, Pencil, Plus, Trash2 } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Tooltip from '@/components/common/Tooltip.vue'
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

const { t } = useI18n({ useScope: 'global' })

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
    ? [
        {
          key: 'search',
          label: t('prompt.list.search_chip', { query: searchQuery.value }),
          color: 'blue',
        },
      ]
    : [],
)

const clearSearch = () => {
  searchQuery.value = ''
}

const toggleExpand = (id: string | number) => {
  const idx = expandedKeys.value.indexOf(id as number)
  if (idx > -1) {
    expandedKeys.value.splice(idx, 1)
  } else {
    expandedKeys.value.push(id as number)
  }
}

const hasPlaceholder = (prompt: Prompt): boolean =>
  (!!prompt.system_prompt && prompt.system_prompt.includes('{document_content}')) ||
  (!!prompt.user_prompt && prompt.user_prompt.includes('{document_content}'))

const columns = computed(() => [
  { key: 'name', label: t('prompt.list.col_name') },
  { key: 'placeholder', label: t('prompt.list.col_placeholder') },
  { key: 'created_at', label: t('prompt.list.col_created') },
])
</script>
