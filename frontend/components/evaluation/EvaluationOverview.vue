<template>
  <div class="space-y-6">
    <!-- Header with overall metrics -->
    <div
      class="bg-gradient-to-r from-blue-50 to-white dark:from-slate-800 dark:to-slate-900 rounded-lg p-6 border border-slate-200 dark:border-slate-700"
    >
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-slate-800 dark:text-white">
            Trial #{{ evaluationDetail.trial_id }}
          </h2>
          <p class="text-slate-600 dark:text-slate-300">
            Model: {{ evaluationDetail.model || 'Unknown' }}
          </p>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            {{ formatDate(evaluationDetail.created_at) }}
          </p>
        </div>
        <div class="text-right">
          <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
            {{ ((evaluationDetail.metrics?.accuracy || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">Overall Accuracy</div>
        </div>
      </div>

      <!-- Key metrics grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          class="bg-white dark:bg-slate-900 rounded-lg p-4 text-center border border-slate-200 dark:border-slate-700 shadow-sm"
        >
          <div class="text-lg font-semibold text-slate-800 dark:text-white">
            {{ evaluationDetail.document_count || 0 }}
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">Documents</div>
        </div>
        <div
          class="bg-white dark:bg-slate-900 rounded-lg p-4 text-center border border-slate-200 dark:border-slate-700 shadow-sm"
        >
          <div class="text-lg font-semibold text-green-600 dark:text-green-400">
            {{ ((evaluationDetail.metrics?.precision || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">Precision</div>
        </div>
        <div
          class="bg-white dark:bg-slate-900 rounded-lg p-4 text-center border border-slate-200 dark:border-slate-700 shadow-sm"
        >
          <div class="text-lg font-semibold text-yellow-600 dark:text-yellow-400">
            {{ ((evaluationDetail.metrics?.recall || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">Recall</div>
        </div>
        <div
          class="bg-white dark:bg-slate-900 rounded-lg p-4 text-center border border-slate-200 dark:border-slate-700 shadow-sm"
        >
          <div class="text-lg font-semibold text-purple-600 dark:text-purple-400">
            {{ ((evaluationDetail.metrics?.f1_score || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">F1 Score</div>
        </div>
      </div>
    </div>

    <!-- Field-level metrics -->
    <div
      v-if="evaluationDetail.fields && Object.keys(evaluationDetail.fields).length > 0"
      class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-6 shadow-sm"
    >
      <h3 class="text-lg font-semibold text-slate-800 dark:text-white mb-4">
        Field-Level Performance
      </h3>
      <div class="overflow-x-auto">
        <table :class="t.table">
          <thead :class="t.thead">
            <tr>
              <th :class="t.th">Field</th>
              <th :class="t.th">Accuracy</th>
              <th :class="t.th">Precision</th>
              <th :class="t.th">Recall</th>
              <th :class="t.th">F1 Score</th>
              <th :class="t.th">Errors</th>
            </tr>
          </thead>
          <tbody :class="t.tbody">
            <tr
              v-for="(fieldData, fieldName) in evaluationDetail.fields"
              :key="fieldName"
              :class="t.tr"
            >
              <td
                class="px-4 py-3 whitespace-nowrap text-sm font-medium text-slate-900 dark:text-white"
              >
                {{ fieldName }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-700 dark:text-slate-300">
                <div class="flex items-center">
                  <div class="mr-2">{{ ((fieldData.accuracy || 0) * 100).toFixed(1) }}%</div>
                  <div class="w-16 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                    <div
                      class="bg-blue-600 h-2 rounded-full"
                      :style="{ width: `${(fieldData.accuracy || 0) * 100}%` }"
                    ></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                {{ ((fieldData.precision || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                {{ ((fieldData.recall || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                {{ ((fieldData.f1_score || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm">
                <BaseButton
                  variant="link"
                  tone="red"
                  class="text-sm underline"
                  :disabled="!fieldData.error_count || fieldData.error_count === 0"
                  @click="$emit('view-field-errors', fieldName)"
                >
                  {{ fieldData.error_count || 0 }} errors
                </BaseButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Document performance summary -->
    <div
      class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-6 shadow-sm"
    >
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-slate-800 dark:text-white">
          Document Performance Summary
        </h3>
        <BaseButton
          variant="link"
          tone="blue"
          class="text-sm underline"
          @click="$emit('view-document-details')"
        >
          View All Documents →
        </BaseButton>
      </div>

      <!-- Document performance distribution -->
      <div class="mb-4">
        <div
          class="flex items-center justify-between text-sm text-slate-600 dark:text-slate-300 mb-2"
        >
          <span>Accuracy Distribution</span>
          <span
            >{{ documentStats.perfect }} perfect, {{ documentStats.good }} good,
            {{ documentStats.poor }} needs improvement</span
          >
        </div>
        <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-3">
          <div class="h-3 rounded-full flex">
            <div
              class="bg-green-500 rounded-l-full"
              :style="{ width: `${documentStats.perfectPercent}%` }"
            ></div>
            <div class="bg-yellow-500" :style="{ width: `${documentStats.goodPercent}%` }"></div>
            <div
              class="bg-red-500 rounded-r-full"
              :style="{ width: `${documentStats.poorPercent}%` }"
            ></div>
          </div>
        </div>
        <div class="flex justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
          <span>Perfect (≥90%)</span>
          <span>Good (70-89%)</span>
          <span>Needs Review (&lt;70%)</span>
        </div>
      </div>

      <!-- Quick document stats -->
      <div class="grid grid-cols-3 gap-4">
        <div
          class="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800"
        >
          <div class="text-2xl font-bold text-green-700 dark:text-green-400">
            {{ documentStats.perfect }}
          </div>
          <div class="text-sm text-green-600 dark:text-green-500">Perfect Match</div>
        </div>
        <div
          class="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
        >
          <div class="text-2xl font-bold text-yellow-700 dark:text-yellow-400">
            {{ documentStats.good }}
          </div>
          <div class="text-sm text-yellow-600 dark:text-yellow-500">Good Performance</div>
        </div>
        <div
          class="text-center p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
        >
          <div class="text-2xl font-bold text-red-700 dark:text-red-400">
            {{ documentStats.poor }}
          </div>
          <div class="text-sm text-red-600 dark:text-red-500">Needs Review</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from '@/utils/formatters'
import BaseButton from '@/components/common/BaseButton.vue'
import { useTableClasses } from '@/composables/useTableClasses'

const t = useTableClasses()

defineProps({
  evaluationDetail: {
    type: Object,
    required: true,
  },
  documentStats: {
    type: Object,
    required: true,
  },
})

defineEmits(['view-field-errors', 'view-document-details'])
</script>
