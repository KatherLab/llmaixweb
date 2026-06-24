<template>
  <div
    class="bg-gradient-to-br from-white via-blue-50 to-white shadow-inner rounded-xl p-6 mb-7 border border-gray-100"
  >
    <div class="flex flex-col md:flex-row md:justify-between gap-6">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h2 class="text-xl font-bold text-blue-900 truncate">
            {{ trial.name || `Trial #${trial.id}` }}
          </h2>
          <StatusBadge v-if="trial.status" :status="trial.status" class="ml-2 shadow" />
        </div>
        <div v-if="trial.description" class="text-gray-700 text-sm mb-1">
          {{ trial.description }}
        </div>
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600 mt-1">
          <span
            ><span class="font-semibold">Started:</span>
            {{ formatDate(trial.created_at, true) }}</span
          >
          <span><span class="font-semibold">Model:</span> {{ trial.llm_model }}</span>
          <span v-if="trial.prompt"
            ><span class="font-semibold">Prompt:</span>
            <span class="text-gray-800">{{ trial.prompt.name || '[unnamed prompt]' }}</span></span
          >
          <span v-if="trial.document_set"
            ><span class="font-semibold">Document Set:</span>
            <span class="text-gray-800">{{
              trial.document_set.name || 'Set #' + trial.document_set.id
            }}</span></span
          >
          <span
            ><span class="font-semibold">Documents:</span>
            {{ trial.document_ids?.length || 0 }}</span
          >
        </div>
      </div>
      <div class="flex flex-col items-start md:items-end gap-2 min-w-[200px]">
        <div class="flex gap-2">
          <BaseButton variant="secondary" size="sm" class="shadow-sm" @click="$emit('open-schema')">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            View Schema
          </BaseButton>
          <BaseButton variant="secondary" size="sm" class="shadow-sm" @click="$emit('open-prompt')">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 9h8m-8 4h8m-8 4h5M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z"
              />
            </svg>
            View Prompt
          </BaseButton>
        </div>
        <span class="text-sm bg-blue-50 px-4 py-2 rounded-lg font-medium text-blue-800 shadow-sm">
          {{ trial.results?.length || 0 }} documents processed
        </span>
        <span
          v-if="totalUsage.total_tokens !== undefined"
          class="text-xs bg-blue-100 px-3 py-1 rounded-lg font-semibold text-blue-800 mt-1"
          title="Sum of prompt and completion tokens across all results"
        >
          Usage: {{ totalUsage.prompt_tokens || 0 }} prompt /
          {{ totalUsage.completion_tokens || 0 }} completion /
          <b>{{ totalUsage.total_tokens || 0 }}</b> total tokens
        </span>
        <div
          v-if="trial.advanced_options && Object.keys(trial.advanced_options).length"
          class="mt-2 bg-white rounded-lg border border-blue-100 px-4 py-2 shadow text-xs max-w-xs"
        >
          <div class="text-xs font-semibold text-blue-700 mb-1">LLM Advanced Options</div>
          <ul>
            <li
              v-for="(value, key) in trial.advanced_options"
              :key="key"
              class="flex items-center gap-1 mb-0.5"
            >
              <span class="font-medium capitalize">{{ key.replace(/_/g, ' ') }}:</span>
              <span class="text-blue-900">{{ value }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { formatDate } from '@/utils/formatters.js'

defineProps({
  trial: {
    type: Object,
    required: true,
  },
  totalUsage: {
    type: Object,
    required: true,
  },
})

defineEmits(['open-schema', 'open-prompt'])
</script>
