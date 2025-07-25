<template>
  <div class="p-6 space-y-6">
    <!-- Header with Quick Actions -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-gray-900">File Preprocessing</h2>
        <p class="mt-1 text-sm text-gray-500">Process your files with OCR and text extraction</p>
      </div>
      <div class="flex items-center space-x-3">
        <button
            class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            @click="showConfigManager = true"
        >
          <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"
               xmlns="http://www.w3.org/2000/svg">
            <path
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                stroke-linecap="round" stroke-linejoin="round"
                stroke-width="2"/>
            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
          </svg>
          Manage Configurations
        </button>
        <button
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            @click="startQuickPreprocess"
        >
          <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"
               xmlns="http://www.w3.org/2000/svg">
            <path d="M13 10V3L4 14h7v7l9-11h-7z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
          </svg>
          Quick Process All
        </button>
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
                stroke-linecap="round" stroke-linejoin="round"
                stroke-width="2"/>
          </svg>
        </button>

      </div>
    </div>

    <div v-if="isLoadingTasks && allTasks.length === 0" class="flex justify-center items-center py-12">
      <div class="flex items-center space-x-3">
        <svg class="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24"
             xmlns="http://www.w3.org/2000/svg">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                fill="currentColor"></path>
        </svg>
        <span class="text-gray-600">Loading preprocessing tasks...</span>
      </div>
    </div>

    <!-- Active Tasks Dashboard -->
    <div v-if="activeTasks.length > 0" class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-gray-900 flex items-center">
          <span class="relative flex h-3 w-3 mr-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
          </span>
          Active Processing Tasks
        </h3>
        <button
            class="text-sm text-red-600 hover:text-red-800 font-medium"
            @click="cancelAllTasks"
        >
          Cancel All
        </button>
      </div>
      <div class="space-y-3">
        <TaskCard
            v-for="task in activeTasks"
            :key="task.id"
            :task="task"
            @cancel="cancelTask"
            @retry="retryTask"
            @view-details="viewTaskDetails"
        />
      </div>
    </div>

    <!-- Completed Tasks Summary -->
    <div v-if="completedTasks.length > 0" class="bg-white rounded-2xl shadow-lg border border-gray-200 p-0 mt-6">
      <!-- Clickable Header -->
      <div
        class="flex items-center justify-between px-6 py-4 cursor-pointer select-none hover:bg-gray-50 active:bg-gray-100 rounded-t-2xl transition group focus:outline-none"
        @click="showCompletedTasks = !showCompletedTasks"
        tabindex="0"
        @keyup.enter.space="showCompletedTasks = !showCompletedTasks"
        :aria-expanded="showCompletedTasks.toString()"
        role="button"
      >
        <div class="flex items-center gap-2">
          <svg class="h-6 w-6 text-emerald-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
          </svg>
          <h3 class="text-xl font-bold text-gray-900 tracking-tight">
            Recent Task History
          </h3>
          <span class="ml-3 px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
            {{ completedTasks.length }} total
          </span>
        </div>
        <div class="flex items-center gap-2 text-sm font-medium text-gray-500">
          <span>{{ showCompletedTasks ? 'Hide Details' : 'Show Details' }}</span>
          <svg
            class="h-4 w-4 transition-transform duration-300"
            :class="{ 'rotate-180': showCompletedTasks }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
          </svg>
        </div>
      </div>

      <!-- Animated Expand/Collapse -->
      <transition
        name="fade-expand"
        mode="out-in"
        appear
      >
        <div
          v-show="showCompletedTasks"
          class="px-4 pb-2 pt-1 space-y-1 overflow-hidden"
          key="completed-tasks-list"
        >
          <!-- Tasks List -->
          <div
            v-for="task in displayedCompletedTasks"
            :key="task.id"
            class="flex items-center justify-between bg-white/90 border border-gray-100 rounded-lg px-3 py-2 my-1 shadow-xs hover:shadow-md hover:bg-blue-50 transition group cursor-pointer"
            @click="viewTaskDetails(task)"
            tabindex="0"
            @keyup.enter.space="viewTaskDetails(task)"
          >
            <!-- Left: Status Icon, Task Info -->
            <div class="flex items-center gap-3 min-w-0">
              <span
                class="w-6 h-6 flex items-center justify-center rounded-full"
                :class="{
                  'bg-green-50': task.status === 'completed',
                  'bg-red-50': task.status === 'failed',
                  'bg-yellow-50': task.status === 'cancelled' || task.status === 'errored'
                }"
              >
                <svg v-if="task.status === 'completed'" class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="task.status === 'failed'" class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else class="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke-width="2" stroke="currentColor" fill="none"/>
                  <path d="M12 8v4m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
              </span>
              <div class="flex flex-col text-xs min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900 truncate">Task #{{ task.id }}</span>
                  <span v-if="task.configuration?.name" class="text-gray-500 truncate">— {{ task.configuration.name }}</span>
                  <span
                    v-if="task.status === 'failed'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-red-100 text-red-600 text-2xs font-semibold uppercase tracking-wide"
                  >FAILED</span>
                  <span
                    v-else-if="task.status === 'cancelled'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 text-2xs font-semibold uppercase tracking-wide"
                  >CANCELLED</span>
                  <span
                    v-else-if="task.status === 'errored'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 text-2xs font-semibold uppercase tracking-wide"
                  >ERROR</span>
                  <span
                    v-else-if="task.status === 'completed'"
                    class="ml-2 px-1.5 py-0.5 rounded bg-green-100 text-green-700 text-2xs font-semibold uppercase tracking-wide"
                  >COMPLETED</span>
                </div>
                <div class="flex items-center gap-3 mt-0.5">
                  <span v-if="task.failed_files > 0" class="text-red-500">
                    ✗ {{ task.failed_files }} failed
                  </span>
                  <span v-if="task.processed_files - task.failed_files - (task.skipped_files || 0) > 0" class="text-green-500">
                    ✓ {{ task.processed_files - task.failed_files - (task.skipped_files || 0) }} succeeded
                  </span>
                  <span v-if="task.skipped_files > 0" class="text-yellow-600">
                    ⚠ {{ task.skipped_files }} skipped
                  </span>
                  <span v-if="task.status === 'failed' && task.message" class="text-red-400 truncate max-w-[200px]">
                    {{ task.message }}
                  </span>
                </div>
              </div>
            </div>
            <!-- Right: Time -->
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-xs text-gray-400" :title="task.completed_at || task.updated_at">
                {{ formatRelativeTime(task.completed_at || task.updated_at) }}
              </span>
            </div>
          </div>
          <!-- Show more/less button -->
          <div v-if="completedTasks.length > 5" class="text-center pt-2">
            <button
              class="text-sm text-emerald-700 hover:text-emerald-900 font-medium inline-flex items-center gap-1"
              @click.stop="showAllCompleted = !showAllCompleted"
            >
              <span v-if="!showAllCompleted">
                Show {{ completedTasks.length - 5 }} more
              </span>
              <span v-else>
                Show less
              </span>
              <svg
                :class="['h-4 w-4 transition-transform duration-200', showAllCompleted ? 'rotate-180' : '']"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
            </button>
          </div>
        </div>
      </transition>
    </div>



    <!-- Create New Task -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-6">Create New Preprocessing Task</h3>
        <!-- Configuration Selection -->
        <!-- ... keep your config selection as in your original file ... -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-3">
            Configuration
          </label>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <!-- ... all your configuration buttons ... -->
            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedConfig === 'quick'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectedConfig = 'quick'"
            >
              <svg :class="selectedConfig === 'quick' ? 'text-blue-600' : 'text-gray-400'" class="h-8 w-8 mb-2"
                   fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Quick Process</span>
              <span class="text-xs text-gray-500 mt-1">Smart defaults</span>
            </button>
            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedConfig === 'saved'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectedConfig = 'saved'"
            >
              <svg :class="selectedConfig === 'saved' ? 'text-blue-600' : 'text-gray-400'" class="h-8 w-8 mb-2"
                   fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                      stroke-linecap="round" stroke-linejoin="round"
                      stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Saved Config</span>
              <span class="text-xs text-gray-500 mt-1">Reuse settings</span>
            </button>
            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedConfig === 'custom'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectedConfig = 'custom'"
            >
              <svg :class="selectedConfig === 'custom' ? 'text-blue-600' : 'text-gray-400'" class="h-8 w-8 mb-2"
                   fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                    stroke-linecap="round" stroke-linejoin="round"
                    stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Custom</span>
              <span class="text-xs text-gray-500 mt-1">Fine-tune settings</span>
            </button>
          </div>
        </div>
        <div v-if="selectedConfig === 'saved'" class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Select Configuration
          </label>
          <select
              v-model="selectedSavedConfig"
              class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
          >
            <option value="">Choose a configuration...</option>
            <option
                v-for="config in savedConfigs"
                :key="config.id"
                :value="config.id"
            >
              {{ config.name }} - {{ config.file_type }}
            </option>
          </select>
        </div>
        <div v-if="selectedConfig === 'custom'" class="space-y-6 mb-6">
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                   xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    stroke-linecap="round" stroke-linejoin="round"
                    stroke-width="2"/>
              </svg>
              OCR Settings
            </h4>
            <div class="space-y-4">
              <label class="flex items-center">
                <input
                    v-model="preprocessingConfig.use_ocr"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Enable OCR</span>
              </label>
              <label class="flex items-center">
                <input
                    v-model="preprocessingConfig.force_ocr"
                    :disabled="!preprocessingConfig.use_ocr"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Force OCR (ignore existing text)</span>
              </label>
              <div v-if="preprocessingConfig.use_ocr" class="relative">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  OCR Languages
                </label>
                <Multiselect
                    v-model="preprocessingConfig.ocr_languages"
                    :can-clear="true"
                    :can-deselect="true"
                    :clear-on-select="false"
                    :close-on-select="false"
                    :create-option="false"
                    :hide-selected="true"
                    :object="true"
                    :options="ocrLanguagesForSelect"
                    :preselect-first="false"
                    :preserve-search="true"
                    :searchable="true"
                    class="multiselect-custom"
                    label="label"
                    mode="tags"
                    placeholder="Select languages"
                    track-by="value"
                    valueProp="value"
                >
                  <template #tag="{ option, handleTagRemove, disabled }">
                    <div class="multiselect-tag">
                      {{ option.label }}
                      <span
                          v-if="!disabled"
                          class="multiselect-tag-remove"
                          @click.stop="handleTagRemove(option, $event)"
                      >
                        <span class="multiselect-tag-remove-icon"></span>
                      </span>
                    </div>
                  </template>
                </Multiselect>

              </div>
            </div>
          </div>
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                   xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    stroke-linecap="round" stroke-linejoin="round"
                    stroke-width="2"/>
              </svg>
              PDF Processing
            </h4>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                PDF Backend
              </label>
              <select
                  v-model="preprocessingConfig.pdf_backend"
                  class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
              >
                <option value="pymupdf4llm">PyMuPDF4LLM (Recommended)</option>
                <option value="markitdown">MarkItDown</option>
              </select>
            </div>
          </div>
          <div class="flex items-center">
            <input
                v-model="saveAsConfig"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                type="checkbox"
            />
            <label class="ml-2 text-sm text-gray-700">
              Save as reusable configuration
            </label>
            <input
                v-if="saveAsConfig"
                v-model="configName"
                class="ml-3 flex-1 px-3 py-1 text-sm border-gray-300 rounded-md"
                placeholder="Configuration name"
                type="text"
            />
          </div>
        </div>

        <!-- Add this section after the OCR settings in PreprocessingManagement.vue -->

        <!-- API Settings (Collapsible) -->
        <div v-if="selectedConfig === 'custom'" class="bg-gray-50 rounded-lg p-4">
          <button
              class="w-full flex items-center justify-between text-left"
              type="button"
              @click="showApiSettings = !showApiSettings"
          >
            <h4 class="font-medium text-gray-900 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                   xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
                    stroke-linecap="round" stroke-linejoin="round"
                    stroke-width="2"/>
              </svg>
              API Settings (Optional)
            </h4>
            <svg
                :class="['h-5 w-5 transition-transform', showApiSettings ? 'rotate-180' : '']"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
            >
              <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
            </svg>
          </button>

          <Transition
              enter-active-class="transition-all duration-200 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-96 opacity-100"
              leave-active-class="transition-all duration-200 ease-in"
              leave-from-class="max-h-96 opacity-100"
              leave-to-class="max-h-0 opacity-0"
          >
            <div v-if="showApiSettings" class="mt-4 space-y-4 overflow-hidden">
              <p class="text-sm text-gray-600">
                Provide custom API credentials for LLM-based preprocessing. Leave empty to use default settings.
              </p>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  API Base URL
                </label>
                <input
                    v-model="apiCredentials.base_url"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="https://api.openai.com/v1"
                    type="text"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <input
                    v-model="apiCredentials.api_key"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="sk-..."
                    type="password"
                />
              </div>

              <div class="flex items-center text-sm text-gray-500">
                <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                     xmlns="http://www.w3.org/2000/svg">
                  <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"/>
                </svg>
                API credentials are not stored and must be provided for each preprocessing task.
              </div>
            </div>
          </Transition>
        </div>

        <!-- File Selection -->
        <div class="mb-6">
          <div class="flex justify-between items-center mb-3">
            <label class="block text-sm font-medium text-gray-700">
              Select Files to Process
            </label>
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
            <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                 fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    fill="currentColor"></path>
            </svg>
            Start Processing
          </button>
        </div>
      </div>
    </div>

    <!-- Configuration Manager Modal -->
    <ConfigurationManager
        v-if="showConfigManager"
        :project-id="projectId"
        @close="showConfigManager = false"
        @config-selected="applyConfiguration"
    />

    <!-- Task Details Modal -->
    <TaskDetailsModal
        v-if="selectedTask"
        :task="selectedTask"
        @close="selectedTask = null"
        @retry-failed="retryFailedFiles"
    />
  </div>
</template>

<script setup>
import {computed, onMounted, onUnmounted, ref, watch} from 'vue';
import {api} from '@/services/api';
import {useToast} from 'vue-toastification';
import Multiselect from '@vueform/multiselect';

import TaskCard from './preprocessing/TaskCard.vue';
import FileSelector from './preprocessing/FileSelector.vue';
import ConfigurationManager from './preprocessing/ConfigurationManager.vue';
import TaskDetailsModal from './preprocessing/TaskDetailsModal.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  files: {
    type: Array,
    default: () => []
  }
});

const toast = useToast();

// State management
const allTasks = ref([]);
const isLoadingTasks = ref(false);
const savedConfigs = ref([]);
const availableFiles = ref([]);
const selectedFiles = ref([]);
const selectedConfig = ref('quick');
const selectedSavedConfig = ref('');
const selectedTask = ref(null);
const showConfigManager = ref(false);
const showCompletedTasks = ref(false);
const isSubmitting = ref(false);
const saveAsConfig = ref(false);
const configName = ref('');
let pollInterval = null;
const showAllCompleted = ref(false);


const showApiSettings = ref(false);
const apiCredentials = ref({
  api_key: '',
  base_url: ''
});


// Preprocessing configuration
const preprocessingConfig = ref({
  use_ocr: true,
  force_ocr: false,
  ocr_backend: 'ocrmypdf',
  pdf_backend: 'pymupdf4llm',
  ocr_languages: [{value: 'eng', label: 'English'}],
});

// OCR language options
const ocrLanguagesForSelect = ref([
  {value: 'eng', label: 'English'},
  {value: 'spa', label: 'Spanish'},
  {value: 'fra', label: 'French'},
  {value: 'deu', label: 'German'},
  {value: 'ita', label: 'Italian'},
  {value: 'por', label: 'Portuguese'},
  {value: 'rus', label: 'Russian'},
  {value: 'jpn', label: 'Japanese'},
  {value: 'chi_sim', label: 'Chinese (Simplified)'},
  {value: 'chi_tra', label: 'Chinese (Traditional)'},
  {value: 'ara', label: 'Arabic'},
  {value: 'hin', label: 'Hindi'},
  {value: 'kor', label: 'Korean'},
  {value: 'nld', label: 'Dutch'},
  {value: 'pol', label: 'Polish'},
  {value: 'tur', label: 'Turkish'},
  {value: 'vie', label: 'Vietnamese'},
  {value: 'ces', label: 'Czech'},
  {value: 'dan', label: 'Danish'},
  {value: 'fin', label: 'Finnish'},
  {value: 'gre', label: 'Greek'},
  {value: 'heb', label: 'Hebrew'},
  {value: 'hun', label: 'Hungarian'},
  {value: 'nor', label: 'Norwegian'},
  {value: 'swe', label: 'Swedish'},
  {value: 'tha', label: 'Thai'},
  {value: 'ukr', label: 'Ukrainian'},
]);

// Computed properties
const activeTasks = computed(() =>
    allTasks.value.filter(task =>
        ['pending', 'processing', 'in_progress'].includes(task.status)
    )
);

const completedTasks = computed(() =>
    allTasks.value
        .filter(
            (task) =>
                ['completed', 'failed', 'cancelled', 'errored'].includes(task.status)
        )
        .sort(
            (a, b) =>
                new Date(b.completed_at || b.updated_at) -
                new Date(a.completed_at || a.updated_at)
        )
);


const displayedCompletedTasks = computed(() => {
  const filtered = completedTasks.value.filter(Boolean);
  if (showAllCompleted.value) {
    return filtered;
  }
  return filtered.slice(0, 5);
});


const canStartProcessing = computed(() =>
    selectedFiles.value.length > 0 && !isSubmitting.value
);

// API methods
const fetchPreprocessingTasks = async () => {
  if (isLoadingTasks.value) return;

  isLoadingTasks.value = true;
  try {
    // Get all tasks, not just active ones
    const response = await api.get(`/project/${props.projectId}/preprocess?limit=50`);
    allTasks.value = response.data;
    console.log('Fetched tasks:', response.data.map(t => ({
      id: t.id,
      status: t.status,
      file_tasks: t.file_tasks?.length
    })));
  } catch (error) {
    console.error('Failed to fetch preprocessing tasks:', error);
  } finally {
    isLoadingTasks.value = false;
  }
};


const fetchConfigurations = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    savedConfigs.value = response.data;
  } catch (error) {
    console.error('Failed to fetch configurations:', error);
  }
};

const fetchAvailableFiles = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/file?file_creator=user`);
    availableFiles.value = response.data;
  } catch (error) {
    console.error('Failed to fetch files:', error);
  }
};

// Task status updates
const updateTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${taskId}`);
    console.log(`Task ${taskId} status:`, response.data.status, 'File tasks:', response.data.file_tasks?.length);

    const index = allTasks.value.findIndex(task => task.id === taskId);
    if (index !== -1) {
      // Always update the task, even if completed
      allTasks.value[index] = response.data;

      if (selectedTask.value && selectedTask.value.id === taskId) {
        selectedTask.value = response.data;
      }
    } else {
      // Task not found in our list, add it
      allTasks.value.unshift(response.data);
    }
  } catch (error) {
    console.error(`Failed to update task ${taskId}:`, error);
  }
};


// Polling setup
const setupPolling = () => {
  if (pollInterval) clearInterval(pollInterval);

  const pollActiveTasks = () => {
    const tasksToUpdate = allTasks.value.filter(
        task => ['pending', 'processing', 'in_progress'].includes(task.status)
    );

    if (tasksToUpdate.length === 0) {
      clearInterval(pollInterval);
      pollInterval = null;
      return;
    }

    tasksToUpdate.forEach(task => updateTaskStatus(task.id));
  };


  pollActiveTasks();
  pollInterval = setInterval(pollActiveTasks, 2000);
};

// Helper functions
const getAlreadyProcessedFileIds = () => {
  const alreadyDone = new Set();
  allTasks.value.forEach(task => {
    if (task.status === 'completed' && Array.isArray(task.file_ids)) {
      task.file_ids.forEach(id => alreadyDone.add(id));
    }
  });
  return selectedFiles.value.filter(fid => alreadyDone.has(fid));
};

const formatRelativeTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
};

const findExistingConfiguration = (configSettings) => {
  return savedConfigs.value.find(config => {
    // Compare key settings
    return (
        config.file_type === (configSettings.file_type || 'mixed') &&
        config.preprocessing_strategy === (configSettings.preprocessing_strategy || 'full_document') &&
        config.use_ocr === (configSettings.use_ocr !== undefined ? configSettings.use_ocr : true) &&
        config.force_ocr === (configSettings.force_ocr || false) &&
        config.pdf_backend === (configSettings.pdf_backend || 'pymupdf4llm') &&
        config.ocr_backend === (configSettings.ocr_backend || 'ocrmypdf') &&
        // Compare OCR languages
        JSON.stringify(sortLanguages(config.ocr_languages || [])) ===
        JSON.stringify(sortLanguages(configSettings.ocr_languages || ['eng']))
    );
  });
};

const sortLanguages = (langs) => {
  return langs.map(l => typeof l === 'string' ? l : l.value).sort();
};


// Task actions
const startPreprocessing = async () => {
  if (!canStartProcessing.value) return;

  const alreadyProcessedIds = getAlreadyProcessedFileIds();
  if (alreadyProcessedIds.length === selectedFiles.value.length) {
    toast.info('All selected files were already processed. No new task created.');
    return;
  }

  if (alreadyProcessedIds.length > 0) {
    toast.info(`${alreadyProcessedIds.length} selected file(s) were already processed and will be skipped.`);
  }

  const filesToProcess = selectedFiles.value.filter(id => !alreadyProcessedIds.includes(id));
  if (filesToProcess.length === 0) {
    toast.info('No new files to process.');
    return;
  }

  isSubmitting.value = true;
  try {
    let taskData;

    if (selectedConfig.value === 'saved' && selectedSavedConfig.value) {
      taskData = {
        configuration_id: selectedSavedConfig.value,
        file_ids: filesToProcess
      };
    } else {
      // Build configuration
      const config = {
        file_type: 'mixed',
        ...preprocessingConfig.value,
        ocr_languages: preprocessingConfig.value.ocr_languages.map(lang =>
            typeof lang === 'string' ? lang : lang.value
        ),
      };

      // Only save as a named config if explicitly requested
      if (saveAsConfig.value && configName.value) {
        config.name = configName.value;
        config.description = `Created from ${selectedConfig.value} process`;

        const configResponse = await api.post(`/project/${props.projectId}/preprocessing-config`, config);
        taskData = {
          configuration_id: configResponse.data.id,
          file_ids: filesToProcess
        };
        await fetchConfigurations();
      } else {
        // Use inline config - backend will find or create matching config
        config.name = selectedConfig.value === 'quick' ? 'Quick Process' : 'Custom Process';
        taskData = {
          inline_config: config,
          file_ids: filesToProcess
        };
      }
    }

    // Add API credentials if provided
    if (apiCredentials.value.api_key && apiCredentials.value.base_url) {
      taskData.api_key = apiCredentials.value.api_key;
      taskData.base_url = apiCredentials.value.base_url;
    }

    const response = await api.post(`/project/${props.projectId}/preprocess`, taskData);
    allTasks.value.unshift(response.data);

    // Clear form
    selectedFiles.value = [];
    configName.value = '';
    saveAsConfig.value = false;
    apiCredentials.value = {api_key: '', base_url: ''};

    toast.success('Preprocessing task started successfully');
    setupPolling();
  } catch (error) {
    if (error.response?.data?.detail) {
      const details = Array.isArray(error.response.data.detail)
          ? error.response.data.detail.map(d => d.msg).join(', ')
          : error.response.data.detail;
      toast.error(`Failed to start preprocessing: ${details}`);
    } else {
      toast.error('Failed to start preprocessing task');
    }
    console.error(error);
  } finally {
    isSubmitting.value = false;
  }
};

const startQuickPreprocess = async () => {
  const processedIds = new Set();
  allTasks.value.forEach(task => {
    if (task.status === 'completed' && Array.isArray(task.file_ids)) {
      task.file_ids.forEach(id => processedIds.add(id));
    }
  });

  const unprocessedFiles = availableFiles.value.filter(file => !processedIds.has(file.id));
  if (unprocessedFiles.length === 0) {
    toast.info('All files have been processed');
    return;
  }

  isSubmitting.value = true;
  try {
    // Use inline config - backend will reuse existing "Quick Process" config if it exists
    const taskData = {
      inline_config: {
        name: 'Quick Process',
        file_type: 'mixed',
        use_ocr: true,
        force_ocr: false,
        ocr_backend: 'ocrmypdf',
        pdf_backend: 'pymupdf4llm',
        ocr_languages: ['eng'],
        preprocessing_strategy: 'full_document'
      },
      file_ids: unprocessedFiles.map(f => f.id)
    };

    // Add API credentials if provided (though usually not for quick process)
    if (apiCredentials.value.api_key && apiCredentials.value.base_url) {
      taskData.api_key = apiCredentials.value.api_key;
      taskData.base_url = apiCredentials.value.base_url;
    }

    const response = await api.post(`/project/${props.projectId}/preprocess`, taskData);
    allTasks.value.unshift(response.data);

    toast.success('Quick preprocessing started for all unprocessed files');
    setupPolling();
  } catch (error) {
    toast.error('Failed to start quick preprocessing');
    console.error(error);
  } finally {
    isSubmitting.value = false;
  }
};


const cancelTask = async (task) => {
  try {
    const keepProcessed = await confirm('Keep already processed files?');
    await api.post(`/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=${keepProcessed}`);
    toast.success('Task cancelled');
    fetchPreprocessingTasks();
  } catch (error) {
    toast.error('Failed to cancel task');
  }
};

const retryTask = async (task) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${task.id}/retry-failed`);
    allTasks.value.unshift(response.data);
    toast.success('Retry task created');
    setupPolling();
  } catch (error) {
    toast.error('Failed to retry task');
  }
};

const cancelAllTasks = async () => {
  if (!confirm('Cancel all active tasks?')) return;
  for (const task of activeTasks.value) {
    await cancelTask(task);
  }
};

const viewTaskDetails = async (task) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${task.id}`);
    selectedTask.value = response.data;
  } catch (error) {
    console.error('Failed to fetch task details:', error);
    selectedTask.value = task;
  }
};

const retryFailedFiles = async (taskId) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${taskId}/retry-failed`);
    allTasks.value.unshift(response.data);
    toast.success('Retry task created for failed files');
    selectedTask.value = null;
    setupPolling();
  } catch (error) {
    toast.error('Failed to create retry task');
  }
};

// Form actions
const selectAllFiles = () => {
  selectedFiles.value = availableFiles.value.map(f => f.id);
};

const resetForm = () => {
  selectedFiles.value = [];
  selectedConfig.value = 'quick';
  selectedSavedConfig.value = '';
  configName.value = '';
  saveAsConfig.value = false;
  apiCredentials.value = {api_key: '', base_url: ''};
  showApiSettings.value = false;
};


const applyConfiguration = (config) => {
  selectedConfig.value = 'saved';
  selectedSavedConfig.value = config.id;
  showConfigManager.value = false;
};

// Lifecycle hooks
onMounted(() => {
  fetchPreprocessingTasks();
  fetchConfigurations();
  fetchAvailableFiles();

  if (activeTasks.value.length > 0) {
    setupPolling();
  }
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});

// Watchers
watch(() => props.files, (newFiles) => {
  availableFiles.value = newFiles;
}, {immediate: true});

watch(() => activeTasks.value.length, (newLength, oldLength) => {
  if (newLength > 0 && !pollInterval) {
    setupPolling();
  }
});

watch(() => completedTasks.value.length, () => {
  // Reset to collapsed view when tasks change
  showAllCompleted.value = false;
});
</script>


<style>
/* Multiselect styling - ensure dropdown behavior works correctly */
.multiselect-custom {
  --ms-bg: #ffffff;
  --ms-border-color: #d1d5db;
  --ms-border-color-active: #3b82f6;
  --ms-radius: 0.375rem;
  --ms-py: 0.375rem;
  --ms-px: 0.75rem;
  --ms-font-size: 0.875rem;
  --ms-line-height: 1.25rem;
  --ms-option-bg-selected: #eff6ff;
  --ms-option-color-selected: #1e40af;
  --ms-tag-bg: #3b82f6;
  --ms-tag-color: #ffffff;
  --ms-dropdown-bg: #ffffff;
  --ms-dropdown-border-color: #e5e7eb;
  --ms-group-label-bg: #f9fafb;
  --ms-option-bg-pointed: #eff6ff;
  --ms-option-color-pointed: #1e40af;
  --ms-dropdown-radius: 0.375rem;
  --ms-spinner-color: #3b82f6;
  --ms-max-height: 15rem;
  --ms-tag-font-size: 0.75rem;
  --ms-tag-line-height: 1rem;
  --ms-tag-font-weight: 500;
  --ms-tag-py: 0.125rem;
  --ms-tag-px: 0.5rem;
  --ms-tag-radius: 0.25rem;
  --ms-tag-margin: 0.25rem;
}

/* Ensure dropdown is hidden by default and only shows when active */
.multiselect-custom .multiselect-dropdown {
  position: absolute !important;
  top: 100% !important;
  left: 0 !important;
  right: 0 !important;
  margin-top: 0.25rem !important;
  background-color: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 0.375rem !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
  z-index: 50 !important;
  max-height: 15rem !important;
  overflow-y: auto !important;
  display: none !important;
}

/* Show dropdown only when multiselect is open */
.multiselect-custom.is-open .multiselect-dropdown {
  display: block !important;
}

/* Ensure the multiselect wrapper has relative positioning */
.multiselect-custom.multiselect {
  position: relative !important;
}

/* Style the multiselect input area */
.multiselect-custom .multiselect-wrapper {
  background-color: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 0.375rem !important;
  min-height: 2.5rem !important;
  cursor: pointer !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
}

/* When focused */
.multiselect-custom.is-active .multiselect-wrapper {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

/* Style the options */
.multiselect-custom .multiselect-option {
  display: block !important;
  padding: 0.5rem 0.75rem !important;
  cursor: pointer !important;
  background-color: transparent !important;
}

.multiselect-custom .multiselect-option.is-pointed {
  background-color: #eff6ff !important;
  color: #1e40af !important;
}

.multiselect-custom .multiselect-option.is-selected {
  background-color: #dbeafe !important;
  color: #1e40af !important;
  font-weight: 500 !important;
}

/* Hide the native selected options display */
.multiselect-custom .multiselect-option.is-selected.is-hidden {
  display: none !important;
}

/* Style the tags */
.multiselect-custom .multiselect-tag {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  padding: 0.125rem 0.5rem !important;
  border-radius: 0.25rem !important;
  margin: 0.25rem !important;
  display: inline-flex !important;
  align-items: center !important;
}

/* Tag container */
.multiselect-custom .multiselect-tags {
  padding: 0.25rem !important;
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0 !important;
  margin: 0 !important;
}

/* Tag remove button */
.multiselect-custom .multiselect-tag-remove {
  margin-left: 0.25rem !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 1rem !important;
  height: 1rem !important;
  border-radius: 9999px !important;
  background-color: rgba(255, 255, 255, 0.2) !important;
  transition: background-color 0.2s !important;
}

.multiselect-custom .multiselect-tag-remove:hover {
  background-color: rgba(255, 255, 255, 0.3) !important;
}

.multiselect-custom .multiselect-tag-remove-icon {
  width: 0.75rem !important;
  height: 0.75rem !important;
  display: block !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'%3E%3Cpath stroke='%23ffffff' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M6 18L18 6M6 6l12 12'/%3E%3C/svg%3E") !important;
  background-size: contain !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
}

/* Ensure proper input styling */
.multiselect-custom .multiselect-input {
  background-color: transparent !important;
  border: none !important;
  font-size: 0.875rem !important;
  padding: 0.375rem 0.75rem !important;
  margin: 0 !important;
  width: auto !important;
  outline: none !important;
  min-width: 10rem !important;
}

/* Placeholder */
.multiselect-custom .multiselect-placeholder {
  color: #9ca3af !important;
  padding: 0.375rem 0.75rem !important;
  display: block !important;
}

/* Clear button */
.multiselect-custom .multiselect-clear {
  margin-right: 0.5rem !important;
  padding: 0.25rem !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  background-color: transparent !important;
  border-radius: 0.25rem !important;
  transition: background-color 0.2s !important;
}

.multiselect-custom .multiselect-clear:hover {
  background-color: #f3f4f6 !important;
}

.multiselect-custom .multiselect-clear-icon {
  width: 1rem !important;
  height: 1rem !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M6 18L18 6M6 6l12 12'/%3E%3C/svg%3E") !important;
  background-size: contain !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
}

/* Caret icon */
.multiselect-custom .multiselect-caret {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E") !important;
  background-position: center !important;
  background-repeat: no-repeat !important;
  background-size: 1.25rem 1.25rem !important;
  height: 1.25rem !important;
  width: 1.25rem !important;
  margin-right: 0.5rem !important;
  transition: transform 0.2s !important;
  flex-shrink: 0 !important;
}

/* Rotate caret when open */
.multiselect-custom.is-open .multiselect-caret {
  transform: rotate(180deg) !important;
}

/* Ensure the multiselect takes full width */
.multiselect-custom {
  width: 100% !important;
}

/* Options list */
.multiselect-custom .multiselect-options {
  list-style: none !important;
  margin: 0 !important;
  padding: 0.25rem 0 !important;
}

/* No options message */
.multiselect-custom .multiselect-no-options,
.multiselect-custom .multiselect-no-results {
  padding: 0.5rem 0.75rem !important;
  color: #6b7280 !important;
  font-size: 0.875rem !important;
}

/* Ensure selected items are properly hidden from the dropdown */
.multiselect-custom .multiselect-options .is-selected {
  display: none !important;
}

/* Spinner */
.multiselect-custom .multiselect-spinner {
  margin-right: 0.5rem !important;
}

/* Single value display */
.multiselect-custom .multiselect-single-label {
  padding: 0.375rem 0.75rem !important;
  display: block !important;
  font-size: 0.875rem !important;
}

/* Tags search */
.multiselect-custom .multiselect-tags-search-wrapper {
  display: inline-block !important;
  margin: 0.25rem !important;
  flex-grow: 1 !important;
  flex-shrink: 1 !important;
  min-width: 10rem !important;
}

.multiselect-custom .multiselect-tags-search {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  font-size: 0.875rem !important;
  line-height: 1.25rem !important;
  padding: 0.125rem 0 !important;
  margin: 0 !important;
  width: 100% !important;
}

/* Ensure proper layout */
.multiselect-custom .multiselect-tags-search-copy {
  visibility: hidden !important;
  white-space: pre-wrap !important;
  display: inline-block !important;
  font-size: 0.875rem !important;
  line-height: 1.25rem !important;
  padding: 0.125rem 0 !important;
  min-width: 10rem !important;
}

/* Hide the duplicate selected values text */
.multiselect-custom .multiselect-single-label {
  display: none !important;
}

/* Hide the multiselect value display that shows selected items as text */
.multiselect-custom .multiselect-multiple-label {
  display: none !important;
}

/* Ensure only tags are visible */
.multiselect-custom.is-active .multiselect-multiple-label,
.multiselect-custom:not(.is-active) .multiselect-multiple-label {
  display: none !important;
}

/* Fix the multiselect wrapper to only show tags */
.multiselect-custom .multiselect-wrapper {
  min-height: 2.5rem !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
}

/* Ensure tags container is properly styled */
.multiselect-custom .multiselect-tags {
  flex: 1 !important;
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  padding: 0.25rem !important;
  margin: 0 !important;
}

/* Hide any text nodes that might be showing selected values */
.multiselect-custom .multiselect-tags-search-wrapper ~ span,
.multiselect-custom .multiselect-tags-search-wrapper ~ div:not(.multiselect-tag) {
  display: none !important;
}

/* Hide the assistive text that shows selected values as plain text */
.multiselect-custom .multiselect-assistive-text {
  display: none !important;
}

/* Alternative: make it truly invisible but keep it for screen readers */
.multiselect-custom .multiselect-assistive-text {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

/* Also ensure the tags look good */
.multiselect-custom .multiselect-tag {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.25rem 0.75rem !important;
  padding-right: 2rem !important; /* Make room for the X button */
  border-radius: 0.375rem !important;
  margin: 0.25rem !important;
  display: inline-flex !important;
  align-items: center !important;
  position: relative !important;
}

/* Style the remove button properly */
.multiselect-custom .multiselect-tag-remove {
  position: absolute !important;
  right: 0.25rem !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 1.25rem !important;
  height: 1.25rem !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  border-radius: 0.25rem !important;
  transition: background-color 0.2s !important;
}

.multiselect-custom .multiselect-tag-remove:hover {
  background-color: rgba(255, 255, 255, 0.2) !important;
}

/* Ensure the tag remove icon is visible */
.multiselect-custom .multiselect-tag-remove-icon {
  width: 0.875rem !important;
  height: 0.875rem !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none'%3E%3Cpath stroke='%23ffffff' stroke-linecap='round' stroke-linejoin='round' stroke-width='3' d='M6 18L18 6M6 6l12 12'/%3E%3C/svg%3E") !important;
  background-size: contain !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
}

.fade-expand-enter-active,
.fade-expand-leave-active {
  transition: all 0.3s cubic-bezier(.4,0,.2,1), opacity 0.3s;
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