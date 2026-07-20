<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-content">JSON Schemas</h2>
        <p class="mt-1 text-sm text-content-muted">
          Define the structure for information extraction
        </p>
      </div>
      <BaseButton data-testid="create-schema-open" @click="emit('create')">
        <Plus class="h-5 w-5" />
        Create Schema
      </BaseButton>
    </div>

    <SkeletonTable v-if="isLoading" :columns="2" :rows="4" />

    <EmptyState
      v-else-if="schemas.length === 0"
      title="No schemas created yet"
      description="Create a schema to define the structure for information extraction"
      action-text="Create Schema"
      @action="emit('create')"
    />

    <template v-else>
      <FilterBar
        v-model:search="searchQuery"
        :total-count="schemas.length"
        item-label="schemas"
        search-placeholder="Search schemas..."
        :active-filters="activeFilters"
        class="mb-4"
        @clear-filter="clearSearch"
      />

      <DataTable
        :columns="columns"
        :items="filteredSchemas"
        row-key="id"
        expandable
        :expanded-keys="expandedKeys"
        empty-title="No schemas match your search"
        @expand="toggleExpand"
      >
        <template #cell-schema_name="{ row: schema }">
          <span class="text-sm font-medium text-content">{{ schema.schema_name }}</span>
          <span class="block text-xs text-content-muted mt-0.5">{{
            summarizeSchema(schema.schema_definition)
          }}</span>
        </template>

        <template #cell-created_at="{ row: schema }">
          <span class="text-sm text-content-muted">
            {{ formatDate(schema.created_at) }}
          </span>
        </template>

        <template #row-actions="{ row: schema }">
          <BaseButton
            variant="icon"
            tone="blue"
            title="View Schema"
            aria-label="View Schema"
            @click.stop="emit('view', schema as Schema)"
          >
            <Eye class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="gray"
            title="Edit Schema"
            aria-label="Edit Schema"
            @click.stop="emit('edit', schema as Schema)"
          >
            <Pencil class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
          <BaseButton
            variant="icon"
            tone="red"
            title="Delete Schema"
            aria-label="Delete Schema"
            @click.stop="emit('delete', schema as Schema)"
          >
            <Trash2 class="w-5 h-5" aria-hidden="true" />
          </BaseButton>
        </template>

        <template #expanded="{ row: schema }">
          <div class="p-4 max-h-64 overflow-auto">
            <SchemaFieldList :schema-definition="schema.schema_definition" />
          </div>
        </template>
      </DataTable>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { formatDate } from '@/utils/formatters'
import { summarizeSchema } from '@/utils/schemaFieldList'
import { Eye, Pencil, Plus, Trash2 } from '@lucide/vue'
import SkeletonTable from '@/components/common/SkeletonTable.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import DataTable from '@/components/common/DataTable.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import SchemaFieldList from './SchemaFieldList.vue'
import type { Schema } from '@/types'

interface Props {
  schemas: Schema[]
  isLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
})

const emit = defineEmits<{
  create: []
  view: [schema: Schema]
  edit: [schema: Schema]
  delete: [schema: Schema]
}>()

const expandedKeys = ref<number[]>([])
const searchQuery = ref('')

const filteredSchemas = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return props.schemas
  return props.schemas.filter((s) => (s.schema_name || '').toLowerCase().includes(q))
})

const activeFilters = computed(() =>
  searchQuery.value
    ? [{ key: 'search', label: `Search: "${searchQuery.value}"`, color: 'blue' }]
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

const columns = [
  { key: 'schema_name', label: 'Name' },
  { key: 'created_at', label: 'Created' },
]
</script>
