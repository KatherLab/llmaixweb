<template>
  <div class="bg-surface shadow-inner rounded-modal p-6 mb-7 border border-default">
    <div class="flex flex-col md:flex-row md:justify-between gap-6">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h2 class="text-xl font-bold text-primary truncate">
            {{ trial.name || `Trial #${trial.id}` }}
          </h2>
          <StatusBadge v-if="trial.status" :status="trial.status" class="ml-2 shadow" />
        </div>
        <div v-if="trial.description" class="text-content-muted text-sm mb-1">
          {{ trial.description }}
        </div>
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-content-muted mt-1">
          <span
            ><span class="font-semibold">Started:</span>
            {{ formatDate(trial.created_at, true) }}</span
          >
          <span><span class="font-semibold">Model:</span> {{ trial.llm_model }}</span>
          <span v-if="trial.prompt"
            ><span class="font-semibold">Prompt:</span>
            <span class="text-content">{{ trial.prompt.name || '[unnamed prompt]' }}</span></span
          >
          <span v-if="trial.document_set"
            ><span class="font-semibold">Document Set:</span>
            <span class="text-content">{{
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
            <FileText class="h-4 w-4" />
            View Schema
          </BaseButton>
          <BaseButton variant="secondary" size="sm" class="shadow-sm" @click="$emit('open-prompt')">
            <FileText class="h-4 w-4" />
            View Prompt
          </BaseButton>
        </div>
        <span
          class="text-sm bg-primary-soft px-4 py-2 rounded-card font-medium text-primary shadow-sm"
        >
          {{ resultsCount || 0 }} documents processed
        </span>
        <span
          v-if="totalUsage.total_tokens !== undefined"
          class="text-xs bg-primary-soft px-3 py-1 rounded-card font-semibold text-primary mt-1"
          title="Sum of prompt and completion tokens across all results"
        >
          Usage: {{ totalUsage.prompt_tokens || 0 }} prompt /
          {{ totalUsage.completion_tokens || 0 }} completion /
          <b>{{ totalUsage.total_tokens || 0 }}</b> total tokens
        </span>
        <div
          v-if="trial.advanced_options && Object.keys(trial.advanced_options).length"
          class="mt-2 bg-surface rounded-card border border-default px-4 py-2 shadow text-xs max-w-xs"
        >
          <div class="text-xs font-semibold text-primary mb-1">LLM Advanced Options</div>
          <ul>
            <li
              v-for="(value, key) in trial.advanced_options"
              :key="key"
              class="flex items-center gap-1 mb-0.5"
            >
              <span class="font-medium capitalize text-content-muted"
                >{{ key.replace(/_/g, ' ') }}:</span
              >
              <span class="text-primary">{{ value }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileText } from '@lucide/vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { formatDate } from '@/utils/formatters'
import type { Trial } from '@/types'

interface TokenUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}

defineProps<{
  trial: Trial
  totalUsage: TokenUsage
  resultsCount?: number
}>()

defineEmits<{ 'open-schema': []; 'open-prompt': [] }>()
</script>
