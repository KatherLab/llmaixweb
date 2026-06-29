<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-slate-900 dark:text-white">Extraction Prompts</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Configure how the LLM extracts information from documents
        </p>
      </div>
      <BaseButton @click="emit('create')">
        <Plus class="h-5 w-5" />
        Create Prompt
      </BaseButton>
    </div>

    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>

    <EmptyState
      v-else-if="prompts.length === 0"
      title="No prompts created yet"
      description="Create a prompt to guide the LLM in extracting information"
      action-text="Create Prompt"
      @action="emit('create')"
    />

    <div v-else class="grid grid-cols-1 gap-6">
      <div
        v-for="prompt in prompts"
        :key="prompt.id"
        class="bg-white dark:bg-slate-900 border rounded-xl shadow-sm overflow-hidden hover:shadow-md dark:hover:bg-slate-800 transition-shadow duration-200"
      >
        <div class="p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-medium text-slate-900 dark:text-white">{{ prompt.name }}</h3>
              <p v-if="prompt.description" class="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {{ prompt.description }}
              </p>
              <p class="mt-2 text-xs text-slate-400 dark:text-slate-500">
                Created: {{ formatDate(prompt.created_at) }}
              </p>
            </div>
            <div class="flex space-x-2">
              <button
                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors duration-200"
                title="View Prompt"
                @click="emit('view', prompt)"
              >
                <Eye class="h-5 w-5" />
              </button>
              <button
                class="text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors duration-200"
                title="Edit Prompt"
                @click="emit('edit', prompt)"
              >
                <Pencil class="h-5 w-5" />
              </button>
              <button
                class="text-slate-600 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-colors duration-200"
                title="Delete Prompt"
                @click="emit('delete', prompt)"
              >
                <Trash2 class="h-5 w-5" />
              </button>
            </div>
          </div>

          <!-- Prompt Preview Cards -->
          <div class="space-y-3">
            <div v-if="prompt.system_prompt" class="bg-slate-50 dark:bg-slate-800 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider"
                  >System Prompt</span
                >
                <StatusBadge
                  v-if="prompt.system_prompt.includes('{document_content}')"
                  color="green"
                  label="Contains placeholder"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                {{ truncateText(prompt.system_prompt, 200) }}
              </p>
            </div>
            <div v-if="prompt.user_prompt" class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div class="flex items-center mb-2">
                <span
                  class="text-xs font-medium text-blue-600 dark:text-blue-400 uppercase tracking-wider"
                  >User Prompt</span
                >
                <StatusBadge
                  v-if="prompt.user_prompt.includes('{document_content}')"
                  color="green"
                  label="Contains placeholder"
                  class="ml-2"
                />
              </div>
              <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
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
import { Eye, Pencil, Plus, Trash2 } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

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
