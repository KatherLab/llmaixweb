<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-gray-900 dark:text-white">Extraction Prompts</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
          Configure how the LLM extracts information from documents
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
        Create Prompt
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
      v-else-if="prompts.length === 0"
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
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
        />
      </svg>
      <p class="mt-2 text-sm text-gray-600 dark:text-slate-300">No prompts created yet</p>
      <p class="mt-1 text-sm text-gray-500 dark:text-slate-400">
        Create a prompt to guide the LLM in extracting information
      </p>
    </div>

    <div v-else class="grid grid-cols-1 gap-6">
      <div
        v-for="prompt in prompts"
        :key="prompt.id"
        class="bg-white dark:bg-slate-900 border rounded-xl shadow-sm overflow-hidden hover:shadow-md dark:hover:bg-slate-800 transition-shadow duration-200"
      >
        <div class="p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">{{ prompt.name }}</h3>
              <p v-if="prompt.description" class="mt-1 text-sm text-gray-500 dark:text-slate-400">
                {{ prompt.description }}
              </p>
              <p class="mt-2 text-xs text-gray-400 dark:text-slate-500">
                Created: {{ formatDate(prompt.created_at) }}
              </p>
            </div>
            <div class="flex space-x-2">
              <button
                class="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors duration-200"
                title="View Prompt"
                @click="emit('view', prompt)"
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
                title="Edit Prompt"
                @click="emit('edit', prompt)"
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
                title="Delete Prompt"
                @click="emit('delete', prompt)"
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

          <!-- Prompt Preview Cards -->
          <div class="space-y-3">
            <div v-if="prompt.system_prompt" class="bg-gray-50 dark:bg-slate-800 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider"
                  >System Prompt</span
                >
                <span
                  v-if="prompt.system_prompt.includes('{document_content}')"
                  class="ml-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 px-2 py-0.5 rounded-full"
                >
                  Contains placeholder
                </span>
              </div>
              <p class="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">
                {{ truncateText(prompt.system_prompt, 200) }}
              </p>
            </div>
            <div v-if="prompt.user_prompt" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider"
                  >User Prompt</span
                >
                <span
                  v-if="prompt.user_prompt.includes('{document_content}')"
                  class="ml-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 px-2 py-0.5 rounded-full"
                >
                  Contains placeholder
                </span>
              </div>
              <p class="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">
                {{ truncateText(prompt.user_prompt, 200) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate, truncateText } from '@/utils/formatters'

defineProps({
  prompts: {
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
