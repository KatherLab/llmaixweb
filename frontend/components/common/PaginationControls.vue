<template>
  <div
    v-if="totalPages > 1 || showPageSizeSelector"
    class="bg-surface px-4 py-3 flex items-center justify-between border-t border-default sm:px-6"
  >
    <div class="flex-1 flex justify-between sm:hidden">
      <button
        :disabled="modelValue === 1"
        class="relative inline-flex items-center px-4 py-2 border border-strong text-sm font-medium rounded-card text-content bg-surface hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed"
        @click="$emit('update:modelValue', modelValue - 1)"
      >
        {{ $t('common.pagination.previous') }}
      </button>
      <button
        :disabled="modelValue === totalPages"
        class="ml-3 relative inline-flex items-center px-4 py-2 border border-strong text-sm font-medium rounded-card text-content bg-surface hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed"
        @click="$emit('update:modelValue', modelValue + 1)"
      >
        {{ $t('common.pagination.next') }}
      </button>
    </div>
    <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
      <div>
        <p class="text-sm text-content">
          {{ $t('common.pagination.showing') }}
          <span class="font-medium">{{ (modelValue - 1) * (pageSize ?? 1) + 1 }}</span>
          {{ $t('common.pagination.to') }}
          <span class="font-medium">{{
            Math.min(modelValue * (pageSize ?? 1), totalItems ?? 0)
          }}</span>
          {{ $t('common.pagination.of') }}
          <span class="font-medium">{{ totalItems }}</span>
          {{ itemLabel }}
        </p>
      </div>
      <div class="flex items-center gap-4">
        <label v-if="showPageSizeSelector" class="text-sm text-content flex items-center gap-2">
          {{ $t('common.pagination.rows_per_page') }}
          <select
            :value="pageSize"
            class="border border-strong bg-surface rounded px-2 py-1 text-sm text-content focus:ring-ring focus:border-ring"
            @change="$emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
          >
            <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
          </select>
        </label>
        <nav
          v-if="totalPages > 1"
          class="relative z-0 inline-flex rounded-card shadow-sm -space-x-px"
          :aria-label="$t('common.pagination.label')"
        >
          <button
            :disabled="modelValue === 1"
            class="relative inline-flex items-center px-2 py-2 rounded-l-card border border-strong bg-surface text-sm font-medium text-content-muted hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('update:modelValue', 1)"
          >
            <span class="sr-only">{{ $t('common.pagination.first') }}</span>
            <ChevronsLeft class="h-5 w-5" aria-hidden="true" />
          </button>
          <button
            v-for="page in visiblePages"
            :key="page"
            :disabled="page === '...'"
            :aria-current="page === modelValue ? 'page' : undefined"
            :aria-label="
              page === '...'
                ? $t('common.pagination.ellipsis')
                : $t('common.pagination.page', { page })
            "
            :class="[
              'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
              page === modelValue
                ? 'z-10 bg-primary-soft border-primary text-primary'
                : 'bg-surface border-strong text-content-muted hover:bg-surface-muted',
              page === '...' ? 'cursor-default disabled:opacity-100' : '',
            ]"
            @click="page !== '...' && $emit('update:modelValue', page)"
          >
            {{ page }}
          </button>
          <button
            :disabled="modelValue === totalPages"
            class="relative inline-flex items-center px-2 py-2 rounded-r-card border border-strong bg-surface text-sm font-medium text-content-muted hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed"
            @click="$emit('update:modelValue', totalPages)"
          >
            <span class="sr-only">{{ $t('common.pagination.last') }}</span>
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
