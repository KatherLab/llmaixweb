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
          :aria-expanded="showCompletedTasks.toString()"
          class="flex items-center justify-between px-6 py-4 cursor-pointer select-none hover:bg-gray-50 active:bg-gray-100 rounded-t-2xl transition group focus:outline-none"
          role="button"
          tabindex="0"
          @click="showCompletedTasks = !showCompletedTasks"
          @keyup.enter.space="showCompletedTasks = !showCompletedTasks"
      >
        <div class="flex items-center gap-2">
          <svg class="h-6 w-6 text-emerald-500 transition-transform" fill="none" stroke="currentColor"
               viewBox="0 0 24 24">
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
              :class="{ 'rotate-180': showCompletedTasks }"
              class="h-4 w-4 transition-transform duration-300"
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
          appear
          mode="out-in"
          name="fade-expand"
      >
        <div
            v-show="showCompletedTasks"
            key="completed-tasks-list"
            class="px-4 pb-2 pt-1 space-y-1 overflow-hidden"
        >
          <!-- Tasks List -->
          <div
              v-for="task in displayedCompletedTasks"
              :key="task.id"
              class="flex items-center justify-between bg-white/90 border border-gray-100 rounded-lg px-3 py-2 my-1 shadow-xs hover:shadow-md hover:bg-blue-50 transition group cursor-pointer"
              tabindex="0"
              @click="viewTaskDetails(task)"
              @keyup.enter.space="viewTaskDetails(task)"
          >
            <!-- Left: Status Icon, Task Info -->
            <div class="flex items-center gap-3 min-w-0">
              <span
                  :class="{
                  'bg-green-50': task.status === 'completed',
                  'bg-red-50': task.status === 'failed',
                  'bg-yellow-50': task.status === 'cancelled' || task.status === 'errored'
                }"
                  class="w-6 h-6 flex items-center justify-center rounded-full"
              >
                <svg v-if="task.status === 'completed'" class="w-4 h-4 text-emerald-500" fill="none"
                     stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="task.status === 'failed'" class="w-4 h-4 text-red-500" fill="none" stroke="currentColor"
                     viewBox="0 0 24 24">
                  <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else class="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" fill="none" r="10" stroke="currentColor" stroke-width="2"/>
                  <path d="M12 8v4m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
              </span>
              <div class="flex flex-col text-xs min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-900 truncate">Task #{{ task.id }}</span>
                  <span v-if="task.configuration?.name" class="text-gray-500 truncate">— {{
                      task.configuration.name
                    }}</span>
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
                  <span v-if="task.processed_files - task.failed_files - (task.skipped_files || 0) > 0"
                        class="text-green-500">
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
              <span :title="task.completed_at || task.updated_at" class="text-xs text-gray-400">
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

    <!-- Update the configuration selection section -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200">
      <div class="p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-6">Create New Preprocessing Task</h3>

        <!-- Mode Selection -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-3">
            Processing Mode
          </label>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedMode === 'quick'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectMode('quick')"
            >
              <svg :class="selectedMode === 'quick' ? 'text-blue-600' : 'text-gray-400'"
                   class="h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M13 10V3L4 14h7v7l9-11h-7z" stroke-linecap="round" stroke-linejoin="round"
                      stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Quick Process</span>
              <span class="text-xs text-gray-500 mt-1 text-center">Fast extraction<br/>OCRmyPDF</span>
            </button>

            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedMode === 'better'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectMode('better')"
            >
              <svg :class="selectedMode === 'better' ? 'text-blue-600' : 'text-gray-400'"
                   class="h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Better Quality</span>
              <span class="text-xs text-gray-500 mt-1 text-center">Enhanced OCR<br/>PaddleOCR</span>
            </button>

            <button
                :class="[
                'relative rounded-lg border-2 p-4 flex flex-col items-center justify-center transition-all',
                selectedMode === 'custom'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
                @click="selectMode('custom')"
            >
              <svg :class="selectedMode === 'custom' ? 'text-blue-600' : 'text-gray-400'"
                   class="h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                    d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              <span class="font-medium text-sm">Custom</span>
              <span class="text-xs text-gray-500 mt-1">Full control</span>
            </button>
          </div>

          <!-- Mode-specific presets -->
          <div v-if="selectedMode !== 'custom'" class="mt-4 p-4 bg-blue-50 rounded-lg">
            <div class="flex items-start">
              <svg class="h-5 w-5 text-blue-600 mt-0.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              <div class="text-sm text-blue-900">
                <p v-if="selectedMode === 'quick'">
                  <strong>Quick Process:</strong> Uses OCRmyPDF for fast text extraction.
                  Best for digital PDFs and simple scanned documents.
                </p>
                <p v-else-if="selectedMode === 'better'">
                  <strong>Better Quality:</strong> Uses PaddleOCR for enhanced text recognition.
                  Recommended for complex layouts, handwritten text, or poor quality scans.
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Custom Settings (shown only in custom mode) -->
        <div v-if="selectedMode === 'custom'" class="space-y-6 mb-6">
          <!-- Saved Configuration Selection -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                      stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              Load Saved Configuration
            </h4>
            <div class="space-y-3">
              <select
                v-model="selectedSavedConfig"
                @change="loadSavedConfiguration"
                class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
              >
                <option value="">Start from scratch...</option>
                <option
                  v-for="config in savedConfigs"
                  :key="config.id"
                  :value="config.id"
                >
                  {{ config.name }}{{ config.description ? ` - ${config.description}` : '' }}
                </option>
              </select>
              <p v-if="selectedSavedConfig" class="text-sm text-gray-600">
                Configuration loaded. You can modify settings below and save as a new configuration if needed.
              </p>
            </div>
          </div>

          <!-- Processing Mode -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4">Processing Mode</h4>
            <div class="space-y-3">
              <label class="flex items-center">
                <input
                    v-model="customSettings.mode"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500"
                    type="radio"
                    value="fast"
                />
                <span class="ml-2 text-sm text-gray-700">Fast Mode (PyMuPDF extraction)</span>
              </label>
              <label class="flex items-center">
                <input
                    v-model="customSettings.mode"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500"
                    type="radio"
                    value="advanced"
                />
                <span class="ml-2 text-sm text-gray-700">Advanced Mode (Docling extraction)</span>
              </label>
            </div>
          </div>

          <!-- OCR Settings -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              OCR Settings
            </h4>

            <div class="space-y-4">
              <label class="flex items-center">
                <input
                    v-model="customSettings.force_ocr"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Force OCR (ignore existing text)</span>
              </label>

              <!-- OCR Engine Selection -->
              <div v-if="customSettings.mode === 'fast'">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  OCR Engine
                </label>
                <select
                    v-model="customSettings.ocr_engine"
                    class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                >
                  <option value="ocrmypdf">OCRmyPDF (Tesseract)</option>
                  <option value="paddleocr">PaddleOCR</option>
                  <option value="surya">Surya OCR</option>
                </select>
              </div>

              <!-- Docling OCR Engine (for advanced mode) -->
              <div v-if="customSettings.mode === 'advanced' && !customSettings.use_vlm">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Docling OCR Engine
                </label>
                <select
                    v-model="customSettings.docling_ocr_engine"
                    class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                >
                  <option value="rapidocr">RapidOCR (Default)</option>
                  <option value="easyocr">EasyOCR</option>
                  <option value="tesseract">Tesseract</option>
                </select>
              </div>

              <!-- Language Selection (only for tesseract) -->
              <div v-if="(customSettings.mode === 'fast' && customSettings.ocr_engine === 'ocrmypdf') ||
                         (customSettings.mode === 'advanced' && customSettings.docling_ocr_engine === 'tesseract')"
                   class="relative">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  OCR Languages
                </label>
                <Multiselect
                    v-model="customSettings.ocr_languages"
                    :canClear="true"
                    :canDeselect="true"
                    :clearOnSelect="false"
                    :closeOnSelect="false"
                    :createOption="false"
                    :hideSelected="true"
                    :object="true"
                    :options="ocrLanguagesForSelect"
                    :preselect-first="false"
                    :preserveSearch="true"
                    :searchable="true"
                    class="multiselect-custom"
                    label="label"
                    mode="tags"
                    placeholder="Select languages"
                    trackBy="value"
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

          <!-- Advanced Features (only in advanced mode) -->
          <div v-if="customSettings.mode === 'advanced' && !customSettings.use_vlm"
               class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              Advanced Extraction Features
            </h4>
            <div class="space-y-3">
              <label class="flex items-center">
                <input
                    v-model="customSettings.enable_picture_description"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Extract picture descriptions</span>
              </label>
              <label class="flex items-center">
                <input
                    v-model="customSettings.enable_formula"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Extract formulas</span>
              </label>
              <label class="flex items-center">
                <input
                    v-model="customSettings.enable_code"
                    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    type="checkbox"
                />
                <span class="ml-2 text-sm text-gray-700">Extract code blocks</span>
              </label>
            </div>
            <p class="mt-3 text-xs text-gray-500">
              Note: These features use Docling's internal processing and may increase processing time.
            </p>
          </div>

          <!-- VLM Settings -->
          <div v-if="customSettings.mode === 'advanced'" class="bg-gray-50 rounded-lg p-4">
            <h4 class="font-medium text-gray-900 mb-4 flex items-center">
              <svg class="h-5 w-5 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round"
                      stroke-width="2"/>
                <path
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              Vision Language Model (VLM) Settings
            </h4>

            <label class="flex items-center mb-4">
              <input
                  v-model="customSettings.use_vlm"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  type="checkbox"
              />
              <span class="ml-2 text-sm text-gray-700">Use Vision Language Model for enrichment</span>
            </label>

            <div v-if="customSettings.use_vlm" class="space-y-4 ml-6">
              <!-- VLM Type Selection -->
              <div class="space-y-3">
                <label class="flex items-center">
                  <input
                      v-model="customSettings.use_local_vlm"
                      :value="false"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      type="radio"
                  />
                  <span class="ml-2 text-sm text-gray-700">Remote VLM (OpenAI-compatible API)</span>
                </label>

                <!-- Remote VLM Settings -->
                <div v-if="!customSettings.use_local_vlm" class="ml-6 space-y-3">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                    <select
                        v-model="customSettings.vlm_model"
                        class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                    >
                      <option value="">Use default model</option>
                      <option value="gpt-4-vision-preview">GPT-4 Vision</option>
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                      <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                      <option value="custom">Custom model...</option>
                    </select>
                    <input
                        v-if="customSettings.vlm_model === 'custom'"
                        v-model="customSettings.vlm_custom_model"
                        class="mt-2 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="Enter model name"
                        type="text"
                    />
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      Custom API Base URL (optional)
                    </label>
                    <input
                        v-model="customSettings.vlm_base_url"
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="https://api.openai.com/v1"
                        type="text"
                    />
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      API Key (optional)
                    </label>
                    <input
                        v-model="vlmApiKey"
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="sk-..."
                        type="password"
                    />
                  </div>

                  <!-- Test Connection Button -->
                  <div class="flex items-center space-x-3">
                    <button
                        :disabled="!canTestVLM || isTestingVLM"
                        class="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        @click="testVLMConnection"
                    >
                      <svg v-if="isTestingVLM" class="animate-spin -ml-0.5 mr-2 h-4 w-4" fill="none"
                           viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                stroke-width="4"></circle>
                        <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                              fill="currentColor"></path>
                      </svg>
                      <span v-else>Test Image Support</span>
                    </button>

                    <span v-if="vlmTestResult !== null" class="text-sm">
                      <span v-if="vlmTestResult.supported" class="text-green-600 flex items-center">
                        <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        {{ vlmTestResult.message }}
                      </span>
                      <span v-else class="text-red-600 flex items-center">
                        <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"
                                stroke-width="2"/>
                        </svg>
                        {{ vlmTestResult.message }}
                      </span>
                    </span>
                  </div>
                </div>

                <!-- Local VLM Settings (hidden) -->
                <label v-show="false" class="flex items-center">
                  <input
                      v-model="customSettings.use_local_vlm"
                      :value="true"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500"
                      type="radio"
                  />
                  <span class="ml-2 text-sm text-gray-700">Local VLM (HuggingFace)</span>
                </label>

                <div v-if="customSettings.use_local_vlm" v-show="false" class="ml-6 space-y-3">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                    <select
                        v-model="customSettings.local_vlm_repo_id"
                        class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-lg"
                    >
                      <option value="HuggingFaceTB/SmolVLM-256M-Instruct">SmolVLM-256M-Instruct</option>
                      <option value="custom">Custom HuggingFace model...</option>
                    </select>
                    <input
                        v-if="customSettings.local_vlm_repo_id === 'custom'"
                        v-model="customSettings.local_vlm_custom_repo"
                        class="mt-2 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        placeholder="organization/model-name"
                        type="text"
                    />
                  </div>
                </div>
              </div>

              <!-- VLM Prompt -->
              <div v-if="customSettings.use_vlm" class="ml-6">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  VLM Prompt (optional)
                </label>
                <textarea
                    v-model="customSettings.vlm_prompt"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Please perform OCR! Please extract the full text from the document and describe images and figures!"
                    rows="3"
                />
              </div>

              <!-- Max Image Dimension -->
              <div v-if="customSettings.use_vlm" class="ml-6">
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Max Image Dimension (pixels)
                </label>
                <input
                    v-model.number="customSettings.max_image_dim"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    max="2048"
                    min="400"
                    step="100"
                    type="number"
                />
                <p class="mt-1 text-xs text-gray-500">
                  Images will be scaled down to this maximum dimension while preserving aspect ratio
                </p>
              </div>
            </div>

            <div
                v-if="customSettings.use_vlm && (customSettings.enable_picture_description || customSettings.enable_formula || customSettings.enable_code)"
                class="mt-3 p-3 bg-yellow-50 rounded-lg">
              <p class="text-sm text-yellow-800">
                <svg class="inline h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                Note: Advanced extraction features (picture description, formula, code) cannot be used together with
                VLM.
                Please disable VLM to use these features.
              </p>
            </div>
          </div>
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
                 fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor"></path>
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
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
const selectedTask = ref(null);
const showConfigManager = ref(false);
const showCompletedTasks = ref(false);
const isSubmitting = ref(false);
const saveAsConfig = ref(false);
const configName = ref('');
let pollInterval = null;
const showAllCompleted = ref(false);
const showApiSettings = ref(false);

// New state for preprocessing modes
const selectedMode = ref('quick');
const selectedConfig = ref('quick'); // Keep for saved configs
const selectedSavedConfig = ref('');

const customSettings = ref({
  mode: 'fast',
  ocr_engine: 'ocrmypdf',
  docling_ocr_engine: 'rapidocr',
  force_ocr: false,
  ocr_languages: [{ value: 'eng', label: 'English' }],
  enable_picture_description: false,
  enable_formula: false,
  enable_code: false,
  max_image_dim: 800,
  use_vlm: false,
  use_local_vlm: false,
  local_vlm_repo_id: 'HuggingFaceTB/SmolVLM-256M-Instruct',
  local_vlm_custom_repo: '',
  vlm_model: '',
  vlm_custom_model: '',
  vlm_base_url: '',
  vlm_prompt: 'Please perform OCR! Please extract the full text from the document and describe images and figures!'
});

const vlmApiKey = ref('');
const vlmTestResult = ref(null);
const isTestingVLM = ref(false);

// OCR language options
const ocrLanguagesForSelect = ref([
  { value: 'eng', label: 'English' },
  { value: 'spa', label: 'Spanish' },
  { value: 'fra', label: 'French' },
  { value: 'deu', label: 'German' },
  { value: 'ita', label: 'Italian' },
  { value: 'por', label: 'Portuguese' },
  { value: 'rus', label: 'Russian' },
  { value: 'jpn', label: 'Japanese' },
  { value: 'chi_sim', label: 'Chinese (Simplified)' },
  { value: 'chi_tra', label: 'Chinese (Traditional)' },
  { value: 'ara', label: 'Arabic' },
  { value: 'hin', label: 'Hindi' },
  { value: 'kor', label: 'Korean' },
  { value: 'nld', label: 'Dutch' },
  { value: 'pol', label: 'Polish' },
  { value: 'tur', label: 'Turkish' },
  { value: 'vie', label: 'Vietnamese' },
  { value: 'ces', label: 'Czech' },
  { value: 'dan', label: 'Danish' },
  { value: 'fin', label: 'Finnish' },
  { value: 'gre', label: 'Greek' },
  { value: 'heb', label: 'Hebrew' },
  { value: 'hun', label: 'Hungarian' },
  { value: 'nor', label: 'Norwegian' },
  { value: 'swe', label: 'Swedish' },
  { value: 'tha', label: 'Thai' },
  { value: 'ukr', label: 'Ukrainian' },
]);

// Mode selection handler
const selectMode = (mode) => {
  selectedMode.value = mode;

  // Reset settings based on mode
  if (mode === 'quick') {
    customSettings.value = {
      ...customSettings.value,
      mode: 'fast',
      ocr_engine: 'ocrmypdf',
      force_ocr: false,
      use_vlm: false,
      enable_picture_description: false,
      enable_formula: false,
      enable_code: false
    };
  } else if (mode === 'better') {
    customSettings.value = {
      ...customSettings.value,
      mode: 'fast',
      ocr_engine: 'paddleocr',
      force_ocr: false,
      use_vlm: false,
      enable_picture_description: false,
      enable_formula: false,
      enable_code: false
    };
  } else if (mode === 'saved') {
    // Don't reset custom settings when selecting saved config
  }

  // Reset VLM test result when changing modes
  vlmTestResult.value = null;
};

// Computed properties
const activeTasks = computed(() =>
  allTasks.value.filter(task =>
    ['pending', 'processing', 'in_progress'].includes(task.status)
  )
);

const completedTasks = computed(() =>
  allTasks.value
    .filter(task =>
      ['completed', 'failed', 'cancelled', 'errored'].includes(task.status)
    )
    .sort((a, b) =>
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

const canTestVLM = computed(() => {
  if (customSettings.value.use_local_vlm) {
    return customSettings.value.local_vlm_repo_id || customSettings.value.local_vlm_custom_repo;
  }

  const model = customSettings.value.vlm_model === 'custom'
    ? customSettings.value.vlm_custom_model
    : customSettings.value.vlm_model;

  return model && (vlmApiKey.value || customSettings.value.vlm_base_url);
});

const canStartProcessing = computed(() => {
  if (!selectedFiles.value.length || isSubmitting.value) return false;

  // If using saved config, make sure one is selected
  if (selectedMode.value === 'saved' && !selectedSavedConfig.value) return false;

  // If using remote VLM, must have successful test
  if (selectedMode.value === 'custom' &&
      customSettings.value.mode === 'advanced' &&
      customSettings.value.use_vlm &&
      !customSettings.value.use_local_vlm) {
    return vlmTestResult.value?.supported === true;
  }

  return true;
});

// API methods
const fetchPreprocessingTasks = async () => {
  if (isLoadingTasks.value) return;

  isLoadingTasks.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess?limit=50`);
    allTasks.value = response.data;
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

const loadSavedConfiguration = () => {
  if (!selectedSavedConfig.value) {
    // Reset to defaults
    customSettings.value = {
      mode: 'fast',
      ocr_engine: 'ocrmypdf',
      docling_ocr_engine: 'rapidocr',
      force_ocr: false,
      ocr_languages: [{ value: 'eng', label: 'English' }],
      enable_picture_description: false,
      enable_formula: false,
      enable_code: false,
      max_image_dim: 800,
      use_vlm: false,
      use_local_vlm: false,
      local_vlm_repo_id: 'HuggingFaceTB/SmolVLM-256M-Instruct',
      local_vlm_custom_repo: '',
      vlm_model: '',
      vlm_custom_model: '',
      vlm_base_url: '',
      vlm_prompt: 'Please perform OCR! Please extract the full text from the document and describe images and figures!'
    };
    return;
  }

  const config = savedConfigs.value.find(c => c.id === selectedSavedConfig.value);
  if (!config) return;

  // Load settings from saved configuration
  if (config.additional_settings) {
    customSettings.value = {
      ...customSettings.value,
      ...config.additional_settings,
      force_ocr: config.force_ocr || false,
      ocr_languages: config.ocr_languages?.map(lang =>
        typeof lang === 'string'
          ? ocrLanguagesForSelect.value.find(l => l.value === lang) || { value: lang, label: lang }
          : lang
      ) || [{ value: 'eng', label: 'English' }]
    };
  }

  // Clear VLM test result when loading new config
  vlmTestResult.value = null;
};


// VLM test function
const testVLMConnection = async () => {
  if (!canTestVLM.value) return;

  isTestingVLM.value = true;
  vlmTestResult.value = null;

  try {
    const model = customSettings.value.vlm_model === 'custom'
      ? customSettings.value.vlm_custom_model
      : customSettings.value.vlm_model;

    const response = await api.post(`/project/${props.projectId}/test-vlm-image-support`, {
      base_url: customSettings.value.vlm_base_url || 'https://api.openai.com/v1',
      model: model,
      api_key: vlmApiKey.value
    });

    vlmTestResult.value = response.data;
  } catch (error) {
    vlmTestResult.value = {
      supported: false,
      message: error.response?.data?.detail || 'Connection test failed'
    };
  } finally {
    isTestingVLM.value = false;
  }
};

// Task status updates
const updateTaskStatus = async (taskId) => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocess/${taskId}`);

    const index = allTasks.value.findIndex(task => task.id === taskId);
    if (index !== -1) {
      allTasks.value[index] = response.data;

      if (selectedTask.value && selectedTask.value.id === taskId) {
        selectedTask.value = response.data;
      }
    } else {
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

// Task actions
const startPreprocessing = async () => {
  if (!canStartProcessing.value) return;

  isSubmitting.value = true;
  try {
    let taskData;

    if (selectedMode.value === 'quick' || selectedMode.value === 'better') {
      // Use inline config for quick modes
      const config = {
        name: selectedMode.value === 'quick' ? 'Quick Process' : 'Better Quality Quick Process',
        file_type: 'mixed',
        preprocessing_strategy: 'full_document',
        pdf_backend: 'pymupdf4llm',
        ocr_backend: 'ocrmypdf',
        use_ocr: true,
        force_ocr: false,
        ocr_languages: ['eng'],
        additional_settings: {
          mode: 'fast',
          ocr_engine: selectedMode.value === 'quick' ? 'ocrmypdf' : 'paddleocr'
        }
      };

      taskData = {
        inline_config: config,
        file_ids: selectedFiles.value
      };
    } else if (selectedMode.value === 'saved' && selectedSavedConfig.value) {
      taskData = {
        configuration_id: selectedSavedConfig.value,
        file_ids: selectedFiles.value
      };
    } else {
      // Custom mode - build full configuration
      const config = {
        name: saveAsConfig.value && configName.value ? configName.value : 'Custom Process',
        file_type: 'mixed',
        preprocessing_strategy: 'full_document',
        pdf_backend: 'pymupdf4llm',
        ocr_backend: customSettings.value.ocr_engine,
        use_ocr: true,
        force_ocr: customSettings.value.force_ocr,
        ocr_languages: customSettings.value.ocr_languages.map(lang =>
          typeof lang === 'string' ? lang : lang.value
        ),
        additional_settings: {
          mode: customSettings.value.mode,
          ocr_engine: customSettings.value.ocr_engine,
          docling_ocr_engine: customSettings.value.docling_ocr_engine,
          enable_picture_description: customSettings.value.enable_picture_description,
          enable_formula: customSettings.value.enable_formula,
          enable_code: customSettings.value.enable_code,
          max_image_dim: customSettings.value.max_image_dim,
          use_vlm: customSettings.value.use_vlm,
          use_local_vlm: customSettings.value.use_local_vlm,
          local_vlm_repo_id: customSettings.value.use_local_vlm
            ? (customSettings.value.local_vlm_repo_id === 'custom'
                ? customSettings.value.local_vlm_custom_repo
                : customSettings.value.local_vlm_repo_id)
            : null,
          vlm_model: customSettings.value.vlm_model === 'custom'
            ? customSettings.value.vlm_custom_model
            : customSettings.value.vlm_model,
          vlm_base_url: customSettings.value.vlm_base_url,
          vlm_prompt: customSettings.value.vlm_prompt
        }
      };

      if (saveAsConfig.value && configName.value) {
        const configResponse = await api.post(`/project/${props.projectId}/preprocessing-config`, config);
        taskData = {
          configuration_id: configResponse.data.id,
          file_ids: selectedFiles.value
        };
        await fetchConfigurations();
      } else {
        taskData = {
          inline_config: config,
          file_ids: selectedFiles.value
        };
      }
    }

    // Add API credentials if using VLM
    if (customSettings.value.use_vlm && !customSettings.value.use_local_vlm && vlmApiKey.value) {
      taskData.api_key = vlmApiKey.value;
      taskData.base_url = customSettings.value.vlm_base_url || 'https://api.openai.com/v1';
    }

    const response = await api.post(`/project/${props.projectId}/preprocess`, taskData);
    allTasks.value.unshift(response.data);

    // Clear form
    resetForm();

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
    const taskData = {
      inline_config: {
        name: 'Quick Process',
        file_type: 'mixed',
        use_ocr: true,
        force_ocr: false,
        ocr_backend: 'ocrmypdf',
        pdf_backend: 'pymupdf4llm',
        ocr_languages: ['eng'],
        preprocessing_strategy: 'full_document',
        additional_settings: {
          mode: 'fast',
          ocr_engine: 'ocrmypdf'
        }
      },
      file_ids: unprocessedFiles.map(f => f.id)
    };

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
  selectedMode.value = 'quick';
  selectedConfig.value = 'quick';
  selectedSavedConfig.value = '';
  configName.value = '';
  saveAsConfig.value = false;
  vlmApiKey.value = '';
  vlmTestResult.value = null;
  showApiSettings.value = false;
  customSettings.value = {
    mode: 'fast',
    ocr_engine: 'ocrmypdf',
    docling_ocr_engine: 'rapidocr',
    force_ocr: false,
    ocr_languages: [{ value: 'eng', label: 'English' }],
    enable_picture_description: false,
    enable_formula: false,
    enable_code: false,
    max_image_dim: 800,
    use_vlm: false,
    use_local_vlm: false,
    local_vlm_repo_id: 'HuggingFaceTB/SmolVLM-256M-Instruct',
    local_vlm_custom_repo: '',
    vlm_model: '',
    vlm_custom_model: '',
    vlm_base_url: '',
    vlm_prompt: 'Please perform OCR! Please extract the full text from the document and describe images and figures!'
  };
};

const applyConfiguration = (config) => {
  // Parse the configuration and apply to custom settings
  selectedMode.value = 'saved';
  selectedSavedConfig.value = config.id;

  if (config.additional_settings) {
    customSettings.value = {
      ...customSettings.value,
      ...config.additional_settings,
      ocr_languages: config.ocr_languages?.map(lang =>
        typeof lang === 'string'
          ? ocrLanguagesForSelect.value.find(l => l.value === lang) || { value: lang, label: lang }
          : lang
      ) || [{ value: 'eng', label: 'English' }]
    };
  }

  customSettings.value.force_ocr = config.force_ocr || false;

  showConfigManager.value = false;
};

// Watch for VLM settings changes to reset test
watch([
  () => customSettings.value.vlm_model,
  () => customSettings.value.vlm_custom_model,
  () => customSettings.value.vlm_base_url,
  () => vlmApiKey.value
], () => {
  vlmTestResult.value = null;
});

// Watch for conflicts between VLM and advanced features
watch(() => customSettings.value.use_vlm, (useVlm) => {
  if (useVlm) {
    customSettings.value.enable_picture_description = false;
    customSettings.value.enable_formula = false;
    customSettings.value.enable_code = false;
  }
});

// Watch for advanced features to disable VLM
watch([
  () => customSettings.value.enable_picture_description,
  () => customSettings.value.enable_formula,
  () => customSettings.value.enable_code
], ([picture, formula, code]) => {
  if (picture || formula || code) {
    customSettings.value.use_vlm = false;
  }
});

// Watch for advanced features to switch to advanced mode
watch([
  () => customSettings.value.enable_picture_description,
  () => customSettings.value.enable_formula,
  () => customSettings.value.enable_code
], ([picture, formula, code]) => {
  if ((picture || formula || code) && customSettings.value.mode === 'fast') {
    customSettings.value.mode = 'advanced';
  }
});

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
}, { immediate: true });

watch(() => activeTasks.value.length, (newLength, oldLength) => {
  if (newLength > 0 && !pollInterval) {
    setupPolling();
  }
});

watch(() => completedTasks.value.length, () => {
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
  transition: all 0.3s cubic-bezier(.4, 0, .2, 1), opacity 0.3s;
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