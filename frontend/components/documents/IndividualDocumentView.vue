<template>
  <div class="space-y-6">
    <!-- Header with document info -->
    <div class="bg-gradient-to-r from-slate-50 to-white rounded-lg p-6 border">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-slate-800">Document #{{ document.document_id }}</h2>
          <p class="text-slate-600">Individual field-by-field analysis</p>
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
          <div class="text-2xl font-bold text-blue-600">
            {{ (document.accuracy * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-slate-500">Accuracy</div>
        </div>
      </div>

      <!-- Show error prominently if exists -->
      <div
        v-if="document.error"
        class="my-4 p-3 bg-pink-50 border border-pink-300 rounded flex items-center gap-2 text-pink-800 font-semibold"
      >
        <AlertTriangle class="h-5 w-5" />
        <span>{{ document.error }}</span>
      </div>

      <!-- Summary stats -->
      <div v-if="!document.error" class="grid grid-cols-3 gap-4">
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-green-600">{{ document.correct_fields }}</div>
          <div class="text-sm text-slate-500">Correct Fields</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-red-600">
            {{ document.total_fields - document.correct_fields }}
          </div>
          <div class="text-sm text-slate-500">Incorrect Fields</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-slate-800">{{ document.total_fields }}</div>
          <div class="text-sm text-slate-500">Total Fields</div>
        </div>
      </div>
    </div>

    <!-- Field-by-field analysis -->
    <div v-if="!document.error" class="bg-white rounded-lg border p-6 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-4">Field-by-Field Analysis</h3>
      <div class="space-y-4">
        <div
          v-for="(fieldDetail, fieldName) in document.field_details"
          :key="fieldName"
          class="border rounded-lg p-4"
          :class="{
            'border-green-200 bg-green-50': fieldDetail.is_correct,
            'border-red-200 bg-red-50': !fieldDetail.is_correct,
          }"
        >
          <div class="flex justify-between items-start mb-3">
            <h4 class="font-medium text-slate-900">{{ fieldName }}</h4>
            <span
              class="px-2 py-1 rounded-full text-xs font-medium"
              :class="{
                'bg-green-100 text-green-800': fieldDetail.is_correct,
                'bg-red-100 text-red-800': !fieldDetail.is_correct,
              }"
            >
              {{ fieldDetail.is_correct ? 'Correct' : fieldDetail.error_type || 'Incorrect' }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="bg-white border rounded p-3">
              <h5 class="text-xs font-medium text-slate-700 mb-1">Ground Truth</h5>
              <p class="text-sm text-slate-800">
                {{ formatFieldValue(fieldDetail.ground_truth_value) }}
              </p>
            </div>
            <div class="bg-white border rounded p-3">
              <h5 class="text-xs font-medium text-slate-700 mb-1">Predicted</h5>
              <p class="text-sm text-slate-800">
                {{ formatFieldValue(fieldDetail.predicted_value) }}
              </p>
            </div>
          </div>

          <div v-if="fieldDetail.confidence_score !== null" class="mt-3">
            <div class="flex items-center justify-between text-xs text-slate-600 mb-1">
              <span>Confidence Score</span>
              <span>{{ (fieldDetail.confidence_score * 100).toFixed(1) }}%</span>
            </div>
            <div class="w-full bg-slate-200 rounded-full h-2">
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
    <div class="bg-white rounded-lg border p-6 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-slate-800">Document Content</h3>
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
        class="bg-slate-50 p-4 rounded-md overflow-auto max-h-96 border border-slate-200"
      >
        <div class="text-sm text-slate-800 whitespace-pre-wrap">{{ documentContent }}</div>
      </div>
      <div v-else-if="loadingContent" class="text-center py-8">
        <LoadingSpinner size="small" />
        <p class="mt-2 text-slate-500 text-sm">Loading document content...</p>
      </div>
      <div v-else class="text-center py-8">
        <FileText class="h-10 w-10 mx-auto text-slate-400 mb-2" />
        <p class="text-sm text-slate-500">Click "Load Content" to view document text</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { AlertTriangle, ArrowLeft, FileText } from '@lucide/vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
  documentContent: {
    type: String,
    default: null,
  },
  loadingContent: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['load-content', 'back-to-documents'])

const formatFieldValue = (value) => {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>
