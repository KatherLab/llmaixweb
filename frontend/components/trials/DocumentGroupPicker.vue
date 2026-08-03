<template>
  <div class="mt-4 flex-1 min-h-0 flex flex-col">
    <div v-if="loadingGroups" class="text-center py-8">
      <LoadingSpinner />
    </div>
    <EmptyState
      v-else-if="!documentGroups || documentGroups.length === 0"
      :title="$t('trials.groups.empty')"
    />
    <!-- Scrolls inside the panel: the panel clips its overflow, so a project
         with many groups would otherwise lose the ones past the bottom edge. -->
    <!-- Scrolls inside the panel: the panel clips its overflow, so a project
         with many groups would otherwise lose the ones past the bottom edge.
         Selection is marked with an *inset* ring — an outset one is painted
         outside the box and gets clipped by this scroll container, which showed
         as a border visible only along the bottom edge. -->
    <div v-else class="space-y-1.5 flex-1 min-h-0 overflow-y-auto">
      <div
        v-for="group in documentGroups"
        :key="group.id"
        :class="
          selectedGroupId === group.id
            ? 'ring-2 ring-inset ring-primary bg-primary-soft'
            : 'border border-default'
        "
        class="rounded-card px-3 py-2 hover:bg-surface-muted transition-colors cursor-pointer flex items-center gap-3"
        :title="groupTitle(group)"
        @click="emit('toggle-group', group)"
      >
        <LoadingSpinner
          v-if="loadingGroupDocs && selectedGroupId === group.id"
          size="small"
          inline
          label=""
        />
        <input
          v-else
          :checked="selectedGroupId === group.id"
          class="h-4 w-4 shrink-0 text-primary focus:ring-ring border-strong rounded"
          type="checkbox"
          @change="emit('toggle-group', group)"
          @click.stop
        />

        <div class="flex-1 min-w-0">
          <div class="flex items-baseline gap-2">
            <span class="truncate text-sm font-medium text-content">{{ group.name }}</span>
            <span class="shrink-0 text-xs text-content-subtle">
              {{ $t('trials.groups.n_documents', { count: group.document_count ?? 0 }) }}
            </span>
          </div>
          <!-- Second line only when there is something to say; description and
               tags share it, and the full detail is in the row tooltip. -->
          <div
            v-if="group.description || (group.tags && group.tags.length)"
            class="flex items-center gap-2 min-w-0"
          >
            <span v-if="group.description" class="truncate text-xs text-content-muted">
              {{ group.description }}
            </span>
            <span v-if="group.tags && group.tags.length" class="shrink-0 flex items-center gap-1">
              <span
                v-for="tag in group.tags.slice(0, 2)"
                :key="tag"
                class="inline-flex items-center px-1.5 py-0.5 rounded-card text-[10px] font-medium bg-surface-sunken text-content-muted"
              >
                {{ tag }}
              </span>
              <span v-if="group.tags.length > 2" class="text-[10px] text-content-subtle"
                >+{{ group.tags.length - 2 }}</span
              >
            </span>
          </div>
        </div>

        <span class="shrink-0 text-[11px] text-content-subtle">
          {{ formatDate(group.created_at) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n({ useScope: 'global' })

/** Everything the card used to spell out, on hover. */
function groupTitle(group: DocumentSetSummary): string {
  const lines = [group.name]
  if (group.description) lines.push(group.description)
  lines.push(t('trials.groups.n_documents', { count: group.document_count ?? 0 }))
  if (group.preprocessing_config) {
    lines.push(t('trials.groups.config', { name: group.preprocessing_config.name }))
  }
  if (group.created_at) {
    lines.push(t('trials.groups.created', { date: formatDate(group.created_at) }))
  }
  if (group.tags?.length) lines.push(group.tags.join(', '))
  return lines.join('\n')
}
</script>
