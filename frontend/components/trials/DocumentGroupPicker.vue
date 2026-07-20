<template>
  <div class="mt-4 flex-1 flex flex-col">
    <div v-if="loadingGroups" class="text-center py-8">
      <LoadingSpinner />
    </div>
    <EmptyState
      v-else-if="!documentGroups || documentGroups.length === 0"
      :title="$t('trials.groups.empty')"
    />
    <div v-else class="space-y-2">
      <div
        v-for="group in documentGroups"
        :key="group.id"
        :class="{
          'ring-2 ring-ring bg-primary-soft': selectedGroupId === group.id,
        }"
        class="border border-default rounded-card p-4 hover:bg-surface-muted transition-colors cursor-pointer"
        @click="emit('toggle-group', group)"
      >
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h4 class="font-medium text-content">{{ group.name }}</h4>
            <p v-if="group.description" class="text-sm text-content-muted mt-1">
              {{ group.description }}
            </p>
            <div class="flex items-center gap-4 mt-2 text-xs text-content-muted">
              <span>{{
                $t('trials.groups.n_documents', { count: group.document_count ?? 0 })
              }}</span>
              <span v-if="group.preprocessing_config">
                {{ $t('trials.groups.config', { name: group.preprocessing_config.name }) }}
              </span>
              <span v-if="group.created_at">
                {{ $t('trials.groups.created', { date: formatDate(group.created_at) }) }}
              </span>
            </div>
            <div v-if="group.tags && group.tags.length > 0" class="mt-2 flex flex-wrap gap-1">
              <span
                v-for="tag in group.tags"
                :key="tag"
                class="inline-flex items-center px-2 py-0.5 rounded-card text-xs font-medium bg-surface-sunken text-content"
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
              class="h-4 w-4 text-primary focus:ring-ring border-strong rounded"
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
