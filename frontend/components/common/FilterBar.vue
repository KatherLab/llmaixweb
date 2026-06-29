<template>
  <div
    class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700"
  >
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
        class="px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400 transition-colors"
        title="Clear all filters"
        @click="$emit('clear-all')"
      >
        <X class="w-4 h-4" />
      </button>

      <!-- Count (right) -->
      <div v-if="showCount" class="ml-auto text-sm text-slate-500 dark:text-slate-400">
        {{ totalCount }} {{ itemLabel }}
      </div>
    </div>

    <!-- Custom range row (optional, caller-provided) -->
    <div
      v-if="$slots['custom-range']"
      class="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600"
    >
      <slot name="custom-range" />
    </div>

    <!-- Active filter chips (unified) -->
    <div
      v-if="hasActiveFilters"
      class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-600"
    >
      <span class="text-xs text-slate-500 dark:text-slate-400">Active filters:</span>
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

<script setup>
import { computed } from 'vue'
import { X } from '@lucide/vue'
import SearchInput from '@/components/common/SearchInput.vue'
import FilterChip from '@/components/common/FilterChip.vue'

const props = defineProps({
  // search
  search: { type: String, default: '' },
  searchable: { type: Boolean, default: true },
  searchPlaceholder: { type: String, default: 'Search...' },

  // count
  totalCount: { type: Number, default: 0 },
  showCount: { type: Boolean, default: true },
  itemLabel: { type: String, default: 'items' },

  // active filter chips: [{ key, label, color? }]
  activeFilters: { type: Array, default: () => [] },

  // clear-all button visibility (still only shown when filters active)
  showClear: { type: Boolean, default: true },
})

defineEmits(['update:search', 'search-input', 'clear-all', 'clear-filter'])

const hasActiveFilters = computed(() => props.activeFilters.length > 0)
</script>
