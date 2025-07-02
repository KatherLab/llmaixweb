<template>
  <div class="space-y-6">
    <!-- Header with overall metrics -->
    <div class="bg-gradient-to-r from-blue-50 to-white rounded-lg p-6 border">
      <div class="flex justify-between items-start mb-4">
        <div>
          <h2 class="text-xl font-semibold text-gray-800">Trial #{{ evaluationDetail.trial_id }}</h2>
          <p class="text-gray-600">Model: {{ evaluationDetail.model || 'Unknown' }}</p>
          <p class="text-sm text-gray-500">{{ formatDate(evaluationDetail.created_at) }}</p>
        </div>
        <div class="text-right">
          <div class="text-3xl font-bold text-blue-600">
            {{ ((evaluationDetail.metrics?.accuracy || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-gray-500">Overall Accuracy</div>
        </div>
      </div>

      <!-- Key metrics grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-gray-800">{{ evaluationDetail.document_count || 0 }}</div>
          <div class="text-sm text-gray-500">Documents</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-green-600">
            {{ ((evaluationDetail.metrics?.precision || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-gray-500">Precision</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-yellow-600">
            {{ ((evaluationDetail.metrics?.recall || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-gray-500">Recall</div>
        </div>
        <div class="bg-white rounded-lg p-4 text-center border shadow-sm">
          <div class="text-lg font-semibold text-purple-600">
            {{ ((evaluationDetail.metrics?.f1_score || 0) * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-gray-500">F1 Score</div>
        </div>
      </div>
    </div>

    <!-- Field-level metrics -->
    <div v-if="evaluationDetail.fields && Object.keys(evaluationDetail.fields).length > 0" class="bg-white rounded-lg border p-6 shadow-sm">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Field-Level Performance</h3>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Field</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Accuracy</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precision</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recall</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">F1 Score</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="(fieldData, fieldName) in evaluationDetail.fields" :key="fieldName" class="hover:bg-gray-50">
              <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ fieldName }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm">
                <div class="flex items-center">
                  <div class="mr-2">{{ ((fieldData.accuracy || 0) * 100).toFixed(1) }}%</div>
                  <div class="w-16 bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full" :style="{width: `${(fieldData.accuracy || 0) * 100}%`}"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                {{ ((fieldData.precision || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                {{ ((fieldData.recall || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                {{ ((fieldData.f1_score || 0) * 100).toFixed(1) }}%
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm">
                <button
                  @click="$emit('view-field-errors', fieldName)"
                  class="text-red-600 hover:text-red-800 text-sm underline disabled:text-gray-400 disabled:no-underline disabled:cursor-not-allowed"
                  :disabled="!fieldData.error_count || fieldData.error_count === 0"
                >
                  {{ fieldData.error_count || 0 }} errors
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Document performance summary -->
    <div class="bg-white rounded-lg border p-6 shadow-sm">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-800">Document Performance Summary</h3>
        <button
          @click="$emit('view-document-details')"
          class="text-blue-600 hover:text-blue-800 text-sm underline"
        >
          View All Documents →
        </button>
      </div>

      <!-- Document performance distribution -->
      <div class="mb-4">
        <div class="flex items-center justify-between text-sm text-gray-600 mb-2">
          <span>Accuracy Distribution</span>
          <span>{{ documentStats.perfect }} perfect, {{ documentStats.good }} good, {{ documentStats.poor }} needs improvement</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-3">
          <div class="h-3 rounded-full flex">
            <div class="bg-green-500 rounded-l-full" :style="{width: `${documentStats.perfectPercent}%`}"></div>
            <div class="bg-yellow-500" :style="{width: `${documentStats.goodPercent}%`}"></div>
            <div class="bg-red-500 rounded-r-full" :style="{width: `${documentStats.poorPercent}%`}"></div>
          </div>
        </div>
        <div class="flex justify-between text-xs text-gray-500 mt-1">
          <span>Perfect (≥90%)</span>
          <span>Good (70-89%)</span>
          <span>Needs Review (<70%)</span>
        </div>
      </div>

      <!-- Quick document stats -->
      <div class="grid grid-cols-3 gap-4">
        <div class="text-center p-3 bg-green-50 rounded-lg border border-green-200">
          <div class="text-2xl font-bold text-green-700">{{ documentStats.perfect }}</div>
          <div class="text-sm text-green-600">Perfect Match</div>
        </div>
        <div class="text-center p-3 bg-yellow-50 rounded-lg border border-yellow-200">
          <div class="text-2xl font-bold text-yellow-700">{{ documentStats.good }}</div>
          <div class="text-sm text-yellow-600">Good Performance</div>
        </div>
        <div class="text-center p-3 bg-red-50 rounded-lg border border-red-200">
          <div class="text-2xl font-bold text-red-700">{{ documentStats.poor }}</div>
          <div class="text-sm text-red-600">Needs Review</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate } from '@/utils/formatters';

defineProps({
  evaluationDetail: {
    type: Object,
    required: true
  },
  documentStats: {
    type: Object,
    required: true
  }
});

defineEmits(['view-field-errors', 'view-document-details']);
</script>
