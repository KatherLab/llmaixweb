<template>
  <div class="mt-4 flex-1 flex flex-col">
    <div v-if="loadingGroups" class="text-center py-8">
      <LoadingSpinner />
    </div>
    <EmptyState
      v-else-if="!documentGroups || documentGroups.length === 0"
      title="No document groups available"
    />
    <div v-else class="space-y-2">
      <div
        v-for="group in documentGroups"
        :key="group.id"
        :class="{
          'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/30': selectedGroupId === group.id,
        }"
        class="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
        @click="emit('toggle-group', group)"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h4 class="font-medium text-slate-900 dark:text-white">{{ group.name }}</h4>
            <p v-if="group.description" class="text-sm text-slate-600 dark:text-slate-400 mt-1">
              {{ group.description }}
            </p>
            <div class="flex items-center gap-4 mt-2 text-xs text-slate-500 dark:text-slate-400">
              <span>{{ group.document_count ?? 0 }} documents</span>
              <span v-if="group.preprocessing_config">
                Config: {{ group.preprocessing_config.name }}
              </span>
              <span v-if="group.created_at"> Created: {{ formatDate(group.created_at) }} </span>
            </div>
            <div v-if="group.tags && group.tags.length > 0" class="mt-2 flex flex-wrap gap-1">
              <span
                v-for="tag in group.tags"
                :key="tag"
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200"
              >
                {{ tag }}
              </span>
            </div>
          </div>
          <div class="ml-4">
            <LoadingSpinner v-if="loadingGroupDocs && selectedGroupId === group.id" size="small" />
            <input
              v-else
              :checked="selectedGroupId === group.id"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-600 dark:bg-slate-700 rounded"
              type="checkbox"
              @change="emit('toggle-group', group)"
              @click.stop
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/formatters'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { DocumentSetSummary } from '@/types'

withDefaults(
  defineProps<{
    documentGroups?: DocumentSetSummary[]
    loadingGroups?: boolean
    loadingGroupDocs?: boolean
    selectedGroupId?: number | null
  }>(),
  {
    documentGroups: () => [],
    loadingGroups: false,
    loadingGroupDocs: false,
    selectedGroupId: null,
  },
)

const emit = defineEmits<{ 'toggle-group': [group: DocumentSetSummary] }>()
</script>
