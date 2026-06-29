<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h2 class="text-lg font-medium text-slate-900 dark:text-white">JSON Schemas</h2>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Define the structure for information extraction
        </p>
      </div>
      <BaseButton @click="emit('create')">
        <Plus class="h-5 w-5" />
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
            <h3 class="text-lg font-medium text-slate-900 dark:text-white">
              {{ schema.schema_name }}
            </h3>
            <div class="flex space-x-2">
              <button
                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors duration-200"
                title="View Schema"
                @click="emit('view', schema)"
              >
                <Eye class="h-5 w-5" />
              </button>
              <button
                class="text-slate-600 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 transition-colors duration-200"
                title="Edit Schema"
                @click="emit('edit', schema)"
              >
                <Pencil class="h-5 w-5" />
              </button>
              <button
                class="text-slate-600 hover:text-red-600 dark:text-slate-400 dark:hover:text-red-400 transition-colors duration-200"
                title="Delete Schema"
                @click="emit('delete', schema)"
              >
                <Trash2 class="h-5 w-5" />
              </button>
            </div>
          </div>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Created: {{ formatDate(schema.created_at) }}
          </p>
        </div>
        <div class="bg-slate-50 dark:bg-slate-800 p-4 max-h-64 overflow-auto">
          <pre class="text-xs text-slate-700 dark:text-slate-300">{{
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
import { Eye, Pencil, Plus, Trash2 } from '@lucide/vue'
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
