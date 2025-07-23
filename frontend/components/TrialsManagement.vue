<template>
  <div class="trials-management p-4">
    <div class="header flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Trials</h1>
        <p class="text-gray-600">Run information extraction trials on your documents</p>
      </div>
      <div class="flex gap-4">
        <label class="flex items-center">
          <input
            type="checkbox"
            v-model="showCompleted"
            class="mr-2"
          />
          Show completed trials
        </label>
        <button
          @click="openCreateTrialModal"
          class="px-4 py-2 rounded-md font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed"
          :disabled="isLoading || schemas.length === 0 || documents.length === 0 || prompts.length === 0"
        >
          Start New Trial
        </button>
      </div>
    </div>

    <ErrorBanner v-if="error" :message="error" />
    <LoadingSpinner v-if="isLoading" />

    <EmptyState
      v-else-if="trials.length === 0"
      title="No trials yet"
      description="Run a trial to extract structured information from your documents"
      actionText="Start a Trial"
      @action="openCreateTrialModal"
      :disabled="schemas.length === 0 || documents.length === 0 || prompts.length === 0"
    >
      <template #icon>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </template>
    </EmptyState>

    <div v-else-if="filteredTrials.length === 0" class="text-center py-8 bg-gray-50 rounded-md">
      <p>No trials match your filter criteria.</p>
    </div>

    <!-- Integrated Trial Cards -->
    <div v-else class="space-y-4">
      <div
        v-for="trial in filteredTrials"
        :key="trial.id"
        class="border rounded-lg overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow"
      >
        <!-- Trial Header -->
        <div class="p-4">
          <div class="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4">
            <!-- Trial Info -->
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-3">
                <h3 class="font-semibold text-lg">Trial #{{ trial.id }}</h3>
                <span :class="['text-xs px-2 py-1 rounded-full font-medium', getStatusClass(trial.status)]">
                  {{ trial.status }}
                </span>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm text-gray-600">
                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>{{ trial.document_ids?.length || 0 }} document(s)</span>
                </div>

                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                  </svg>
                  <span>{{ trial.llm_model || 'Unknown Model' }}</span>
                </div>

                <div class="flex items-center gap-2" v-if="getSchemaForTrial(trial)">
                  <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>{{ getSchemaForTrial(trial)?.schema_name }}</span>
                </div>

                <div class="flex items-center gap-2" v-if="getPromptForTrial(trial)">
                  <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span>{{ getPromptForTrial(trial)?.name }}</span>
                </div>

                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{{ formatDate(trial.created_at) }}</span>
                </div>
              </div>
            </div>

            <!-- Progress/Results -->
            <div class="flex-shrink-0">
              <!-- Progress for active trials -->
              <div v-if="isTrialActive(trial)" class="w-full lg:w-40">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-blue-600">Processing</span>
                  <span class="text-sm text-gray-500">{{ getProgressPercentage(trial) }}%</span>
                </div>
                <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-blue-500 transition-all duration-500 ease-out"
                    :style="{ width: `${getProgressPercentage(trial)}%` }"
                  ></div>
                </div>
              </div>

              <!-- Results summary for completed trials -->
              <div v-else-if="trial.results && trial.results.length > 0" class="text-sm">
                <div class="flex items-center gap-2 text-green-600 font-medium">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{{ getResultSummary(trial) }}</span>
                </div>
              </div>

              <!-- Failed state -->
              <div v-else-if="trial.status === 'failed'" class="text-sm">
                <div class="flex items-center gap-2 text-red-600 font-medium">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Processing failed</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions Footer -->
        <div class="border-t bg-gray-50 px-4 py-3 flex justify-between items-center">
          <!-- Left side - Schema and Prompt buttons -->
          <div class="flex gap-2">
            <button
              v-if="getSchemaForTrial(trial)"
              @click="viewTrialSchema(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View Schema
            </button>

            <button
              v-if="getPromptForTrial(trial)"
              @click="viewTrialPrompt(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              View Prompt
            </button>
          </div>

          <!-- Right side - Action buttons -->
          <div class="flex gap-2">
            <!-- Download button -->
            <button
              v-if="trial.results && trial.results.length > 0"
              @click="openDownloadModal(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </button>

            <!-- View Results button -->
            <button
              v-if="trial.results && trial.results.length > 0"
              @click="viewTrialResults(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View Results
            </button>

            <!-- Retry button -->
            <button
              v-if="['completed', 'failed'].includes(trial.status)"
              @click="retryTrial(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retry
            </button>

            <button
              v-if="trial.results && trial.results.length > 0"
              @click="saveAsDocumentGroup(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
              title="Save document selection as reusable group"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14v6m-3-3h6M6 10h2a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2zm10 0h2a2 2 0 002-2V6a2 2 0 00-2-2h-2a2 2 0 00-2 2v2a2 2 0 002 2zM6 20h2a2 2 0 002-2v-2a2 2 0 00-2-2H6a2 2 0 00-2 2v2a2 2 0 002 2z" />
              </svg>
              Save Document Group
            </button>

            <!-- Delete button -->
            <button
              @click="confirmDeleteTrial(trial)"
              class="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-white border border-red-300 text-red-600 rounded-md hover:bg-red-50 transition-colors"
            >
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateTrialModal
      v-if="isModalOpen"
      :open="isModalOpen"
      :documents="documents"
      :schemas="schemas"
      :prompts="prompts"
      :projectId=props.projectId
      @close="isModalOpen = false"
      @create="handleCreateTrial"
    />

    <ConfirmationDialog
      v-if="isConfirmDialogOpen"
      :open="isConfirmDialogOpen"
      title="Delete Trial"
      message="Are you sure you want to delete this trial? This action cannot be undone."
      @confirm="deleteTrial"
      @cancel="isConfirmDialogOpen = false"
    />

    <TrialResults
      v-if="showTrialResultsModal"
      :isModal="true"
      :projectId="props.projectId"
      :trialId="selectedTrialId"
      @close="showTrialResultsModal = false"
    />

    <!-- Prompt Viewer Modal (Built-in) -->
    <div v-if="showPromptModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" @click.self="showPromptModal = false">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div class="flex justify-between items-center p-6 border-b">
          <h3 class="text-lg font-semibold">Trial Prompt</h3>
          <button @click="showPromptModal = false" class="text-gray-500 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="p-6 overflow-y-auto max-h-[calc(90vh-160px)]">
          <div class="space-y-4">
            <div class="bg-gray-50 p-4 rounded-lg">
              <h4 class="font-medium text-gray-900 mb-2">{{ selectedPrompt?.name }}</h4>
              <p v-if="selectedPrompt?.description" class="text-sm text-gray-600 mb-4">{{ selectedPrompt.description }}</p>

              <div class="space-y-4">
                <div v-if="selectedPrompt?.system_prompt">
                  <h5 class="font-medium text-gray-700 mb-2">System Prompt:</h5>
                  <div class="bg-white border rounded-md">
                    <pre class="text-sm text-gray-700 p-4 overflow-auto whitespace-pre-wrap">{{ selectedPrompt.system_prompt }}</pre>
                  </div>
                </div>

                <div v-if="selectedPrompt?.user_prompt">
                  <h5 class="font-medium text-gray-700 mb-2">User Prompt:</h5>
                  <div class="bg-white border rounded-md">
                    <pre class="text-sm text-gray-700 p-4 overflow-auto whitespace-pre-wrap">{{ selectedPrompt.user_prompt }}</pre>
                  </div>
                </div>

                <div v-if="!selectedPrompt?.system_prompt && !selectedPrompt?.user_prompt" class="text-gray-500 text-center py-4">
                  No prompt content available
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Fixed footer with proper spacing -->
        <div class="flex justify-end gap-3 p-6 border-t bg-gray-50">
          <button
            @click="showPromptModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          <button
            @click="copyPromptToClipboard"
            class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Copy to Clipboard
          </button>
        </div>
      </div>
    </div>


    <!-- Schema Viewer Modal (Built-in) -->
    <div v-if="showSchemaModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" @click.self="showSchemaModal = false">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div class="flex justify-between items-center p-6 border-b">
          <h3 class="text-lg font-semibold">Trial Schema</h3>
          <button @click="showSchemaModal = false" class="text-gray-500 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="p-6 overflow-y-auto max-h-[calc(90vh-160px)]">
          <div class="space-y-4">
            <div class="bg-gray-50 p-4 rounded-lg">
              <h4 class="font-medium text-gray-900 mb-3">{{ selectedSchema?.schema_name }}</h4>
              <div class="bg-white border rounded-md">
                <pre class="text-sm text-gray-700 p-4 overflow-auto whitespace-pre-wrap">{{ formatJsonSchema(selectedSchema?.schema_definition) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- Fixed footer with proper spacing -->
        <div class="flex justify-end gap-3 p-6 border-t bg-gray-50">
          <button
            @click="showSchemaModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          <button
            @click="copySchemaToClipboard"
            class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Copy to Clipboard
          </button>
        </div>
      </div>
    </div>

    <!-- Download Modal (Built-in) -->
    <div v-if="showDownloadModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" @click.self="showDownloadModal = false">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div class="flex justify-between items-center p-6 border-b">
          <h3 class="text-lg font-semibold">Download Trial Results</h3>
          <button @click="showDownloadModal = false" class="text-gray-500 hover:text-gray-700 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="p-6">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Format</label>
              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="downloadFormat"
                    type="radio"
                    value="json"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <span class="ml-2 text-sm text-gray-700">JSON (one file per document)</span>
                </label>
                <label class="flex items-center">
                  <input
                    v-model="downloadFormat"
                    type="radio"
                    value="csv"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <span class="ml-2 text-sm text-gray-700">CSV (flattened structure)</span>
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Options</label>
              <label class="flex items-center">
                <input
                  v-model="includeContent"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span class="ml-2 text-sm text-gray-700">Include document content</span>
              </label>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 p-6 border-t bg-gray-50">
          <button
            @click="showDownloadModal = false"
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleDownload"
            :disabled="isDownloading"
            class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors disabled:bg-blue-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg v-if="isDownloading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ isDownloading ? 'Downloading...' : 'Download' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue';
import { useToast } from 'vue-toastification';
import { api } from '@/services/api';
import CreateTrialModal from '@/components/CreateTrialModal.vue';
import TrialResults from '@/components/TrialResults.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import EmptyState from '@/components/EmptyState.vue';
import ConfirmationDialog from '@/components/ConfirmationDialog.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const toast = useToast();

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

// Data
const documents = ref([]);
const schemas = ref([]);
const prompts = ref([]);
const trials = ref([]);
const isLoading = ref(true);
const error = ref(null);
const isModalOpen = ref(false);
const isConfirmDialogOpen = ref(false);
const trialToDelete = ref(null);
const showCompleted = ref(true);

// Improved polling state management
const pollInterval = ref(null);
const isPollingActive = ref(false);
const activeTrialIds = ref(new Set());
const POLL_INTERVAL_MS = 3000;

// Schema modal state
const showSchemaModal = ref(false);
const selectedSchema = ref(null);

// Prompt modal state
const showPromptModal = ref(false);
const selectedPrompt = ref(null);

// Trial results modal state
const showTrialResultsModal = ref(false);
const selectedTrialId = ref(null);

// Download modal state
const showDownloadModal = ref(false);
const trialToDownload = ref(null);
const downloadFormat = ref('json');
const includeContent = ref(true);
const isDownloading = ref(false);

// Computed
const filteredTrials = computed(() => {
  if (showCompleted.value) {
    return trials.value;
  }
  return trials.value.filter(trial => !['completed', 'failed'].includes(trial.status));
});

// Utility methods
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString();
};

const isTrialActive = (trial) => {
  return !['completed', 'failed'].includes(trial.status);
};

const getProgressPercentage = (trial) => {
  if (trial.progress !== null && trial.progress !== undefined) {
    return Math.round(trial.progress * 100);
  }
  // Default progress for active trials without specific progress
  return isTrialActive(trial) ? 25 : 0;
};

const getStatusClass = (status) => {
  const statusMap = {
    'pending': 'bg-yellow-100 text-yellow-800',
    'processing': 'bg-blue-100 text-blue-800',
    'completed': 'bg-green-100 text-green-800',
    'failed': 'bg-red-100 text-red-800'
  };
  return statusMap[status] || 'bg-gray-100 text-gray-800';
};

const getResultSummary = (trial) => {
  if (!trial.results || trial.results.length === 0) {
    return null;
  }
  return trial.results.length === 1
    ? '1 document processed'
    : `${trial.results.length} documents processed`;
};

const getSchemaForTrial = (trial) => {
  return schemas.value.find(schema => schema.id === trial.schema_id);
};

const getPromptForTrial = (trial) => {
  return prompts.value.find(prompt => prompt.id === trial.prompt_id);
};


// Improved polling methods
const updateActiveTrials = () => {
  const newActiveIds = new Set(
    trials.value
      .filter(trial => isTrialActive(trial))
      .map(trial => trial.id)
  );

  activeTrialIds.value = newActiveIds;

  if (newActiveIds.size > 0 && !isPollingActive.value) {
    startPolling();
  } else if (newActiveIds.size === 0 && isPollingActive.value) {
    stopPolling();
  }
};

const startPolling = () => {
  if (isPollingActive.value) return;

  isPollingActive.value = true;
  console.log('Starting polling for trials:', Array.from(activeTrialIds.value));

  const poll = async () => {
    if (!isPollingActive.value || activeTrialIds.value.size === 0) {
      stopPolling();
      return;
    }

    try {
      // Update each active trial individually to avoid race conditions
      const updatePromises = Array.from(activeTrialIds.value).map(trialId =>
        updateTrialStatus(trialId)
      );

      await Promise.allSettled(updatePromises);
      updateActiveTrials(); // Recalculate active trials

    } catch (err) {
      console.error('Polling error:', err);
    }

    // Continue polling if still active
    if (isPollingActive.value && activeTrialIds.value.size > 0) {
      pollInterval.value = setTimeout(poll, POLL_INTERVAL_MS);
    }
  };

  poll();
};

const stopPolling = () => {
  console.log('Stopping polling');
  isPollingActive.value = false;
  if (pollInterval.value) {
    clearTimeout(pollInterval.value);
    pollInterval.value = null;
  }
};

const saveAsDocumentGroup = async (trial) => {
  const groupName = prompt(`Enter a name for this document group:`, `Trial #${trial.id} Documents`);
  if (!groupName) return;

  try {
    const payload = {
      name: groupName,
      description: `Documents used in trial #${trial.id} - ${trial.results.length} documents`,
      document_ids: trial.document_ids,
      // trial_id: trial.id,
      tags: ['from-trial', `trial-${trial.id}`]
    };

    await api.post(`/project/${props.projectId}/document-set`, payload);
    toast.success('Document group saved successfully');
  } catch (error) {
    console.error('Failed to save document group:', error);
    toast.error(error.response?.data?.detail || 'Failed to save document group');
  }
};


const updateTrialStatus = async (trialId) => {
  try {
    const response = await api.get(`/project/${props.projectId}/trial/${trialId}`);
    const updatedTrial = response.data;

    const index = trials.value.findIndex(trial => trial.id === trialId);
    if (index !== -1) {
      trials.value[index] = updatedTrial;
    }

    return updatedTrial;
  } catch (err) {
    console.error(`Failed to update status for trial ${trialId}:`, err);
    // Don't throw, just log - we don't want one failed trial to break polling
  }
};

// Modal methods
const viewTrialResults = (trial) => {
  selectedTrialId.value = trial.id;
  showTrialResultsModal.value = true;
};

const viewTrialSchema = (trial) => {
  console.log('viewTrialSchema called with trial:', trial);
  const schema = getSchemaForTrial(trial);
  console.log('Found schema:', schema);
  selectedSchema.value = schema;
  showSchemaModal.value = true;
  console.log('showSchemaModal set to:', showSchemaModal.value);
};

const viewTrialPrompt = (trial) => {
  const prompt = getPromptForTrial(trial);
  selectedPrompt.value = prompt;
  showPromptModal.value = true;
};

const copyPromptToClipboard = async () => {
  if (!selectedPrompt.value) return;

  try {
    const promptText = `System Prompt:\n${selectedPrompt.value.system_prompt || 'N/A'}\n\nUser Prompt:\n${selectedPrompt.value.user_prompt || 'N/A'}`;
    await navigator.clipboard.writeText(promptText);
    toast.success('Prompt copied to clipboard');
  } catch (err) {
    toast.error('Failed to copy prompt to clipboard');
  }
};


const formatJsonSchema = (schema) => {
  if (!schema) return '';
  return JSON.stringify(schema, null, 2);
};

const copySchemaToClipboard = async () => {
  if (!selectedSchema.value) return;

  try {
    await navigator.clipboard.writeText(formatJsonSchema(selectedSchema.value.schema_definition));
    toast.success('Schema copied to clipboard');
  } catch (err) {
    toast.error('Failed to copy schema to clipboard');
  }
};

const openCreateTrialModal = () => {
  isModalOpen.value = true;
};

const handleCreateTrial = async (trialData) => {
  try {
    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.push(response.data);
    toast.success('Trial created successfully');
    isModalOpen.value = false;
    updateActiveTrials(); // This will start polling if needed
  } catch (err) {
    toast.error(`Failed to create trial: ${err.message || 'Unknown error'}`);
  }
};

const confirmDeleteTrial = (trial) => {
  trialToDelete.value = trial;
  isConfirmDialogOpen.value = true;
};

const deleteTrial = async () => {
  if (!trialToDelete.value) return;

  try {
    await api.delete(`/project/${props.projectId}/trial/${trialToDelete.value.id}`);
    trials.value = trials.value.filter(trial => trial.id !== trialToDelete.value.id);
    toast.success('Trial deleted successfully');
    updateActiveTrials();
  } catch (err) {
    toast.error(`Failed to delete trial: ${err.message || 'Unknown error'}`);
  } finally {
    isConfirmDialogOpen.value = false;
    trialToDelete.value = null;
  }
};

const retryTrial = async (trial) => {
  try {
    const trialData = {
      schema_id: trial.schema_id,
      prompt_id: trial.prompt_id,
      document_ids: trial.document_ids,
      llm_model: trial.llm_model,
      api_key: trial.api_key,
      base_url: trial.base_url
    };

    // Include advanced_options if they exist
    if (trial.advanced_options && Object.keys(trial.advanced_options).length > 0) {
      trialData.advanced_options = trial.advanced_options;
    }

    const response = await api.post(`/project/${props.projectId}/trial`, trialData);
    trials.value.push(response.data);
    toast.success('Trial restarted successfully');
    updateActiveTrials();
  } catch (err) {
    toast.error(`Failed to restart trial: ${err.message || 'Unknown error'}`);
  }
};


// Add the missing openDownloadModal method
const openDownloadModal = (trial) => {
  console.log('openDownloadModal called with trial:', trial);
  trialToDownload.value = trial;
  showDownloadModal.value = true;
};

const handleDownload = async () => {
  if (isDownloading.value || !trialToDownload.value) return;

  isDownloading.value = true;
  try {
    const response = await api.get(
      `/project/${props.projectId}/trial/${trialToDownload.value.id}/download?format=${downloadFormat.value}&include_content=${includeContent.value}`,
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `trial_${trialToDownload.value.id}_results.${downloadFormat.value}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    toast.success('Trial results downloaded successfully');
    showDownloadModal.value = false;
  } catch (err) {
    toast.error(`Failed to download trial results: ${err.message}`);
    console.error(err);
  } finally {
    isDownloading.value = false;
  }
};

// Lifecycle
onMounted(async () => {
  try {
    const [documentsResponse, schemasResponse, promptsResponse, trialsResponse] = await Promise.all([
      api.get(`/project/${props.projectId}/document`),
      api.get(`/project/${props.projectId}/schema`),
      api.get(`/project/${props.projectId}/prompt`),
      api.get(`/project/${props.projectId}/trial`)
    ]);

    documents.value = documentsResponse.data;
    schemas.value = schemasResponse.data;
    prompts.value = promptsResponse.data;
    trials.value = trialsResponse.data;

    updateActiveTrials();
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>
