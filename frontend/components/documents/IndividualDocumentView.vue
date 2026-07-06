<template>
  <div class="space-y-6">
    <!-- Header with document info -->
    <div class="bg-surface-muted rounded-card p-6 border border-default">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-content">Document #{{ document.document_id }}</h2>
          <p class="text-content-muted">Individual field-by-field analysis</p>
          <BaseButton
            variant="link"
            tone="blue"
            class="mt-2 text-sm flex items-center"
            @click="$emit('back-to-documents')"
          >
            <ArrowLeft class="mr-1 h-4 w-4" />
            Back to Documents
          </BaseButton>
        </div>
        <div class="text-right">
          <div class="text-2xl font-bold text-primary">
            {{ (document.accuracy * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-content-muted">Accuracy</div>
        </div>
      </div>

      <!-- Show error prominently if exists -->
      <div
        v-if="document.error"
        class="my-4 p-3 bg-pink-50 dark:bg-pink-900/20 border border-pink-300 dark:border-pink-700 rounded flex items-center gap-2 text-pink-800 dark:text-pink-300 font-semibold"
      >
        <AlertTriangle class="h-5 w-5" />
        <span>{{ document.error }}</span>
      </div>

      <!-- Summary stats -->
      <div v-if="!document.error" class="grid grid-cols-3 gap-4">
        <div class="bg-surface rounded-card p-4 text-center border dark:border-default shadow-sm">
          <div class="text-lg font-semibold text-green-600 dark:text-green-400">
            {{ document.correct_fields }}
          </div>
          <div class="text-sm text-content-muted">Correct Fields</div>
        </div>
        <div class="bg-surface rounded-card p-4 text-center border dark:border-default shadow-sm">
          <div class="text-lg font-semibold text-red-600 dark:text-red-400">
            {{ document.total_fields - document.correct_fields }}
          </div>
          <div class="text-sm text-content-muted">Incorrect Fields</div>
        </div>
        <div class="bg-surface rounded-card p-4 text-center border dark:border-default shadow-sm">
          <div class="text-lg font-semibold text-content">
            {{ document.total_fields }}
          </div>
          <div class="text-sm text-content-muted">Total Fields</div>
        </div>
      </div>
    </div>

    <!-- Field-by-field analysis -->
    <div
      v-if="!document.error"
      class="bg-surface rounded-card border dark:border-default p-6 shadow-sm"
    >
      <h3 class="text-lg font-semibold text-content mb-4">Field-by-Field Analysis</h3>
      <div class="space-y-4">
        <div
          v-for="(fieldDetail, fieldName) in document.field_details"
          :key="fieldName"
          class="border rounded-card p-4"
          :class="{
            'border-green-200 bg-green-50 dark:border-green-700 dark:bg-green-900/20':
              fieldDetail.is_correct,
            'border-red-200 bg-red-50 dark:border-red-700 dark:bg-red-900/20':
              !fieldDetail.is_correct,
          }"
        >
          <div class="flex justify-between items-start mb-3">
            <h4 class="font-medium text-content">{{ fieldName }}</h4>
            <span
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="{
                'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300':
                  fieldDetail.is_correct,
                'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300':
                  !fieldDetail.is_correct,
              }"
            >
              {{ fieldDetail.is_correct ? 'Correct' : fieldDetail.error_type || 'Incorrect' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="bg-surface border dark:border-default rounded p-3">
              <h5 class="text-xs font-medium text-content-muted mb-1">Ground Truth</h5>
              <p class="text-sm text-content">
                {{ formatFieldValue(fieldDetail.ground_truth_value) }}
              </p>
            </div>
            <div class="bg-surface border dark:border-default rounded p-3">
              <h5 class="text-xs font-medium text-content-muted mb-1">Predicted</h5>
              <p class="text-sm text-content">
                {{ formatFieldValue(fieldDetail.predicted_value) }}
              </p>
            </div>
          </div>

          <div v-if="fieldDetail.confidence_score !== null" class="mt-3">
            <div class="flex items-center justify-between text-xs text-content-muted mb-1">
              <span>Confidence Score</span>
              <span>{{ (fieldDetail.confidence_score * 100).toFixed(1) }}%</span>
            </div>
            <div class="w-full bg-surface-sunken rounded-full h-2">
              <div
                class="h-2 rounded-full"
                :class="{
                  'bg-green-500': fieldDetail.confidence_score >= 0.8,
                  'bg-yellow-500':
                    fieldDetail.confidence_score >= 0.5 && fieldDetail.confidence_score < 0.8,
                  'bg-red-500': fieldDetail.confidence_score < 0.5,
                }"
                :style="{ width: `${fieldDetail.confidence_score * 100}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Document content -->
    <div class="bg-surface rounded-card border dark:border-default p-6 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-content">Document Content</h3>
        <BaseButton
          v-if="!documentContent && !loadingContent"
          variant="link"
          tone="blue"
          class="text-sm underline"
          @click="$emit('load-content', document.document_id)"
        >
          Load Content
        </BaseButton>
      </div>

      <div
        v-if="documentContent"
        class="bg-surface-muted p-4 rounded-card overflow-auto max-h-96 border border-default"
      >
        <div class="text-sm text-content whitespace-pre-wrap">
          {{ documentContent }}
        </div>
      </div>
      <div v-else-if="loadingContent" class="text-center py-8">
        <LoadingSpinner size="small" />
        <p class="mt-2 text-content-muted text-sm">Loading document content...</p>
      </div>
      <div v-else class="text-center py-8">
        <FileText class="h-10 w-10 mx-auto text-content-subtle mb-2" />
        <p class="text-sm text-content-muted">Click "Load Content" to view document text</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle, ArrowLeft, FileText } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import type { DocumentEvaluationDetail } from '@/types'

interface Props {
  document: DocumentEvaluationDetail
  documentContent?: string | null
  loadingContent?: boolean
}

withDefaults(defineProps<Props>(), {
  documentContent: null,
  loadingContent: false,
})

defineEmits<{
  'load-content': [documentId: number]
  'back-to-documents': []
}>()

const formatFieldValue = (value: unknown): string => {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>
