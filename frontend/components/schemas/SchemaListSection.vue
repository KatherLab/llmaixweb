<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-gray-900 dark:text-white">JSON Schemas</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
          Define the structure for information extraction
        </p>
      </div>
      <button
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition-colors duration-200"
        @click="emit('create')"
      >
        <svg
          class="h-5 w-5 mr-2"
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
      </button>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <svg
        class="animate-spin h-8 w-8 text-indigo-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        ></circle>
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        ></path>
      </svg>
    </div>

    <div
      v-else-if="schemas.length === 0"
      class="bg-gray-50 dark:bg-slate-800 border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-xl p-12 text-center"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-400"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
        />
      </svg>
      <p class="mt-2 text-sm text-gray-600 dark:text-slate-300">No schemas created yet</p>
      <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
        Create a schema to define the structure for information extraction
      </p>
    </div>

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
