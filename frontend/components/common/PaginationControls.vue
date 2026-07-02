<template>
  <div
    v-if="totalPages > 1 || showPageSizeSelector"
    class="bg-white dark:bg-slate-900 px-4 py-3 flex items-center justify-between border-t border-slate-200 dark:border-slate-700 sm:px-6"
  >
    <div class="flex-1 flex justify-between sm:hidden">
      <button
        :disabled="modelValue === 1"
        class="relative inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm font-medium rounded-md text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="$emit('update:modelValue', modelValue - 1)"
      >
        Previous
      </button>
      <button
        :disabled="modelValue === totalPages"
        class="ml-3 relative inline-flex items-center px-4 py-2 border border-slate-300 dark:border-slate-600 text-sm font-medium rounded-md text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="$emit('update:modelValue', modelValue + 1)"
      >
        Next
      </button>
    </div>
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
      <div>
        <p class="text-sm text-slate-700 dark:text-slate-300">
          Showing
          <span class="font-medium">{{ (modelValue - 1) * (pageSize ?? 1) + 1 }}</span>
          to
          <span class="font-medium">{{
            Math.min(modelValue * (pageSize ?? 1), totalItems ?? 0)
          }}</span>
          of
          <span class="font-medium">{{ totalItems }}</span>
          {{ itemLabel }}
        </p>
      </div>
      <div class="flex items-center gap-4">
        <label
          v-if="showPageSizeSelector"
          class="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-2"
        >
          Rows per page:
          <select
            :value="pageSize"
            class="border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 rounded px-2 py-1 text-sm text-slate-900 dark:text-white focus:ring-blue-500 focus:border-blue-500"
            @change="$emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>
        <nav
          v-if="totalPages > 1"
          class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
          aria-label="Pagination"
        >
          <button
            :disabled="modelValue === 1"
            class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('update:modelValue', 1)"
          >
            <span class="sr-only">First</span>
            <ChevronsLeft class="h-5 w-5" aria-hidden="true" />
          </button>
          <button
            v-for="page in visiblePages"
            :key="page"
            :disabled="page === '...'"
            :aria-current="page === modelValue ? 'page' : undefined"
            :aria-label="page === '...' ? 'ellipsis' : 'Page ' + page"
            :class="[
              'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
              page === modelValue
                ? 'z-10 bg-blue-50 dark:bg-blue-900 border-blue-500 dark:border-blue-400 text-blue-600 dark:text-blue-400'
                : 'bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800',
              page === '...' ? 'cursor-default disabled:opacity-100' : '',
            ]"
            @click="page !== '...' && $emit('update:modelValue', page)"
          >
            {{ page }}
          </button>
          <button
            :disabled="modelValue === totalPages"
            class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('update:modelValue', totalPages)"
          >
            <span class="sr-only">Last</span>
            <ChevronsRight class="h-5 w-5" aria-hidden="true" />
          </button>
        </nav>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronsLeft, ChevronsRight } from '@lucide/vue'

interface Props {
  modelValue: number
  totalPages: number
  visiblePages: (number | '...')[]
  totalItems?: number
  pageSize?: number
  showPageSizeSelector?: boolean
  pageSizeOptions?: number[]
  itemLabel?: string
}

withDefaults(defineProps<Props>(), {
  totalItems: 0,
  pageSize: 10,
  showPageSizeSelector: false,
  pageSizeOptions: () => [10, 25, 50, 100],
  itemLabel: 'results',
})

defineEmits<{
  (e: 'update:modelValue', value: number): void
  (e: 'update:pageSize', value: number): void
}>()
</script>
