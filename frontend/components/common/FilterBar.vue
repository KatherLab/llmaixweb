<template>
  <div class="bg-surface-muted rounded-modal p-4 border border-default">
    <!-- Top row: Search + caller-provided filter controls + count -->
    <div class="flex flex-wrap items-center gap-3">
      <!-- Search (left) -->
      <SearchInput
        v-if="searchable"
        :model-value="search"
        :placeholder="searchPlaceholder"
        @update:model-value="$emit('update:search', $event)"
        @input="$emit('search-input')"
      />

      <!-- Caller-provided filter controls (selects, toggles, etc.) -->
      <slot name="filters" />

      <!-- Clear all (X) -->
      <button
        v-if="showClear && hasActiveFilters"
        class="px-3 py-2 text-sm text-content-muted hover:text-red-600 dark:hover:text-red-400 transition-colors"
        :title="$t('common.filter_bar.clear_all')"
        @click="$emit('clear-all')"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Count (right) -->
      <div v-if="showCount" class="ml-auto text-sm text-content-muted">
        {{ totalCount }} {{ itemLabel }}
      </div>
    </div>

    <!-- Custom range row (optional, caller-provided) -->
    <div
      v-if="$slots['custom-range']"
      class="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-default"
    >
      <slot name="custom-range" />
    </div>

    <!-- Active filter chips (unified) -->
    <div
      v-if="hasActiveFilters"
      class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-default"
    >
      <span class="text-xs text-content-muted">{{ $t('common.filter_bar.active_filters') }}</span>
      <FilterChip
        v-for="filter in activeFilters"
        :key="filter.key"
        :label="filter.label"
        :color="filter.color || 'blue'"
        @remove="$emit('clear-filter', filter.key)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { X } from '@lucide/vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'

export interface ActiveFilter {
  key: string
  label: string
  color?: string
}

interface Props {
  // search
  search?: string
  searchable?: boolean
  searchPlaceholder?: string

  // count
  totalCount?: number
  showCount?: boolean
  itemLabel?: string

  // active filter chips: [{ key, label, color? }]
  activeFilters?: ActiveFilter[]

  // clear-all button visibility (still only shown when filters active)
  showClear?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  search: '',
  searchable: true,
  searchPlaceholder: '',
  totalCount: 0,
  showCount: true,
  itemLabel: 'items',
  activeFilters: () => [],
  showClear: true,
})

defineEmits<{
  (e: 'update:search', value: string): void
  (e: 'search-input'): void
  (e: 'clear-all'): void
  (e: 'clear-filter', key: string): void
}>()

const hasActiveFilters = computed(() => props.activeFilters.length > 0)
</script>
