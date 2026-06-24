<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-gray-900 dark:text-white">JSON Schemas</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
          Define the structure for information extraction
        </p>
      </div>
      <BaseButton @click="emit('create')">
        <svg
          class="h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
        Create Schema
      </BaseButton>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>

    <EmptyState
      v-else-if="schemas.length === 0"
      title="No schemas created yet"
      description="Create a schema to define the structure for information extraction"
      action-text="Create Schema"
      @action="emit('create')"
    />

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="schema in schemas"
        :key="schema.id"
        class="bg-white dark:bg-slate-900 border rounded-xl shadow-sm overflow-hidden hover:shadow-md dark:hover:bg-slate-800 transition-shadow duration-200"
      >
        <div class="p-4 border-b dark:border-slate-700">
          <div class="flex justify-between items-start">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              {{ schema.schema_name }}
            </h3>
            <div class="flex space-x-2">
              <button
                class="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors duration-200"
                title="View Schema"
                @click="emit('view', schema)"
              >
                <svg
                  class="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path
                    fill-rule="evenodd"
                    d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                    clip-rule="evenodd"
                  />
                </svg>
              </button>
              <button
                class="text-gray-600 hover:text-gray-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors duration-200"
                title="Edit Schema"
                @click="emit('edit', schema)"
              >
                <svg
                  class="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                  />
                </svg>
              </button>
              <button
                class="text-gray-600 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-colors duration-200"
                title="Delete Schema"
                @click="emit('delete', schema)"
              >
                <svg
                  class="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clip-rule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
          <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
            Created: {{ formatDate(schema.created_at) }}
          </p>
        </div>
        <div class="bg-gray-50 dark:bg-slate-800 p-4 max-h-64 overflow-auto">
          <pre class="text-xs text-gray-700 dark:text-slate-300">{{
            formatJSON(schema.schema_definition)
          }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from '@/utils/formatters'
import { formatJSON } from '@/utils/schemaTemplates'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseButton from '@/components/common/BaseButton.vue'

defineProps({
  schemas: {
    type: Array,
    required: true,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['create', 'view', 'edit', 'delete'])
</script>
