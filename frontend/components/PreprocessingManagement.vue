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
            @cancel="showCancelTaskDialog"
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
        <div v-if="selectedMode === 'custom'"
             class="bg-gradient-to-br from-blue-50/60 to-white border border-blue-200 rounded-2xl px-8 py-8 space-y-10 mt-4 mb-4">

          <!-- Step 1: Configuration Preset -->
          <div>
            <div class="flex items-center gap-3 mb-3">
              <span
                  class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-bold">1</span>
              <span class="text-base font-semibold text-blue-900 tracking-tight">Configuration Preset</span>
              <span v-if="selectedSavedConfig"
                    class="ml-2 px-2 py-0.5 rounded-xl bg-emerald-100 text-emerald-700 text-xs font-medium">Preset Loaded</span>
            </div>
            <div class="flex gap-3 items-center">
              <select
                  v-model="selectedSavedConfig"
                  class="w-full max-w-md border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 transition"
                  @change="loadSavedConfiguration"
              >
                <option value="">Start from scratch...</option>
                <option v-for="config in savedConfigs" :key="config.id" :value="config.id">
                  {{ config.name }}{{ config.description ? ` – ${config.description}` : '' }}
                </option>
              </select>



              <button
                  class="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50"
                  type="button"
                  @click="showConfigManager = true"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                        stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                Manage
              </button>
            </div>
            <!-- Save as Preset UI -->
            <div class="mt-5 flex flex-col md:flex-row md:items-end md:gap-4 gap-3 rounded-xl bg-blue-50/50 border border-blue-100 p-5 shadow-sm">
  <div class="flex-1">
    <label class="block text-xs font-medium text-gray-700 mb-1">Preset Name</label>
    <input
      v-model="presetName"
      type="text"
      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
      maxlength="100"
      placeholder="e.g., 'High Quality VLM Scan'"
      :disabled="isSavingPreset || isUpdatingPreset"
    />
  </div>
  <div class="flex-1">
    <label class="block text-xs font-medium text-gray-700 mb-1">Description</label>
    <input
      v-model="presetDescription"
      type="text"
      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
      maxlength="250"
      placeholder="(optional)"
      :disabled="isSavingPreset || isUpdatingPreset"
    />
  </div>
  <div class="flex flex-col gap-2 min-w-[9rem]">
    <button
      class="px-4 py-2 rounded-lg text-white bg-blue-600 font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      @click="saveAsPreset"
      :disabled="!presetName || isSavingPreset"
      type="button"
    >
      <svg v-if="isSavingPreset" class="animate-spin h-4 w-4 inline-block mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor"></path>
      </svg>
      <span v-else>Save as Preset</span>
    </button>
    <button
      v-if="selectedSavedConfig"
      class="px-4 py-2 rounded-lg text-white bg-emerald-600 font-medium hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      @click="updatePreset"
      :disabled="!presetName || isUpdatingPreset"
      type="button"
    >
      <svg v-if="isUpdatingPreset" class="animate-spin h-4 w-4 inline-block mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor"></path>
      </svg>
      <span v-else>Update Selected</span>
    </button>
  </div>
</div>


            <div class="mt-2 text-xs text-gray-500 ml-1">
              Load a preset or start with blank settings below.
            </div>
          </div>

          <!-- Step 2: Extraction & OCR -->
          <div>
            <div class="flex items-center gap-3 mb-3">
              <span
                  class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-bold">2</span>
              <span class="text-base font-semibold text-blue-900 tracking-tight">Extraction & OCR</span>
            </div>
            <div class="grid md:grid-cols-2 gap-8">

              <!-- Extraction Mode and advanced features -->
              <div>
                <div class="mb-4">
                  <div class="text-sm font-medium text-gray-700 mb-2">Extraction Mode</div>
                  <div class="flex gap-2">
                    <label :class="[
              'flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border transition',
              customSettings.mode === 'fast'
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100'
                : 'border-gray-200 bg-white hover:bg-gray-100'
            ]">
                      <input v-model="customSettings.mode" class="accent-blue-600" type="radio" value="fast"/>
                      Fast (PyMuPDF)
                    </label>
                    <label :class="[
              'flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer border transition',
              customSettings.mode === 'advanced'
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100'
                : 'border-gray-200 bg-white hover:bg-gray-100'
            ]">
                      <input v-model="customSettings.mode" class="accent-blue-600" type="radio" value="advanced"/>
                      Advanced (Docling)
                    </label>
                  </div>
                </div>
                <div v-if="customSettings.mode === 'advanced'" class="space-y-2">
                  <label class="flex items-center gap-2">
                    <input v-model="customSettings.enable_picture_description" :disabled="customSettings.use_vlm" class="accent-blue-600"
                           type="checkbox"/>
                    Extract picture descriptions
                  </label>
                  <label class="flex items-center gap-2">
                    <input v-model="customSettings.enable_formula" :disabled="customSettings.use_vlm" class="accent-blue-600"
                           type="checkbox"/>
                    Extract formulas
                  </label>
                  <label class="flex items-center gap-2">
                    <input v-model="customSettings.enable_code" :disabled="customSettings.use_vlm" class="accent-blue-600"
                           type="checkbox"/>
                    Extract code blocks
                  </label>
                  <p v-if="customSettings.use_vlm"
                     class="text-xs text-yellow-700 bg-yellow-50 border border-yellow-100 rounded px-2 py-1 mt-1">
                    <svg class="inline h-4 w-4 -mt-0.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                          stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                    </svg>
                    Advanced extraction options can't be used together with Vision Language Model.
                  </p>
                </div>
              </div>

              <!-- OCR settings -->
              <div>
                <div class="mb-4">
                  <div class="text-sm font-medium text-gray-700 mb-2">OCR Settings</div>
                  <label class="flex items-center gap-2 mb-2">
                    <input v-model="customSettings.force_ocr" class="accent-blue-600" type="checkbox"/>
                    Force OCR (ignore existing text)
                  </label>
                  <div v-if="customSettings.mode === 'fast'" class="mb-2">
                    <label class="block text-xs font-medium text-gray-700 mb-1">OCR Engine</label>
                    <select v-model="customSettings.ocr_engine"
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500">
                      <option value="ocrmypdf">OCRmyPDF (Tesseract)</option>
                      <option value="paddleocr">PaddleOCR</option>
                      <option value="marker">Marker</option>
                    </select>
                  </div>
                  <div v-if="customSettings.mode === 'advanced' && !customSettings.use_vlm" class="mb-2">
                    <label class="block text-xs font-medium text-gray-700 mb-1">Docling OCR Engine</label>
                    <select v-model="customSettings.docling_ocr_engine"
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500">
                      <option value="rapidocr">RapidOCR (Default)</option>
                      <option value="easyocr">EasyOCR</option>
                      <option value="tesseract">Tesseract</option>
                    </select>
                  </div>
                  <div
                      v-if="(customSettings.mode === 'fast' && customSettings.ocr_engine === 'ocrmypdf') ||
                    (customSettings.mode === 'advanced' && customSettings.docling_ocr_engine === 'tesseract')"
                  >
                    <label class="block text-xs font-medium text-gray-700 mb-1">OCR Languages</label>
                    <Multiselect
                        v-model="customSettings.ocr_languages"
                        :object="true"
                        :options="ocrLanguagesForSelect"
                        class="multiselect-custom"
                        label="label"
                        mode="tags"
                        placeholder="Select languages"
                        trackBy="value"
                        valueProp="value"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isAdmin" class="flex items-center gap-2 mb-4">
            <input
              id="bypass-celery"
              type="checkbox"
              v-model="bypassCelery"
              class="accent-blue-600"
            />
            <label for="bypass-celery" class="text-sm text-gray-700">
              Bypass Celery (run synchronously in backend, for debugging)
            </label>
          </div>

          <!-- Step 3: Vision Language Model (only in advanced mode) -->
          <div v-if="customSettings.mode === 'advanced'">
            <div class="flex items-center gap-3 mb-3">
              <span
                  class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-bold">3</span>
              <span class="text-base font-semibold text-blue-900 tracking-tight">Vision Language Model (optional)</span>
              <span v-if="customSettings.use_vlm && vlmModelTested && vlmModelValid"
                    class="ml-2 px-2 py-0.5 rounded-xl bg-green-100 text-green-700 text-xs font-medium">VLM Ready</span>
            </div>
            <div class="space-y-2 bg-blue-50/40 border border-blue-100 rounded-xl p-6">
              <label class="flex items-center gap-2 mb-2">
                <input v-model="customSettings.use_vlm" :disabled="customSettings.enable_picture_description || customSettings.enable_formula || customSettings.enable_code" class="accent-blue-600"
                       type="checkbox"/>
                Use Vision Language Model for enrichment
                <span
                    v-if="customSettings.enable_picture_description || customSettings.enable_formula || customSettings.enable_code"
                    class="ml-2 text-xs bg-yellow-50 text-yellow-700 px-2 py-0.5 rounded border border-yellow-100"
                >Disable advanced extraction above to enable VLM</span>
              </label>

              <div v-if="customSettings.use_vlm" class="mt-3">
                <!-- VLM Model Stepper Card -->
                <div
                    class="relative bg-gradient-to-br from-blue-50 via-white to-gray-50 border border-blue-200 rounded-xl shadow-lg px-6 py-6 mt-6 space-y-6">
                  <div class="flex items-center gap-3 mb-4">
            <span class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
              <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round"
                      stroke-width="2"/>
                <path
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                    stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
            </span>
                    <span class="text-lg font-semibold text-blue-800 tracking-tight">Select Vision Model</span>
                    <span v-if="vlmModelTested && vlmModelValid"
                          class="ml-2 px-2 py-0.5 rounded-xl bg-green-100 text-green-700 text-xs font-medium inline-flex items-center gap-1">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
              Model Tested
            </span>
                  </div>
                  <div class="space-y-5">

                    <!-- Step 1: Select API source -->
                    <div>
                      <div class="mb-2 text-sm font-medium text-gray-700 flex items-center gap-2">
                        <span class="rounded bg-blue-200 text-blue-900 px-2 py-0.5 text-xs font-semibold">Step 1</span>
                        Choose Model Source
                      </div>
                      <div class="flex gap-3 mb-2">
                        <button
                            :class="[
                    !showCustomVLMSettings
                      ? 'border-blue-600 bg-blue-50 ring-2 ring-blue-200'
                      : 'border-gray-300 bg-white hover:bg-gray-50'
                  ]"
                            class="flex-1 flex items-center gap-2 border rounded-lg px-4 py-2 font-medium transition-all focus:outline-none"
                            type="button"
                            @click="showCustomVLMSettings = false"
                        >
                          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M20 13V7a2 2 0 00-2-2H6a2 2 0 00-2 2v6" stroke-linecap="round"
                                  stroke-linejoin="round" stroke-width="2"/>
                            <path d="M9 17v4h6v-4M17 17a2 2 0 002-2V7a2 2 0 00-2-2" stroke-linecap="round"
                                  stroke-linejoin="round" stroke-width="2"/>
                          </svg>
                          <span>System Default</span>
                        </button>
                        <button
                            :class="[
                    showCustomVLMSettings
                      ? 'border-blue-600 bg-blue-50 ring-2 ring-blue-200'
                      : 'border-gray-300 bg-white hover:bg-gray-50'
                  ]"
                            class="flex-1 flex items-center gap-2 border rounded-lg px-4 py-2 font-medium transition-all focus:outline-none"
                            type="button"
                            @click="showCustomVLMSettings = true"
                        >
                          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round"
                                  stroke-width="2"/>
                            <path
                                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                          </svg>
                          <span>Custom API</span>
                        </button>
                      </div>
                      <div class="text-xs text-gray-500 ml-1">
                <span v-if="!showCustomVLMSettings">
                  Uses your organization's default VLM/OpenAI API settings. No configuration needed.
                </span>
                        <span v-else>
                  Allows you to connect to your own API endpoint. Enter your key and base URL.
                </span>
                      </div>
                    </div>

                    <!-- Step 2: Custom API settings -->
                    <transition name="fade-expand">
                      <div v-show="showCustomVLMSettings"
                           class="bg-white border border-blue-100 rounded-xl px-4 py-4 mt-2 space-y-3">
                        <div class="text-sm font-medium text-blue-800 mb-2 flex items-center gap-1">
                          <svg class="h-4 w-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M9 12h6" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                          </svg>
                          Custom API Settings
                        </div>
                        <div>
                          <label class="block text-xs font-semibold text-gray-700 mb-1">API Key</label>
                          <input
                              v-model="vlmApiKey"
                              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                              placeholder="e.g., sk-1234..."
                              type="password"
                          />
                        </div>
                        <div>
                          <label class="block text-xs font-semibold text-gray-700 mb-1">Base URL</label>
                          <input
                              v-model="vlmBaseUrl"
                              class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                              placeholder="e.g., https://my-company-openai-proxy/api/v1"
                              type="text"
                          />
                        </div>
                      </div>
                    </transition>

                    <!-- Step 3: Select Model -->
                    <div>
                      <div class="mb-2 text-sm font-medium text-gray-700 flex items-center gap-2">
                        <span class="rounded bg-blue-200 text-blue-900 px-2 py-0.5 text-xs font-semibold">Step 2</span>
                        Pick Vision Model
                      </div>
                      <div class="flex gap-2 items-center">
                        <svg v-if="isLoadingVLMModels" class="animate-spin h-5 w-5 text-blue-400" fill="none"
                             viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                  stroke-width="4"></circle>
                          <path class="opacity-75"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                fill="currentColor"></path>
                        </svg>
                        <select
                            v-model="vlmModel"
                            :disabled="isLoadingVLMModels || vlmModels.length === 0"
                            class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition disabled:bg-gray-100"
                            @change="resetVLMModelTest"
                        >
                          <option disabled value="">
                            {{
                              isLoadingVLMModels
                                  ? 'Loading models...'
                                  : vlmModels.length === 0
                                      ? 'No models available'
                                      : 'Select a model'
                            }}
                          </option>
                          <option v-for="model in vlmModels" :key="model" :value="model">
                            {{ model }}
                          </option>
                        </select>
                        <button v-if="!isLoadingVLMModels"
                                class="inline-flex items-center px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 ml-1"
                                title="Reload models"
                                type="button"
                                @click="loadVLMModels">
                          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                          </svg>
                        </button>
                      </div>
                      <div v-if="vlmModelError" class="text-xs text-red-500 mt-1 flex items-center gap-1">
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"
                                stroke-width="2"/>
                        </svg>
                        {{ vlmModelError }}
                      </div>
                      <div v-if="vlmModel && !vlmModelError" class="text-xs text-gray-500 mt-1">
                <span>
                  Selected: <span class="font-semibold text-blue-700">{{ vlmModel }}</span>
                </span>
                      </div>
                    </div>

                    <!-- Step 4: Test Model -->
                    <div>
                      <div class="mb-2 text-sm font-medium text-gray-700 flex items-center gap-2">
                        <span class="rounded bg-blue-200 text-blue-900 px-2 py-0.5 text-xs font-semibold">Step 3</span>
                        Test Model Compatibility
                      </div>
                      <div class="flex gap-2 items-center">
                        <button
                            :disabled="!vlmModel || isTestingVLMModel"
                            class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md font-semibold text-sm hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition"
                            type="button"
                            @click="testVLMModel"
                        >
                          <svg v-if="isTestingVLMModel" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                    stroke-width="4"></circle>
                            <path class="opacity-75"
                                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                  fill="currentColor"></path>
                          </svg>
                          <span>{{ isTestingVLMModel ? 'Testing...' : 'Test Model' }}</span>
                        </button>
                        <div>
                  <span v-if="vlmModelTestStatus.type === 'success'"
                        class="text-green-700 font-semibold flex items-center gap-1">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                    </svg>
                    {{ vlmModelTestStatus.message }}
                  </span>
                          <span v-else-if="vlmModelTestStatus.type === 'error'"
                                class="text-red-600 flex items-center gap-1">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                    </svg>
                    {{ vlmModelTestStatus.message }}
                  </span>
                          <span v-else-if="vlmModelTestStatus.type === 'warning'"
                                class="text-yellow-700 flex items-center gap-1">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                      <path d="M12 8v4m0 4h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                    </svg>
                    {{ vlmModelTestStatus.message }}
                  </span>
                        </div>
                      </div>
                      <div v-if="vlmModelTested && vlmModelValid" class="mt-3">
                        <div class="flex gap-2 items-center">
                  <span
                      class="px-3 py-1 rounded-lg bg-blue-100 text-blue-700 text-xs font-medium flex items-center gap-1">
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round"
                            stroke-width="2"/>
                      <path
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                    </svg>
                    Ready to use!
                  </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <!-- End VLM Model Stepper Card -->

                <div class="grid md:grid-cols-2 gap-6 mt-6">
                  <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">VLM Prompt (optional)</label>
                    <textarea
                        v-model="customSettings.vlm_prompt"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        placeholder="Describe how the VLM should process and explain images, etc"
                        rows="2"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">Max Image Dimension (pixels)</label>
                    <input
                        v-model.number="customSettings.max_image_dim"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        max="2048"
                        min="400"
                        placeholder="e.g. 800"
                        step="100"
                        type="number"
                    />
                    <p class="mt-1 text-xs text-gray-500">Images will be scaled down to this dimension before VLM
                      analysis.</p>
                  </div>
                </div>
              </div>
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

    <ConfirmationDialog
      v-if="showCancelDialog"
      :open="showCancelDialog"
      title="Cancel Preprocessing Task"
      :message="cancelDeleteMode
          ? 'Are you sure you want to cancel and DELETE already processed files? This cannot be undone.'
          : 'Do you want to keep already processed files when cancelling this task?'
        "
      :confirmText="cancelDeleteMode ? 'Delete Processed and Cancel' : 'Keep Processed and Cancel'"
      :cancelText="cancelDeleteMode ? 'Back' : 'Delete Processed'"
      :confirmVariant="cancelDeleteMode ? 'danger' : 'primary'"
      @confirm="() => doCancelTask(cancelTaskPending, !cancelDeleteMode)"
      @cancel="handleCancelDialogSecondary"
    />
  </div>
</template>

<script setup>
import {computed, onMounted, onUnmounted, ref, watch} from 'vue';
import {api} from '@/services/api';
import {useAuthStore} from '@/stores/auth'
import {useToast} from 'vue-toastification';
import Multiselect from '@vueform/multiselect';

import TaskCard from './preprocessing/TaskCard.vue';
import FileSelector from './preprocessing/FileSelector.vue';
import ConfigurationManager from './preprocessing/ConfigurationManager.vue';
import TaskDetailsModal from './preprocessing/TaskDetailsModal.vue';
import ConfirmationDialog from "@/components/ConfirmationDialog.vue";

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
const showCancelDialog = ref(false);
const cancelTaskPending = ref(null);
const cancelDeleteMode = ref(false);
const isSubmitting = ref(false);
const saveAsConfig = ref(false);
const configName = ref('');
let pollInterval = null;
const showAllCompleted = ref(false);
const showApiSettings = ref(false);
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)
const bypassCelery = ref(false);

// New state for preprocessing modes
const selectedMode = ref('quick');
const selectedConfig = ref('quick'); // Keep for saved configs
const selectedSavedConfig = ref('');

const customSettings = ref({
  mode: 'fast',
  ocr_engine: 'ocrmypdf',
  docling_ocr_engine: 'rapidocr',
  force_ocr: false,
  ocr_languages: [{value: 'eng', label: 'English'}],
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

const presetName = ref('');
const presetDescription = ref('');
const isSavingPreset = ref(false);
const isUpdatingPreset = ref(false);

const showCustomVLMSettings = ref(false);
const vlmApiKey = ref('');
const vlmBaseUrl = ref('');
const vlmModel = ref('');
const vlmModels = ref([]);
const isLoadingVLMModels = ref(false);
const vlmModelError = ref('');
const isTestingVLMModel = ref(false);
const vlmModelTested = ref(false);
const vlmModelValid = ref(false);
const vlmModelTestError = ref('');
const vlmModelTestStatus = computed(() => {
  if (isTestingVLMModel.value) {
    return {type: 'loading', message: 'Testing model...'};
  }
  if (!vlmModelTested.value) {
    return {type: 'warning', message: 'You must test the selected model before processing.'};
  }
  if (vlmModelValid.value) {
    return {type: 'success', message: 'Model is compatible and supports vision input.'};
  }
  if (vlmModelTestError.value) {
    return {type: 'error', message: vlmModelTestError.value};
  }
  return {type: 'none', message: ''};
});

const showCancelTaskDialog = (task) => {
  cancelTaskPending.value = task;
  cancelDeleteMode.value = false; // default to "keep"
  showCancelDialog.value = true;
};


const saveAsPreset = async () => {
  if (!presetName.value || isSavingPreset.value) return;
  isSavingPreset.value = true;
  try {
    const configPayload = {
      name: presetName.value,
      description: presetDescription.value,
      file_type: 'mixed',
      pdf_backend: 'pymupdf4llm',
      ocr_backend: customSettings.value.ocr_engine,
      use_ocr: true,
      force_ocr: customSettings.value.force_ocr,
      ocr_languages: (customSettings.value.ocr_languages || []).map(lang =>
        typeof lang === 'string' ? lang : lang.value
      ),
      additional_settings: { ...customSettings.value }
    };
    const response = await api.post(`/project/${props.projectId}/preprocessing-config`, configPayload);
    await fetchConfigurations();
    selectedSavedConfig.value = response.data.id;
    presetName.value = '';
    presetDescription.value = '';
    toast.success('Preset saved!');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to save preset');
  } finally {
    isSavingPreset.value = false;
  }
};

const updatePreset = async () => {
  if (!presetName.value || !selectedSavedConfig.value || isUpdatingPreset.value) return;
  isUpdatingPreset.value = true;
  try {
    const configPayload = {
      name: presetName.value,
      description: presetDescription.value,
      file_type: 'mixed',
      pdf_backend: 'pymupdf4llm',
      ocr_backend: customSettings.value.ocr_engine,
      use_ocr: true,
      force_ocr: customSettings.value.force_ocr,
      ocr_languages: (customSettings.value.ocr_languages || []).map(lang =>
        typeof lang === 'string' ? lang : lang.value
      ),
      additional_settings: { ...customSettings.value }
    };
    await api.put(`/project/${props.projectId}/preprocessing-config/${selectedSavedConfig.value}`, configPayload);
    await fetchConfigurations();
    toast.success('Preset updated!');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update preset');
  } finally {
    isUpdatingPreset.value = false;
  }
};


watch(selectedSavedConfig, id => {
  // Populate fields when user picks a config
  if (!id) {
    presetName.value = '';
    presetDescription.value = '';
    return;
  }
  const config = savedConfigs.value.find(c => c.id === id);
  if (config) {
    presetName.value = config.name || '';
    presetDescription.value = config.description || '';
  }
});



const loadVLMModels = async () => {
  isLoadingVLMModels.value = true;
  vlmModels.value = [];
  vlmModelError.value = '';
  try {
    const res = await api.get(`/project/llm/models`, {
      params: {
        api_key: vlmApiKey.value || undefined,
        base_url: vlmBaseUrl.value || undefined
      }
    });
    if (res.data.success && Array.isArray(res.data.models)) {
      vlmModels.value = res.data.models;
      if (!vlmModels.value.includes(vlmModel.value)) {
        vlmModel.value = '';
      }
    } else {
      vlmModelError.value = res.data.message || 'No models available';
      vlmModels.value = [];
      vlmModel.value = '';
    }
  } catch (e) {
    vlmModelError.value = e.response?.data?.message || 'Failed to load models.';
    vlmModels.value = [];
    vlmModel.value = '';
  } finally {
    isLoadingVLMModels.value = false;
  }
};



// Watch for API settings changes and reload model list (debounced)
let vlmModelDebounce = null;
watch([showCustomVLMSettings, vlmApiKey, vlmBaseUrl], () => {
  clearTimeout(vlmModelDebounce);
  vlmModelDebounce = setTimeout(() => {
    loadVLMModels();
    resetVLMModelTest();
  }, 600);
}, {immediate: true});

// When the model changes, user must re-test
const resetVLMModelTest = () => {
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
};

// Test selected VLM model for compatibility/support
const testVLMModel = async () => {
  if (!vlmModel.value) return;
  isTestingVLMModel.value = true;
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
  try {
    const res = await api.get(`/project/llm/test-vlm-image-support`, {
      params: {
        model: vlmModel.value,
        api_key: vlmApiKey.value || undefined,
        base_url: vlmBaseUrl.value || undefined
      }
    });

    if (res.data.supported) {
      vlmModelTested.value = true;
      vlmModelValid.value = true;
      vlmModelTestError.value = '';
    } else {
      vlmModelTested.value = true;
      vlmModelValid.value = false;
      vlmModelTestError.value = res.data.message || 'Model does not support image input.';
    }
  } catch (e) {
    vlmModelTested.value = true;
    vlmModelValid.value = false;
    vlmModelTestError.value = e.response?.data?.message || 'Test failed.';
  } finally {
    isTestingVLMModel.value = false;
  }
};

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
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
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

  if (selectedMode.value === 'saved') {
    return !!selectedSavedConfig.value;
  }

  if (selectedMode.value === 'custom') {
    if (
        customSettings.value.mode === 'advanced' &&
        customSettings.value.use_vlm &&
        !customSettings.value.use_local_vlm
    ) {
      // Remote VLM
      return !!vlmModel.value && vlmModelTested.value && vlmModelValid.value;
    }
    // Custom, but not VLM: can always proceed
    return true;
  }

  // Quick/better always possible if files selected
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
      ocr_languages: [{value: 'eng', label: 'English'}],
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
              ? ocrLanguagesForSelect.value.find(l => l.value === lang) || {value: lang, label: lang}
              : lang
      ) || [{value: 'eng', label: 'English'}]
    };
  }

  // Clear VLM test result when loading new config
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
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
      if (isAdmin.value && bypassCelery.value) {
        config.bypass_celery = true;
      }


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

function handleCancelDialogSecondary() {
  // If already on "delete" mode, just close
  if (cancelDeleteMode.value) {
    showCancelDialog.value = false;
    cancelTaskPending.value = null;
    cancelDeleteMode.value = false;
  } else {
    // Switch to "delete mode"
    cancelDeleteMode.value = true;
  }
}


const doCancelTask = async (task, keepProcessed) => {
  showCancelDialog.value = false;
  cancelDeleteMode.value = false;
  if (!task) return;
  try {
    await api.post(`/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=${!!keepProcessed}`);
    toast.success('Task cancelled');
    fetchPreprocessingTasks();
  } catch (error) {
    toast.error('Failed to cancel task');
  } finally {
    cancelTaskPending.value = null;
  }
};


const cancelTask = async (task, done) => {
  try {
    const keepProcessed = await confirm('Keep already processed files?');
    await api.post(`/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=${keepProcessed}`);
    toast.success('Task cancelled');
    fetchPreprocessingTasks();
  } catch (error) {
    toast.error('Failed to cancel task');
  } finally {
    if (done) done(); // Resets button
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
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
  showApiSettings.value = false;
  customSettings.value = {
    mode: 'fast',
    ocr_engine: 'ocrmypdf',
    docling_ocr_engine: 'rapidocr',
    force_ocr: false,
    ocr_languages: [{value: 'eng', label: 'English'}],
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
  bypassCelery.value = false;
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
              ? ocrLanguagesForSelect.value.find(l => l.value === lang) || {value: lang, label: lang}
              : lang
      ) || [{value: 'eng', label: 'English'}]
    };
  }

  customSettings.value.force_ocr = config.force_ocr || false;

  showConfigManager.value = false;
};

watch([
  () => customSettings.value.vlm_model,
  () => customSettings.value.vlm_custom_model,
  () => customSettings.value.vlm_base_url,
  () => vlmApiKey.value
], () => {
  vlmModelTested.value = false;
  vlmModelValid.value = false;
  vlmModelTestError.value = '';
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
}, {immediate: true});

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