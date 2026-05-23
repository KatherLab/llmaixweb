<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">File Preprocessing</h2>
        <p class="mt-1 text-sm text-gray-500">Process your files with OCR and text extraction</p>
      </div>
      <div class="flex items-center space-x-3">
        <button
          :disabled="isLoadingTasks"
          class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50"
          title="Refresh tasks"
          @click="fetchPreprocessingTasks"
        >
          <svg
            :class="['h-4 w-4', isLoadingTasks && 'animate-spin']"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div
      v-if="isLoadingTasks && allTasks.length === 0"
      class="flex justify-center items-center py-12"
    >
      <div class="flex items-center space-x-3">
        <svg
          class="animate-spin h-5 w-5 text-blue-600"
          fill="none"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
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
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            fill="currentColor"
          ></path>
        </svg>
        <span class="text-gray-600">Loading preprocessing tasks...</span>
      </div>
    </div>

    <!-- Active Tasks Dashboard -->
    <div
      v-if="activeTasks.length > 0"
      class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6"
    >
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900 flex items-center">
          <span class="relative flex h-3 w-3 mr-2">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"
            ></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
          </span>
          Active Processing Tasks
        </h3>
        <button class="text-sm text-red-600 hover:text-red-800 font-medium" @click="cancelAllTasks">
          Cancel All
        </button>
      </div>
      <div class="space-y-3">
        <TaskCard
          v-for="task in activeTasks"
          :key="task.id"
          :task="task"
          @cancel="showCancelTaskDialog"
          @retry="retryTask"
          @view-details="viewTaskDetails"
        />
      </div>
    </div>

    <!-- Completed Tasks Summary -->
    <div
      v-if="completedTasks.length > 0"
      class="bg-white rounded-2xl shadow-lg border border-gray-200 p-0 mt-6"
    >
      <div
        :aria-expanded="showCompletedTasks.toString()"
        class="flex items-center justify-between px-6 py-4 cursor-pointer select-none hover:bg-gray-50 active:bg-gray-100 rounded-t-2xl transition group focus:outline-none"
        role="button"
        tabindex="0"
        @click="showCompletedTasks = !showCompletedTasks"
        @keyup.enter.space="showCompletedTasks = !showCompletedTasks"
      >
        <div class="flex items-center gap-2">
          <svg
            class="h-6 w-6 text-emerald-500 transition-transform"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
          <h3 class="text-xl font-bold text-gray-900 tracking-tight">Recent Task History</h3>
          <span class="ml-3 px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
            {{ completedTasks.length }} total
          </span>
        </div>
        <div class="flex items-center gap-2 text-sm font-medium text-gray-500">
          <span>{{ showCompletedTasks ? 'Hide Details' : 'Show Details' }}</span>
          <svg
            :class="{ 'rotate-180': showCompletedTasks }"
            class="h-4 w-4 transition-transform duration-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M19 9l-7 7-7-7"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
            />
          </svg>
        </div>
      </div>
      <transition appear mode="out-in" name="fade-expand">
        <div
          v-show="showCompletedTasks"
          key="completed-tasks-list"
          class="px-4 pb-2 pt-1 space-y-1 overflow-hidden"
        >
          <div
            v-for="task in displayedCompletedTasks"
            :key="task.id"
            class="flex items-center justify-between bg-white/90 border border-gray-100 rounded-lg px-3 py-2 my-1 shadow-xs hover:shadow-md hover:bg-blue-50 transition group cursor-pointer"
            tabindex="0"
            @click="viewTaskDetails(task)"
            @keyup.enter.space="viewTaskDetails(task)"
          >
            <div class="flex items-center gap-3 min-w-0">
              <span
                :class="{
                  'bg-green-50':
                    task.status === 'completed' &&
                    !task.file_tasks?.some(
                      (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                    ),
                  'bg-amber-50':
                    task.status === 'completed' &&
                    task.file_tasks?.some(
                      (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                    ),
                  'bg-red-50': task.status === 'failed',
                  'bg-yellow-50': task.status === 'cancelled' || task.status === 'errored',
                }"
                class="w-6 h-6 flex items-center justify-center rounded-full"
              >
                <svg
                  v-if="
                    task.status === 'completed' &&
                    !task.file_tasks?.some(
                      (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                    )
                  "
                  class="w-4 h-4 text-emerald-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M5 13l4 4L19 7"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
                <svg
                  v-else-if="
                    task.status === 'completed' &&
                    task.file_tasks?.some(
                      (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                    )
                  "
                  class="w-4 h-4 text-amber-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 9v2m0 4h.01m-5.355-7.695a9 9 0 1110.71 0 9 9 0 01-10.71 0z"
                  />
                </svg>
                <svg
                  v-else-if="task.status === 'failed'"
                  class="w-4 h-4 text-red-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M6 18L18 6M6 6l12 12"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
                <svg
                  v-else
                  class="w-4 h-4 text-yellow-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <circle
                    cx="12"
                    cy="12"
                    fill="none"
                    r="10"
                    stroke="currentColor"
                    stroke-width="2"
                  />
                  <path
                    d="M12 8v4m0 4h.01"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
              </span>
              <div class="flex flex-col text-xs min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900 truncate">Task #{{ task.id }}</span>
                  <span class="text-gray-500 truncate">— {{ engineLabel(task) }}</span>
                  <span
                    v-if="task.status === 'failed'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-red-100 text-red-600 text-2xs font-semibold uppercase tracking-wide"
                    >FAILED</span
                  >
                  <span
                    v-else-if="task.status === 'cancelled'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 text-2xs font-semibold uppercase tracking-wide"
                    >CANCELLED</span
                  >
                  <span
                    v-else-if="task.status === 'errored'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 text-2xs font-semibold uppercase tracking-wide"
                    >ERROR</span
                  >
                  <span
                    v-else-if="task.status === 'completed'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-green-100 text-green-700 text-2xs font-semibold uppercase tracking-wide"
                    >COMPLETED</span
                  >
                </div>
                <div class="flex items-center gap-3 mt-0.5">
                  <span v-if="task.failed_files > 0" class="text-red-500"
                    >✗ {{ task.failed_files }} failed</span
                  >
                  <span
                    v-if="task.processed_files - task.failed_files - (task.skipped_files || 0) > 0"
                    class="text-green-500"
                    >✓
                    {{ task.processed_files - task.failed_files - (task.skipped_files || 0) }}
                    succeeded</span
                  >
                  <span v-if="task.skipped_files > 0" class="text-yellow-600"
                    >⚠ {{ task.skipped_files }} skipped</span
                  >
                  <span
                    v-if="
                      task.file_tasks?.some(
                        (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                      )
                    "
                    class="text-amber-600"
                    >⚠
                    {{
                      task.file_tasks.filter(
                        (ft) => ft.warnings?.messages || ft.warnings?.skipped_rows,
                      ).length
                    }}
                    with warnings</span
                  >
                  <span
                    v-if="task.status === 'failed' && task.message"
                    class="text-red-400 truncate max-w-[200px]"
                    >{{ task.message }}</span
                  >
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span :title="task.completed_at || task.updated_at" class="text-xs text-gray-400">{{
                formatRelativeTime(task.completed_at || task.updated_at)
              }}</span>
            </div>
          </div>
          <div v-if="completedTasks.length > 5" class="text-center pt-2">
            <button
              class="text-sm text-emerald-700 hover:text-emerald-900 font-medium inline-flex items-center gap-1"
              @click.stop="showAllCompleted = !showAllCompleted"
            >
              <span v-if="!showAllCompleted">Show {{ completedTasks.length - 5 }} more</span>
              <span v-else>Show less</span>
              <svg
                :class="[
                  'h-4 w-4 transition-transform duration-200',
                  showAllCompleted ? 'rotate-180' : '',
                ]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M19 9l-7 7-7-7"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
            </button>
          </div>
        </div>
      </transition>
    </div>

    <!-- New Preprocessing Task -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-6">Create New Preprocessing Task</h3>

        <!-- Engine Selection -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-3"
            >OCR / Text Extraction Engine</label
          >
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all min-h-[100px]',
                selectedEngine === 'ocrmypdf'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300',
              ]"
              @click="selectedEngine = 'ocrmypdf'"
            >
              <svg
                :class="selectedEngine === 'ocrmypdf' ? 'text-blue-600' : 'text-gray-400'"
                class="h-8 w-8 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
              <span class="font-medium text-sm">{{ getEngineLabel('ocrmypdf') }}</span>
              <span class="text-xs text-gray-500 mt-1 text-center"
                >{{ getEngineSubtitle('ocrmypdf') }}<br />No configuration needed</span
              >
            </button>

            <button
              :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all min-h-[100px]',
                selectedEngine === 'mistral_ocr'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300',
                !mistralOcrEnabled && 'opacity-50 cursor-not-allowed',
              ]"
              :disabled="!mistralOcrEnabled"
              @click="selectedEngine = 'mistral_ocr'"
            >
              <svg
                :class="selectedEngine === 'mistral_ocr' ? 'text-blue-600' : 'text-gray-400'"
                class="h-8 w-8 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
              <span class="font-medium text-sm">{{ getEngineLabel('mistral_ocr') }}</span>
              <span class="text-xs text-gray-500 mt-1 text-center">{{
                mistralOcrEnabled ? getEngineSubtitle('mistral_ocr') : 'Disabled by server'
              }}</span>
            </button>

            <button
              :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all min-h-[100px]',
                selectedEngine === 'llm_vision'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300',
                !visionOcrEnabled && 'opacity-50 cursor-not-allowed',
              ]"
              :disabled="!visionOcrEnabled"
              @click="selectedEngine = 'llm_vision'"
            >
              <svg
                :class="selectedEngine === 'llm_vision' ? 'text-blue-600' : 'text-gray-400'"
                class="h-8 w-8 mb-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                />
              </svg>
              <span class="font-medium text-sm">{{ getEngineLabel('llm_vision') }}</span>
              <span class="text-xs text-gray-500 mt-1 text-center">{{
                visionOcrEnabled ? getEngineSubtitle('llm_vision') : 'Disabled by server'
              }}</span>
            </button>
          </div>
        </div>

        <!-- Engine-specific settings -->
        <div
          class="bg-gradient-to-br from-blue-50/60 to-white border border-blue-200 rounded-2xl px-8 py-6 space-y-4 mt-4 mb-4"
        >
          <!-- Force OCR (global) -->
          <label class="flex items-center gap-2">
            <input v-model="forceOcr" class="accent-blue-600" type="checkbox" />
            Force OCR for PDFs (ignore embedded text, run OCR on all pages)
          </label>

          <!-- Mistral settings -->
          <div
            v-if="selectedEngine === 'mistral_ocr'"
            class="space-y-3 border-t border-blue-100 pt-4"
          >
            <!-- Always visible: prompt area (empty for Mistral) -->
            <p class="text-sm text-gray-600">
              Base URL:
              <code class="text-xs bg-blue-50 px-1.5 py-0.5 rounded">{{
                serverDefaults.mistral_api_base
              }}</code>
            </p>

            <!-- Advanced settings -->
            <div>
              <button
                class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                type="button"
                @click="showMistralAdvanced = !showMistralAdvanced"
              >
                <svg
                  :class="showMistralAdvanced ? 'rotate-90' : ''"
                  class="h-3 w-3 transition-transform"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M9 5l7 7-7 7"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
                Advanced
              </button>
            </div>
            <div v-if="showMistralAdvanced" class="space-y-3 pl-3 border-l-2 border-blue-100">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">API Key</label>
                <input
                  v-model="mistralApiKey"
                  type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter API key (leave empty to use server-configured key)"
                  autocomplete="off"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Model (optional)</label>
                <input
                  v-model="mistralModel"
                  type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  placeholder="mistral-ocr-latest"
                />
              </div>
            </div>
          </div>

          <!-- Vision LLM settings -->
          <div
            v-if="selectedEngine === 'llm_vision'"
            class="space-y-3 border-t border-blue-100 pt-4"
          >
            <!-- Always visible -->
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Prompt (optional)</label>
              <textarea
                v-model="visionPrompt"
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                :placeholder="serverDefaults.vision_ocr_prompt"
                rows="2"
              />
            </div>

            <!-- Advanced settings -->
            <div>
              <button
                class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
                type="button"
                @click="showVisionAdvanced = !showVisionAdvanced"
              >
                <svg
                  :class="showVisionAdvanced ? 'rotate-90' : ''"
                  class="h-3 w-3 transition-transform"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M9 5l7 7-7 7"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                  />
                </svg>
                Advanced
              </button>
            </div>
            <div v-if="showVisionAdvanced" class="space-y-3 pl-3 border-l-2 border-blue-100">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">API Key</label>
                <input
                  v-model="visionApiKey"
                  type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter API key (leave empty to use server-configured key)"
                  autocomplete="off"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  v-model="visionBaseUrl"
                  type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  :placeholder="serverDefaults.vision_ocr_api_base || 'https://api.openai.com/v1'"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Model</label>
                <input
                  v-model="visionModel"
                  type="text"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  :placeholder="serverDefaults.vision_ocr_model"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1"
                  >Max Image Dimension (pixels)</label
                >
                <input
                  v-model.number="visionMaxImageDim"
                  type="number"
                  min="400"
                  max="4096"
                  step="100"
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                />
                <p class="mt-1 text-xs text-gray-500">
                  Images will be scaled to this max dimension before sending to the vision model.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- File Selection -->
        <div class="mb-6">
          <div class="flex justify-between items-center mb-3">
            <label class="block text-sm font-medium text-gray-700">Select Files to Process</label>
            <div class="text-sm text-gray-500">
              {{ selectedFiles.length }} of {{ availableFiles.length }} selected
            </div>
          </div>
          <FileSelector
            v-model:selected="selectedFiles"
            :files="availableFiles"
            :show-preview="true"
            @select-all="selectAllFiles"
            @clear-selection="selectedFiles = []"
            @preview="previewFile"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-end space-x-3">
          <button
            class="px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            @click="resetForm"
          >
            Reset
          </button>
          <button
            :disabled="!canStartProcessing"
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="startPreprocessing"
          >
            <svg
              v-if="isSubmitting"
              class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
              />
              <path
                class="opacity-75"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                fill="currentColor"
              />
            </svg>
            Start Processing
          </button>
        </div>
      </div>
    </div>

    <!-- Task Details Modal -->
    <TaskDetailsModal
      v-if="selectedTask"
      :task="selectedTask"
      @close="selectedTask = null"
      @retry-failed="retryFailedFiles"
    />

    <!-- File Preview Modal -->
    <FilePreviewModal
      v-if="previewFileData"
      :file="previewFileData"
      :project-id="props.projectId"
      @close="previewFileData = null"
    />

    <ConfirmationDialog
      v-if="showCancelDialog"
      :open="showCancelDialog"
      title="Cancel Preprocessing Task"
      :message="
        cancelDeleteMode
          ? 'Are you sure you want to cancel and DELETE already processed files? This cannot be undone.'
          : 'Do you want to keep already processed files when cancelling this task?'
      "
      :confirm-text="cancelDeleteMode ? 'Delete Processed and Cancel' : 'Keep Processed and Cancel'"
      :cancel-text="cancelDeleteMode ? 'Back' : 'Delete Processed'"
      :confirm-variant="cancelDeleteMode ? 'danger' : 'primary'"
      @confirm="() => doCancelTask(cancelTaskPending, !cancelDeleteMode)"
      @cancel="handleCancelDialogSecondary"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'vue-toastification'
import { getEngineLabel, getEngineSubtitle, setEngineLabels } from '@/utils/ocrLabels'
import TaskCard from './preprocessing/TaskCard.vue'
import FileSelector from './preprocessing/FileSelector.vue'
import TaskDetailsModal from './preprocessing/TaskDetailsModal.vue'
import ConfirmationDialog from '@/components/ConfirmationDialog.vue'
import FilePreviewModal from '@/components/files/FilePreviewModal.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  files: { type: Array, default: () => [] },
})

const toast = useToast()
const authStore = useAuthStore()

// State
const allTasks = ref([])
const isLoadingTasks = ref(false)
const availableFiles = ref([])
const selectedFiles = ref([])
const mistralOcrEnabled = ref(true)
const visionOcrEnabled = ref(true)
const selectedTask = ref(null)
const showCompletedTasks = ref(false)
const showCancelDialog = ref(false)
const cancelTaskPending = ref(null)
const cancelDeleteMode = ref(false)
const isSubmitting = ref(false)
const showAllCompleted = ref(false)
const isAdmin = computed(() => authStore.isAdmin)
const previewFileData = ref(null)
let pollInterval = null

// Server-provided OCR defaults (populated from /auth/settings)
const serverDefaults = ref({
  vision_ocr_model: 'gpt-4o',
  vision_ocr_api_base: '',
  vision_ocr_prompt:
    'Extract all text from this image and return it as clean markdown. Preserve the original structure, headings, lists, and formatting as much as possible.',
  mistral_api_base: 'https://api.mistral.ai',
})

// Form state
const selectedEngine = ref('ocrmypdf')
const forceOcr = ref(false)
const mistralApiKey = ref('')
const mistralModel = ref('mistral-ocr-latest')
const showMistralAdvanced = ref(false)
const visionApiKey = ref('')
const visionBaseUrl = ref('')
const visionModel = ref('gpt-4o')
const visionPrompt = ref(
  'Extract all text from this image and return it as clean markdown. Preserve the original structure, headings, lists, and formatting as much as possible.',
)
const visionMaxImageDim = ref(2048)
const showVisionAdvanced = ref(false)

const engineLabel = (task) => {
  const engine = task.configuration?.additional_settings?.ocr_engine
  return getEngineLabel(engine)
}

// Computed
const activeTasks = computed(() =>
  allTasks.value.filter((t) => ['pending', 'processing', 'in_progress'].includes(t.status)),
)
const completedTasks = computed(() =>
  allTasks.value
    .filter((t) => ['completed', 'failed', 'cancelled', 'errored'].includes(t.status))
    .sort(
      (a, b) => new Date(b.completed_at || b.updated_at) - new Date(a.completed_at || a.updated_at),
    ),
)
const displayedCompletedTasks = computed(() => {
  const f = completedTasks.value.filter(Boolean)
  return showAllCompleted.value ? f : f.slice(0, 5)
})
const canStartProcessing = computed(() => selectedFiles.value.length > 0 && !isSubmitting.value)

// API
const fetchPreprocessingTasks = async () => {
  if (isLoadingTasks.value) return
  isLoadingTasks.value = true
  try {
    const r = await api.get(`/project/${props.projectId}/preprocess?limit=50`)
    allTasks.value = r.data
  } catch (e) {
    console.error(e)
  } finally {
    isLoadingTasks.value = false
  }
}

const fetchAvailableFiles = async () => {
  try {
    const r = await api.get(`/project/${props.projectId}/file?file_creator=user`)
    availableFiles.value = r.data
  } catch (e) {
    console.error(e)
  }
}

const fetchOcrSettings = async () => {
  try {
    const r = await api.get('/auth/settings')
    if (r.data.mistral_ocr_enabled !== undefined)
      mistralOcrEnabled.value = r.data.mistral_ocr_enabled
    if (r.data.vision_ocr_enabled !== undefined) visionOcrEnabled.value = r.data.vision_ocr_enabled
    // Store server-provided defaults for form fields (API key is NOT exposed)
    if (r.data.vision_ocr_model) {
      serverDefaults.value.vision_ocr_model = r.data.vision_ocr_model
      visionModel.value = r.data.vision_ocr_model
    }
    if (r.data.vision_ocr_api_base) {
      serverDefaults.value.vision_ocr_api_base = r.data.vision_ocr_api_base
    }
    if (r.data.vision_ocr_prompt) {
      serverDefaults.value.vision_ocr_prompt = r.data.vision_ocr_prompt
      visionPrompt.value = r.data.vision_ocr_prompt
    }
    if (r.data.mistral_api_base) serverDefaults.value.mistral_api_base = r.data.mistral_api_base
    // Populate dynamic OCR display names
    setEngineLabels(r.data)
  } catch (e) {
    /* defaults enabled */
  }
}

const updateTaskStatus = async (taskId) => {
  try {
    const r = await api.get(`/project/${props.projectId}/preprocess/${taskId}`)
    const idx = allTasks.value.findIndex((t) => t.id === taskId)
    if (idx !== -1) {
      allTasks.value[idx] = r.data
      if (selectedTask.value?.id === taskId) selectedTask.value = r.data
    } else {
      allTasks.value.unshift(r.data)
    }
  } catch (e) {
    console.error(e)
  }
}

const setupPolling = () => {
  if (pollInterval) clearInterval(pollInterval)
  const poll = () => {
    const active = allTasks.value.filter((t) =>
      ['pending', 'processing', 'in_progress'].includes(t.status),
    )
    if (!active.length) {
      clearInterval(pollInterval)
      pollInterval = null
      return
    }
    active.forEach((t) => updateTaskStatus(t.id))
  }
  poll()
  pollInterval = setInterval(poll, 2000)
}

const formatRelativeTime = (ds) => {
  if (!ds) return ''
  const diff = new Date() - new Date(ds)
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(ds).toLocaleDateString()
}

const buildAdditionalSettings = () => {
  const settings = { ocr_engine: selectedEngine.value, force_ocr: forceOcr.value }
  if (selectedEngine.value === 'mistral_ocr') {
    if (mistralApiKey.value) settings.mistral_api_key = mistralApiKey.value
    settings.mistral_model = mistralModel.value
  }
  if (selectedEngine.value === 'llm_vision') {
    if (visionApiKey.value) settings.vision_api_key = visionApiKey.value
    if (visionBaseUrl.value) settings.vision_base_url = visionBaseUrl.value
    settings.vision_model = visionModel.value
    settings.vision_prompt = visionPrompt.value
    settings.vision_max_image_dim = visionMaxImageDim.value
  }
  return settings
}

const startPreprocessing = async () => {
  if (!canStartProcessing.value) return
  isSubmitting.value = true
  try {
    const inlineConfig = {
      name:
        selectedEngine.value === 'ocrmypdf' ? 'Quick Process' : `Custom ${selectedEngine.value}`,
      additional_settings: buildAdditionalSettings(),
    }
    const taskData = { inline_config: inlineConfig, file_ids: selectedFiles.value }
    const r = await api.post(`/project/${props.projectId}/preprocess`, taskData)
    allTasks.value.unshift(r.data)
    resetForm()
    toast.success('Preprocessing task started')
    setupPolling()
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to start preprocessing')
  } finally {
    isSubmitting.value = false
  }
}

// Dialogs
const showCancelTaskDialog = (task) => {
  cancelTaskPending.value = task
  cancelDeleteMode.value = false
  showCancelDialog.value = true
}
function handleCancelDialogSecondary() {
  if (cancelDeleteMode.value) {
    showCancelDialog.value = false
    cancelTaskPending.value = null
    cancelDeleteMode.value = false
  } else cancelDeleteMode.value = true
}
const doCancelTask = async (task, keepProcessed) => {
  showCancelDialog.value = false
  cancelDeleteMode.value = false
  if (!task) return
  try {
    await api.post(
      `/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=${!!keepProcessed}`,
    )
    toast.success('Task cancelled')
    fetchPreprocessingTasks()
  } catch (e) {
    toast.error('Failed to cancel task')
  } finally {
    cancelTaskPending.value = null
  }
}
const cancelTask = async (task) => {
  if (!confirm('Keep already processed files?')) return
  try {
    await api.post(`/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=true`)
    toast.success('Task cancelled')
    fetchPreprocessingTasks()
  } catch (e) {
    toast.error('Failed to cancel task')
  }
}
const cancelAllTasks = async () => {
  if (!confirm('Cancel all active tasks?')) return
  for (const t of activeTasks.value) await cancelTask(t)
}
const retryTask = async (task) => {
  try {
    const r = await api.get(`/project/${props.projectId}/preprocess/${task.id}/retry-failed`)
    allTasks.value.unshift(r.data)
    toast.success('Retry task created')
    setupPolling()
  } catch (e) {
    toast.error('Failed to retry')
  }
}
const viewTaskDetails = async (task) => {
  try {
    const r = await api.get(`/project/${props.projectId}/preprocess/${task.id}`)
    selectedTask.value = r.data
  } catch (e) {
    selectedTask.value = task
  }
}
const retryFailedFiles = async (taskId) => {
  try {
    const r = await api.get(`/project/${props.projectId}/preprocess/${taskId}/retry-failed`)
    allTasks.value.unshift(r.data)
    toast.success('Retry task created')
    selectedTask.value = null
    setupPolling()
  } catch (e) {
    toast.error('Failed to create retry task')
  }
}
const selectAllFiles = () => {
  selectedFiles.value = availableFiles.value.map((f) => f.id)
}
const resetForm = () => {
  selectedFiles.value = []
  selectedEngine.value = 'ocrmypdf'
  forceOcr.value = false
  mistralApiKey.value = ''
  mistralModel.value = 'mistral-ocr-latest'
  showMistralAdvanced.value = false
  visionApiKey.value = ''
  visionBaseUrl.value = ''
  visionModel.value = serverDefaults.value.vision_ocr_model
  visionPrompt.value = serverDefaults.value.vision_ocr_prompt
  visionMaxImageDim.value = 2048
  showVisionAdvanced.value = false
}

const previewFile = (file) => {
  previewFileData.value = file
}

// Lifecycle
onMounted(() => {
  fetchPreprocessingTasks()
  fetchAvailableFiles()
  fetchOcrSettings()
  if (activeTasks.value.length > 0) setupPolling()
})
onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

watch(
  () => props.files,
  (f) => {
    availableFiles.value = f
  },
  { immediate: true },
)
watch(
  () => activeTasks.value.length,
  (l) => {
    if (l > 0 && !pollInterval) setupPolling()
  },
)
watch(
  () => completedTasks.value.length,
  () => {
    showAllCompleted.value = false
  },
)
</script>

<style>
.fade-expand-enter-active,
.fade-expand-leave-active {
  transition:
    all 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.3s;
  overflow: hidden;
}
.fade-expand-enter-from,
.fade-expand-leave-to {
  max-height: 0;
  opacity: 0;
  padding-bottom: 0 !important;
}
.fade-expand-enter-to,
.fade-expand-leave-from {
  max-height: 900px;
  opacity: 1;
}
</style>
