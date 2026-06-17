<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Files & Preprocessing</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload files and run OCR preprocessing
        </p>
      </div>
      <div class="flex items-center space-x-3">
        <button
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-slate-800 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
          @click="showUploadModal = true"
        >
          <svg
            class="w-5 h-5 mr-2 text-gray-500 dark:text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m4-3L4 16m0 0l8-8m0 0l8 8"
            />
          </svg>
          Upload Files
        </button>
      </div>
    </div>

    <!-- Upload Zone -->
    <div
      v-if="!files.length"
      class="border-2 border-dashed border-gray-300 dark:border-slate-600 rounded-xl p-12 text-center hover:border-blue-400 dark:hover:border-blue-500 transition-colors bg-gray-50 dark:bg-slate-800/50"
      :class="{ 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-slate-800': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m0-3v12"
        />
      </svg>
      <p class="mt-4 text-lg font-medium text-gray-900 dark:text-white">
        Drop files here or click to upload
      </p>
      <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
        PDF, PNG, JPG, DOCX, CSV, XLSX, TXT
      </p>
      <button
        class="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        @click="$refs.fileInput.click()"
      >
        Browse Files
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.docx,.csv,.xlsx,.txt"
        class="hidden"
        @change="handleFileSelect"
      />
    </div>

    <!-- Filters & Search -->
    <div v-else class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-3 flex-1">
        <div class="relative flex-1 max-w-md">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
          />
          <svg
            class="absolute left-3 top-2.5 h-5 w-5 text-gray-400 dark:text-gray-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <select
          v-model="filterStatus"
          class="px-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
        >
          <option value="">All Files</option>
          <option value="not_preprocessed">Not processed</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>
      <div class="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="showUnprocessedOnly" type="checkbox" class="rounded text-blue-600" />
          <span>Show only unprocessed</span>
        </label>
        <span class="text-gray-400 dark:text-gray-500">|</span>
        <span>{{ pagination.total }} files total</span>
      </div>
    </div>

    <!-- Loading Indicator -->
    <div v-if="isLoading" class="flex justify-center py-12">
      <LoadingSpinner size="large" />
    </div>

    <!-- Files Table -->
    <FilesTable
      v-else-if="files.length"
      :files="displayFiles"
      :selected-files="selectedFiles"
      :sort-by="sortBy"
      :sort-order="sortOrder"
      :pagination="pagination"
      @toggle-selection="toggleSelection"
      @toggle-all="toggleSelectAll"
      @preview="previewFile"
      @download="downloadFile"
      @delete="confirmDeleteFile"
      @configure-import="openImportConfigModal"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      @sort="handleSort"
      @view-history="handleViewHistory"
      @select-all-files="selectAllFiles"
      @clear-selection="clearSelection"
    />

    <!-- Slide-in Preprocessing History Panel -->
    <Teleport to="body">
      <div
        v-if="showHistoryPanel"
        class="fixed inset-0 z-50 overflow-hidden bg-black/30 backdrop-blur-md transition-opacity"
        @click="showHistoryPanel = false"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0"></div>

        <!-- Panel -->
        <div class="absolute inset-0 flex justify-end">
          <div class="w-screen max-w-md panel-slide-enter">
            <div class="h-full flex flex-col bg-white shadow-xl" @click.stop>
              <!-- Panel Header -->
              <div
                class="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50"
              >
                <div class="min-w-0">
                  <h3 class="text-lg font-semibold text-gray-900">Preprocessing History</h3>
                  <p v-if="historyFile" class="text-sm text-gray-500 truncate mt-0.5">
                    {{ historyFile.file_name }}
                  </p>
                </div>
                <button
                  class="text-gray-400 hover:text-gray-600 transition-colors"
                  @click="showHistoryPanel = false"
                >
                  <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <!-- Panel Content -->
              <div class="flex-1 overflow-y-auto p-6">
                <!-- Preprocessing Runs (Accordion) -->
                <div v-if="historyFile?.preprocessing_tasks?.length" class="space-y-3">
                  <div
                    v-for="task in historyFile.preprocessing_tasks"
                    :key="task.id"
                    :class="[
                      'bg-white rounded-lg border transition-all overflow-hidden',
                      expandedTasks.has(task.id)
                        ? 'border-blue-300 shadow-md'
                        : 'border-gray-200 hover:border-blue-300',
                    ]"
                  >
                    <!-- Accordion Header (clickable) -->
                    <div
                      class="px-4 py-3 cursor-pointer flex items-center justify-between bg-gradient-to-r from-gray-50 to-white"
                      @click="toggleTaskAccordion(task.id)"
                    >
                      <div class="flex items-center gap-3 flex-1 min-w-0">
                        <!-- Status indicator -->
                        <span
                          :class="[
                            'w-2.5 h-2.5 rounded-full flex-shrink-0',
                            isTaskStatus(task, 'completed')
                              ? 'bg-green-500'
                              : isTaskStatus(task, 'processing') ||
                                  isTaskStatus(task, 'in_progress')
                                ? 'bg-blue-500 animate-pulse'
                                : isTaskStatus(task, 'failed')
                                  ? 'bg-red-500'
                                  : isTaskStatus(task, 'cancelled')
                                    ? 'bg-yellow-500'
                                    : 'bg-gray-400',
                          ]"
                        />
                        <!-- Task info -->
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2">
                            <p class="text-sm font-medium text-gray-900 truncate">
                              Run #{{ task.id }} • {{ getEngineName(task) }}
                            </p>
                            <!-- Expand/collapse chevron -->
                            <svg
                              :class="[
                                'w-4 h-4 text-gray-400 transition-transform flex-shrink-0',
                                expandedTasks.has(task.id) ? 'rotate-90' : '',
                              ]"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M9 5l7 7-7 7"
                              />
                            </svg>
                          </div>
                          <p class="text-xs text-gray-500 mt-0.5 truncate">
                            {{ formatRelativeTime(task.created_at) }}
                            <span v-if="task.completed_at">
                              • {{ formatRelativeTime(task.completed_at) }}
                            </span>
                          </p>
                        </div>
                      </div>
                      <!-- Mini status badge -->
                      <span
                        :class="[
                          'inline-flex items-center px-2 py-1 rounded text-xs font-medium flex-shrink-0 ml-2',
                          isTaskStatus(task, 'completed')
                            ? 'bg-green-100 text-green-700'
                            : isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')
                              ? 'bg-blue-100 text-blue-700'
                              : isTaskStatus(task, 'failed')
                                ? 'bg-red-100 text-red-700'
                                : isTaskStatus(task, 'cancelled')
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-gray-100 text-gray-700',
                        ]"
                      >
                        {{
                          isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')
                            ? `${Math.round(task.meta?.progress || 0)}%`
                            : isTaskStatus(task, 'completed')
                              ? 'Done'
                              : isTaskStatus(task, 'failed')
                                ? 'Failed'
                                : isTaskStatus(task, 'cancelled')
                                  ? 'Cancelled'
                                  : 'Pending'
                        }}
                      </span>
                    </div>

                    <!-- Accordion Content (expanded) -->
                    <div
                      v-show="expandedTasks.has(task.id)"
                      class="border-t border-gray-200 bg-gray-50 px-4 py-3 space-y-3"
                    >
                      <!-- Progress bar for active tasks -->
                      <div
                        v-if="isTaskStatus(task, 'processing') || isTaskStatus(task, 'in_progress')"
                        class="space-y-1"
                      >
                        <div class="flex items-center justify-between text-xs text-gray-600">
                          <span>Processing...</span>
                          <span v-if="task.meta?.eta_seconds > 0" class="text-gray-500">
                            ≈ {{ prettyEta(task.meta.eta_seconds) }} left
                          </span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div
                            :style="{
                              width: `${Math.min((task.processed_files / task.total_files) * 100, 100)}%`,
                            }"
                            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          />
                        </div>
                        <p class="text-xs text-gray-500">
                          {{ task.processed_files }} of {{ task.total_files }} files processed
                          <span v-if="task.failed_files > 0" class="text-red-600">
                            • {{ task.failed_files }} failed
                          </span>
                        </p>
                      </div>

                      <!-- File task details -->
                      <div class="space-y-2">
                        <template v-if="task.file_tasks && task.file_tasks.length > 0">
                          <div
                            v-for="fileTask in task.file_tasks"
                            :key="fileTask.id"
                            :class="[
                              'rounded-md border p-2 text-sm',
                              fileTask.status === 'completed'
                                ? 'bg-green-50 border-green-200'
                                : fileTask.status === 'failed'
                                  ? 'bg-red-50 border-red-200'
                                  : fileTask.status === 'cancelled'
                                    ? 'bg-yellow-50 border-yellow-200'
                                    : 'bg-gray-50 border-gray-200',
                            ]"
                          >
                            <!-- File task header -->
                            <div class="flex items-start justify-between gap-2">
                              <div class="flex items-center gap-2 flex-1 min-w-0">
                                <!-- Status icon -->
                                <svg
                                  v-if="fileTask.status === 'completed'"
                                  class="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M5 13l4 4L19 7"
                                  />
                                </svg>
                                <svg
                                  v-else-if="fileTask.status === 'failed'"
                                  class="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M6 18L18 6M6 6l12 12"
                                  />
                                </svg>
                                <svg
                                  v-else-if="fileTask.status === 'cancelled'"
                                  class="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <circle
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  />
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M12 9v2m0 4h.01"
                                  />
                                </svg>
                                <svg
                                  v-else
                                  class="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                                  />
                                </svg>
                                <span class="font-medium text-gray-900 truncate">
                                  {{ fileTask.file_name || 'Unknown file' }}
                                </span>
                              </div>
                              <!-- Processing time -->
                              <span
                                v-if="fileTask.processing_time"
                                class="text-xs text-gray-500 whitespace-nowrap"
                              >
                                {{ formatProcessingTime(fileTask.processing_time) }}
                              </span>
                            </div>

                            <!-- Error message (nested accordion) -->
                            <div
                              v-if="fileTask.status === 'failed' && fileTask.error_message"
                              class="mt-2"
                            >
                              <details class="group">
                                <summary
                                  class="text-xs text-red-700 cursor-pointer hover:text-red-900 flex items-center gap-1"
                                >
                                  <svg
                                    class="w-3 h-3 transition-transform group-open:rotate-90"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      stroke-width="2"
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                  View error
                                </summary>
                                <p class="mt-1 text-xs text-red-600 bg-red-100 rounded p-2">
                                  {{ fileTask.error_message }}
                                </p>
                              </details>
                            </div>

                            <!-- Warnings (nested accordion for skipped rows) -->
                            <div
                              v-if="
                                fileTask.warnings &&
                                (fileTask.warnings.messages || fileTask.warnings.skipped_rows)
                              "
                              class="mt-2"
                            >
                              <details class="group">
                                <summary
                                  class="text-xs text-amber-700 cursor-pointer hover:text-amber-900 flex items-center gap-1"
                                >
                                  <svg
                                    class="w-3 h-3 transition-transform group-open:rotate-90"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      stroke-linecap="round"
                                      stroke-linejoin="round"
                                      stroke-width="2"
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                  ⚠ {{ fileTask.warnings.skipped_rows?.count || 0 }} skipped rows
                                </summary>
                                <div
                                  class="mt-1 text-xs text-amber-600 bg-amber-100 rounded p-2 max-h-32 overflow-y-auto"
                                >
                                  <div
                                    v-if="fileTask.warnings.skipped_rows?.details"
                                    class="space-y-1"
                                  >
                                    <div
                                      v-for="(
                                        row, idx
                                      ) in fileTask.warnings.skipped_rows.details.slice(0, 10)"
                                      :key="idx"
                                      class="flex justify-between"
                                    >
                                      <span>Row {{ row.row_index }}</span>
                                      <span class="truncate max-w-[150px]">{{ row.reason }}</span>
                                    </div>
                                    <p
                                      v-if="fileTask.warnings.skipped_rows.details.length > 10"
                                      class="text-amber-500"
                                    >
                                      ...and
                                      {{ fileTask.warnings.skipped_rows.details.length - 10 }} more
                                    </p>
                                  </div>
                                  <div v-else>
                                    <p v-for="(msg, idx) in fileTask.warnings.messages" :key="idx">
                                      {{ msg }}
                                    </p>
                                  </div>
                                </div>
                              </details>
                            </div>

                            <!-- Document link for completed tasks -->
                            <div
                              v-if="
                                fileTask.status === 'completed' &&
                                fileTask.document_ids &&
                                fileTask.document_ids.length > 0
                              "
                              class="mt-2 flex items-center justify-between"
                            >
                              <span class="text-xs text-green-700">
                                ✓ {{ fileTask.document_ids.length }} document{{
                                  fileTask.document_ids.length !== 1 ? 's' : ''
                                }}
                              </span>
                              <button
                                v-if="fileTask.document_ids.length === 1"
                                class="text-xs text-blue-600 hover:text-blue-800 font-medium underline flex items-center gap-1"
                                @click.stop="navigateToDocument(fileTask.document_ids[0])"
                              >
                                <svg
                                  class="w-3 h-3"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                  />
                                </svg>
                                Go to Document
                              </button>
                              <button
                                v-else
                                class="text-xs text-blue-600 hover:text-blue-800 font-medium underline flex items-center gap-1"
                                @click.stop="navigateToDocument(fileTask.document_ids[0])"
                              >
                                <svg
                                  class="w-3 h-3"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                  />
                                </svg>
                                Go to Documents ({{ fileTask.document_ids.length }})
                              </button>
                            </div>
                          </div>
                        </template>
                        <div v-else class="text-center text-gray-400 py-4 text-sm">
                          No file tasks recorded
                        </div>
                      </div>

                      <!-- Task-level error message -->
                      <div
                        v-if="task.message && isTaskStatus(task, 'failed')"
                        class="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700"
                      >
                        {{ task.message }}
                      </div>

                      <!-- Actions -->
                      <div
                        class="flex items-center justify-end gap-2 pt-2 border-t border-gray-200"
                      >
                        <button
                          v-if="isTaskStatus(task, 'failed')"
                          class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                          @click.stop="retryFailedFiles(task.id)"
                        >
                          Retry failed files
                        </button>
                        <button
                          v-if="
                            isTaskStatus(task, 'processing') ||
                            isTaskStatus(task, 'pending') ||
                            isTaskStatus(task, 'in_progress')
                          "
                          class="text-xs text-red-600 hover:text-red-800 font-medium flex items-center gap-1"
                          @click.stop="cancelPreprocessingTask(task)"
                        >
                          <svg
                            class="w-3 h-3"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                          Cancel
                        </button>
                        <button
                          class="text-xs text-gray-600 hover:text-gray-800"
                          @click.stop="toggleTaskAccordion(task.id)"
                        >
                          Close
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- No Runs Yet -->
                <div v-else class="text-center py-12">
                  <svg
                    class="mx-auto h-12 w-12 text-gray-300"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p class="mt-4 text-sm text-gray-500">No preprocessing runs yet</p>
                  <button
                    v-if="historyFile"
                    class="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                    @click="processFileAndClose(historyFile)"
                  >
                    🚀 Process this file
                  </button>
                </div>
              </div>

              <!-- Panel Footer -->
              <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
                <div class="flex items-center justify-between">
                  <button
                    v-if="historyFile"
                    class="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    @click="processFileAndClosePanel(historyFile)"
                  >
                    + Run new preprocessing
                  </button>
                  <button
                    class="ml-auto px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                    @click="showHistoryPanel = false"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Empty State -->
    <div v-if="!files.length && !isDragging" class="text-center py-12">
      <svg
        class="mx-auto h-16 w-16 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <p class="mt-4 text-lg text-gray-500">No files uploaded yet</p>
      <p class="mt-2 text-sm text-gray-400">Upload files to get started with preprocessing</p>
    </div>

    <!-- Floating Batch Toolbar -->
    <div
      v-if="selectedFiles.length > 0"
      class="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-50"
    >
      <div
        class="bg-gray-900 text-white rounded-xl shadow-2xl px-6 py-3 flex items-center space-x-4"
      >
        <span class="font-medium"
          >{{ selectedFiles.length }} file{{ selectedFiles.length !== 1 ? 's' : '' }} selected</span
        >
        <!-- Warning indicator for unconfigured CSV/XLSX -->
        <span
          v-if="unconfiguredCsvXlsxFiles.length > 0"
          class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500 text-white"
          :title="
            unconfiguredCsvXlsxFiles.map((f) => f.file_name).join(', ') +
            ' need(s) import configuration'
          "
        >
          <svg class="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          {{ unconfiguredCsvXlsxFiles.length }} needs config
        </span>
        <button
          class="text-sm text-gray-300 hover:text-white underline"
          @click="selectedFiles = []"
        >
          Clear
        </button>
        <div class="w-px h-5 bg-gray-700" />
        <button
          :disabled="unconfiguredCsvXlsxFiles.length > 0"
          :class="[
            'inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            unconfiguredCsvXlsxFiles.length > 0
              ? 'bg-gray-600 cursor-not-allowed opacity-75'
              : 'bg-blue-600 hover:bg-blue-700',
          ]"
          @click="openProcessingPanel"
        >
          <svg
            v-if="unconfiguredCsvXlsxFiles.length === 0"
            class="w-4 h-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <svg v-else class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          {{
            unconfiguredCsvXlsxFiles.length > 0
              ? 'Configure Files First'
              : 'Configure Preprocessing'
          }}
        </button>
      </div>
    </div>

    <!-- Slide-in Preprocessing Panel -->
    <Teleport to="body">
      <div
        v-if="showProcessingPanel"
        class="fixed inset-0 z-50 overflow-hidden bg-black/30 backdrop-blur-md transition-opacity"
        @click="showProcessingPanel = false"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0"></div>

        <!-- Panel -->
        <div class="absolute inset-0 flex justify-end">
          <div class="w-screen max-w-md panel-slide-enter">
            <div class="h-full flex flex-col bg-white shadow-xl" @click.stop>
              <!-- Panel Header -->
              <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900">Configure Preprocessing</h3>
                <button
                  class="text-gray-400 hover:text-gray-600"
                  @click="showProcessingPanel = false"
                >
                  <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <!-- Panel Content -->
              <div class="flex-1 overflow-y-auto p-6 space-y-6">
                <!-- Selected Files -->
                <div>
                  <h4 class="text-sm font-medium text-gray-700 mb-3">
                    Files to Process ({{ selectedFiles.length }})
                  </h4>
                  <div
                    class="space-y-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3"
                  >
                    <div
                      v-for="fileId in selectedFiles"
                      :key="fileId"
                      class="flex items-center justify-between text-sm"
                    >
                      <span class="truncate">{{
                        getFileById(fileId)?.file_name || 'Unknown'
                      }}</span>
                      <button
                        class="text-gray-400 hover:text-red-500"
                        @click="toggleSelection(fileId)"
                      >
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <button
                    class="mt-2 text-xs text-blue-600 hover:text-blue-800 font-medium"
                    @click="
                      () => {
                        selectedFiles = []
                        showProcessingPanel = false
                      }
                    "
                  >
                    Select different files
                  </button>
                </div>

                <!-- OCR Engine Selection -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-3"> OCR Engine </label>
                  <div class="space-y-3">
                    <!-- Local OCR -->
                    <button
                      v-if="doclingOcrEnabled"
                      :class="[
                        'w-full rounded-lg border-2 p-4 text-left transition-all',
                        selectedEngine === 'docling_tesseract'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300',
                      ]"
                      @click="selectedEngine = 'docling_tesseract'"
                    >
                      <div class="flex items-center">
                        <svg
                          class="w-6 h-6 text-blue-600 mr-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                          />
                        </svg>
                        <div>
                          <p class="font-medium text-gray-900">
                            {{ getEngineLabel('docling_tesseract') }}
                          </p>
                          <p class="text-xs text-gray-500">
                            {{ getEngineSubtitle('docling_tesseract') }}
                          </p>
                        </div>
                      </div>
                    </button>

                    <!-- Mistral OCR -->
                    <button
                      v-if="mistralOcrEnabled"
                      :class="[
                        'w-full rounded-lg border-2 p-4 text-left transition-all',
                        selectedEngine === 'mistral_ocr'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300',
                      ]"
                      @click="selectedEngine = 'mistral_ocr'"
                    >
                      <div class="flex items-center">
                        <svg
                          class="w-6 h-6 text-blue-600 mr-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        <div>
                          <p class="font-medium text-gray-900">
                            {{ getEngineLabel('mistral_ocr') }}
                          </p>
                          <p class="text-xs text-gray-500">
                            {{ getEngineSubtitle('mistral_ocr') }}
                          </p>
                        </div>
                      </div>
                    </button>

                    <!-- Vision LLM -->
                    <button
                      v-if="visionOcrEnabled"
                      :class="[
                        'w-full rounded-lg border-2 p-4 text-left transition-all',
                        selectedEngine === 'llm_vision'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300',
                      ]"
                      @click="selectedEngine = 'llm_vision'"
                    >
                      <div class="flex items-center">
                        <svg
                          class="w-6 h-6 text-blue-600 mr-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          />
                        </svg>
                        <div>
                          <p class="font-medium text-gray-900">
                            {{ getEngineLabel('llm_vision') }}
                          </p>
                          <p class="text-xs text-gray-500">{{ getEngineSubtitle('llm_vision') }}</p>
                        </div>
                      </div>
                    </button>
                  </div>
                  <!-- Warning: No OCR engines enabled -->
                  <div
                    v-if="noOcrEnabled"
                    class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                  >
                    <p class="text-sm font-medium text-amber-900">
                      ⚠️ All OCR engines are disabled. Only PDFs with embedded text can be
                      processed.
                    </p>
                    <p class="text-xs text-amber-700 mt-1">
                      Image files (PNG/JPEG) require OCR. Enable Local OCR, Mistral OCR, or Vision
                      LLM in Admin Settings to process images. PDFs will use pypdf for embedded text
                      extraction.
                    </p>
                  </div>
                </div>

                <!-- Force OCR (always visible) -->
                <div class="border-t border-gray-200 pt-4">
                  <label
                    class="flex items-start space-x-3 p-3 bg-amber-50 rounded-lg border border-amber-200"
                  >
                    <input
                      v-model="forceOcr"
                      type="checkbox"
                      class="mt-0.5 text-amber-600 rounded"
                    />
                    <div>
                      <p class="text-sm font-medium text-amber-900">Force OCR for PDFs</p>
                      <p class="text-xs text-amber-700 mt-1">
                        Skip embedded text extraction and run OCR on all PDF pages
                      </p>
                    </div>
                  </label>
                </div>

                <!-- Vision LLM Prompt (always visible when using Vision LLM) -->
                <div v-if="selectedEngine === 'llm_vision'" class="pt-4">
                  <label class="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
                  <textarea
                    v-model="visionPrompt"
                    rows="2"
                    placeholder="Extract all text as markdown..."
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  ></textarea>
                </div>

                <!-- Advanced Options -->
                <div class="border-t border-gray-200 pt-4">
                  <button
                    class="text-sm font-medium text-gray-700 flex items-center"
                    @click="showAdvanced = !showAdvanced"
                  >
                    <svg
                      :class="[
                        'w-4 h-4 mr-2 transition-transform',
                        showAdvanced ? 'rotate-90' : '',
                      ]"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                    Advanced Options
                  </button>

                  <div v-show="showAdvanced" class="mt-4 space-y-4">
                    <!-- Tesseract Language -->
                    <div v-if="selectedEngine === 'docling_tesseract'">
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Tesseract Language
                      </label>
                      <select
                        v-model="tesseractLang"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="auto">Auto-detect</option>
                        <option value="eng">English</option>
                        <option value="deu">German</option>
                        <option value="fra">French</option>
                        <option value="spa">Spanish</option>
                        <option value="ita">Italian</option>
                        <option value="por">Portuguese</option>
                        <option value="nld">Dutch</option>
                        <option value="pol">Polish</option>
                        <option value="rus">Russian</option>
                        <option value="chi-sim">Chinese (Simplified)</option>
                        <option value="lat">Latin</option>
                      </select>
                    </div>

                    <!-- Mistral Settings -->
                    <div v-if="selectedEngine === 'mistral_ocr'" class="space-y-3">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input
                          v-model="mistralApiKey"
                          type="text"
                          placeholder="Leave empty to use server default"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                        <input
                          v-model="mistralModel"
                          type="text"
                          placeholder="mistral-ocr-latest"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>

                    <!-- Vision LLM Advanced Settings -->
                    <div v-if="selectedEngine === 'llm_vision'" class="space-y-3">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                        <input
                          v-model="visionApiKey"
                          type="text"
                          placeholder="Leave empty to use server default"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                        <input
                          v-model="visionBaseUrl"
                          type="text"
                          placeholder="https://api.openai.com/v1"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Model</label>
                        <input
                          v-model="visionModel"
                          type="text"
                          placeholder="Leave empty to use server default"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                          Max Image Dimension (px)
                        </label>
                        <input
                          v-model.number="visionMaxImageDim"
                          type="number"
                          min="400"
                          max="4096"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Panel Footer -->
              <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
                <!-- Warning for unconfigured CSV/XLSX files -->
                <div
                  v-if="unconfiguredCsvXlsxFiles.length > 0"
                  class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg"
                >
                  <div class="flex items-start gap-2">
                    <svg
                      class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                      />
                    </svg>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-amber-900">
                        {{ unconfiguredCsvXlsxFiles.length }} file(s) need import configuration
                      </p>
                      <ul class="mt-1 text-xs text-amber-700 list-disc list-inside">
                        <li
                          v-for="file in unconfiguredCsvXlsxFiles"
                          :key="file.id"
                          class="truncate"
                        >
                          {{ file.file_name }}
                        </li>
                      </ul>
                      <p class="mt-2 text-xs text-amber-700">
                        Click "Configure" next to each file above to set up import settings before
                        preprocessing.
                      </p>
                    </div>
                  </div>
                </div>

                <p class="text-xs text-gray-500 mb-4">
                  This will create a new preprocessing run. Existing runs and documents are
                  preserved.
                </p>
                <div class="flex items-center space-x-3">
                  <button
                    class="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
                    @click="showProcessingPanel = false"
                  >
                    Cancel
                  </button>
                  <button
                    :disabled="!canStartProcessing || isSubmitting"
                    class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    @click="startProcessing"
                  >
                    <svg
                      v-if="isSubmitting"
                      class="animate-spin w-4 h-4 mr-2"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    {{ isSubmitting ? 'Processing...' : 'Start Processing' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Upload Modal -->

    <!-- Upload Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div
          v-if="showUploadModal"
          class="fixed inset-0 z-50 overflow-y-auto bg-black/30 backdrop-blur-md"
          @click="showUploadModal = false"
        >
          <div class="flex items-center justify-center min-h-screen px-4 py-8">
            <!-- Backdrop -->
            <div class="fixed inset-0" />

            <!-- Modal Content -->
            <div
              class="relative bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 z-10"
              @click.stop
            >
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Upload Files</h3>
                <button
                  class="text-gray-400 hover:text-gray-600 transition-colors"
                  @click="showUploadModal = false"
                >
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <!-- Drop Zone -->
              <div
                class="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center hover:border-blue-400 transition-colors bg-gray-50"
                :class="{ 'border-blue-500 bg-blue-50': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleDrop"
              >
                <svg
                  class="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m0-3v12"
                  />
                </svg>
                <p class="mt-4 text-sm font-medium text-gray-900">
                  Drop files here or click to upload
                </p>
                <p class="mt-1 text-xs text-gray-500">PDF, PNG, JPG, DOCX, CSV, XLSX, TXT</p>
                <button
                  class="mt-5 px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  @click="$refs.modalFileInput.click()"
                >
                  Browse Files
                </button>
                <input
                  ref="modalFileInput"
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.docx,.csv,.xlsx,.txt"
                  class="hidden"
                  @change="handleFileSelect"
                />
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- File Preview Modal -->
    <FilePreviewModal
      v-if="previewingFile"
      :file="previewingFile"
      :project-id="projectId"
      @close="previewingFile = null"
    />

    <!-- File Import Config Modal -->
    <FileImportConfigModal
      v-if="showImportConfigModal && configuringFile"
      :file="configuringFile"
      :project-id="projectId"
      @close="
        () => {
          showImportConfigModal = false
          configuringFile = null
        }
      "
      @saved="
        () => {
          showImportConfigModal = false
          configuringFile = null
          fetchFiles()
          emit('files-changed')
        }
      "
    />

    <!-- Duplicate Preview Confirmation Modal -->
    <Teleport to="body">
      <transition name="fade">
        <div
          v-if="showDuplicatePreviewModal"
          class="fixed inset-0 z-50 overflow-y-auto bg-black/30 backdrop-blur-md"
          @click="cancelDuplicatePreview"
        >
          <div class="flex items-center justify-center min-h-screen px-4 py-8">
            <!-- Backdrop -->
            <div class="fixed inset-0" />

            <!-- Modal Content -->
            <div
              class="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full p-6 z-10"
              @click.stop
            >
              <!-- Header -->
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <!-- Dynamic icon based on situation -->
                  <svg
                    v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates"
                    class="w-6 h-6 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="w-6 h-6 text-amber-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <h3 class="text-lg font-semibold text-gray-900">
                    <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
                      PDF Embedded Text Detected
                    </template>
                    <template v-else-if="hasSameConfigDuplicates">
                      Existing Documents Will Be Archived
                    </template>
                    <template v-else> Existing Documents Found </template>
                  </h3>
                </div>
                <button
                  class="text-gray-400 hover:text-gray-600 transition-colors"
                  @click="cancelDuplicatePreview"
                >
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              <!-- Body -->
              <div class="space-y-4">
                <!-- Different messages based on situation -->
                <template v-if="hasPdfsWithEmbeddedText && !hasSameConfigDuplicates">
                  <p class="text-sm text-gray-600">
                    The following PDF file(s) have embedded text. Since "Force OCR" is not enabled,
                    the embedded text will be extracted directly regardless of the selected OCR
                    engine. The result will be identical to previous extractions.
                  </p>
                  <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div class="flex items-start gap-2">
                      <svg
                        class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <p class="text-xs text-blue-800">
                        <strong>Tip:</strong> Enable
                        <code class="bg-blue-100 px-1 rounded">Force OCR for PDFs</code>
                        in Advanced Options to force OCR on all pages, ignoring embedded text.
                      </p>
                    </div>
                  </div>
                </template>

                <template v-else-if="hasSameConfigDuplicates">
                  <p class="text-sm text-gray-600">
                    The following files have existing documents with the
                    <strong>same OCR configuration</strong>. Running preprocessing will create new
                    versions and archive the old ones. Archived documents are hidden by default but
                    can be viewed in the document history.
                  </p>

                  <!-- Option to skip existing -->
                  <label
                    class="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-pointer hover:bg-blue-100 transition-colors"
                  >
                    <input
                      v-model="skipExisting"
                      type="checkbox"
                      class="mt-0.5 text-blue-600 rounded"
                    />
                    <div class="flex-1">
                      <p class="text-sm font-medium text-blue-900">
                        Only process files without existing documents
                      </p>
                      <p class="text-xs text-blue-700 mt-1">
                        Skip files that already have documents for this OCR configuration. Useful if
                        you want to process only new files or re-process files where OCR quality was
                        poor.
                      </p>
                    </div>
                  </label>
                </template>

                <template v-else>
                  <p class="text-sm text-gray-600">
                    The following files have existing documents with a different OCR configuration.
                    Running preprocessing will create additional documents (not replace existing
                    ones). Both versions will be preserved.
                  </p>
                </template>

                <!-- Files with duplicates list -->
                <div class="max-h-80 overflow-y-auto border border-gray-200 rounded-lg">
                  <!-- Show same-config duplicates first (if any) -->
                  <template v-if="hasSameConfigDuplicates">
                    <div
                      v-for="item in duplicatePreview?.same_config_duplicates"
                      :key="item.file_id"
                      class="px-4 py-3 border-b border-gray-100 hover:bg-amber-50"
                    >
                      <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                          <p class="text-sm font-medium text-gray-900 truncate">
                            {{ item.file_name }}
                          </p>
                          <p class="text-xs text-amber-700 mt-1">
                            <svg
                              class="w-3 h-3 inline mr-1"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                              />
                            </svg>
                            {{ item.existing_document_count }} existing document{{
                              item.existing_document_count !== 1 ? 's' : ''
                            }}
                            with same config will be archived
                          </p>
                        </div>
                        <span
                          class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-amber-100 text-amber-700 flex-shrink-0 ml-3"
                        >
                          Same config
                        </span>
                      </div>
                    </div>
                  </template>

                  <!-- Show PDFs with embedded text -->
                  <template v-if="hasPdfsWithEmbeddedText">
                    <div
                      v-for="pdf in duplicatePreview?.pdfs_with_embedded_text"
                      :key="pdf.file_id"
                      class="px-4 py-3 border-b border-gray-100 hover:bg-blue-50"
                    >
                      <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                          <p class="text-sm font-medium text-gray-900 truncate">
                            {{ pdf.file_name }}
                          </p>
                          <p class="text-xs text-blue-700 mt-1">
                            <svg
                              class="w-3 h-3 inline mr-1"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M13 16h-1v-4h-1m1-4h.01"
                              />
                            </svg>
                            Has embedded text
                            <span v-if="pdf.existing_document_ocr_method" class="text-gray-500">
                              • Previously extracted with: {{ pdf.existing_document_ocr_method }}
                            </span>
                          </p>
                        </div>
                        <span
                          class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-700 flex-shrink-0 ml-3"
                        >
                          Embedded text
                        </span>
                      </div>
                    </div>
                  </template>

                  <!-- Show different-config duplicates (if any, and no same-config) -->
                  <template v-if="!hasSameConfigDuplicates && !hasPdfsWithEmbeddedText">
                    <div
                      v-for="item in duplicatePreview?.files_with_duplicates"
                      :key="item.file_id"
                      class="px-4 py-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50"
                    >
                      <div class="flex items-start justify-between">
                        <div class="flex-1 min-w-0">
                          <p class="text-sm font-medium text-gray-900 truncate">
                            {{ item.file_name }}
                          </p>
                          <p class="text-xs text-gray-500 mt-1">
                            {{ item.existing_document_count }} existing document{{
                              item.existing_document_count !== 1 ? 's' : ''
                            }}
                            with different config
                            <span v-if="item.config_name" class="text-gray-400">
                              • Config: {{ item.config_name }}
                            </span>
                          </p>
                        </div>
                        <span
                          class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 flex-shrink-0 ml-3"
                        >
                          Different config
                        </span>
                      </div>
                    </div>
                  </template>
                </div>

                <!-- Summary -->
                <div class="bg-gray-50 rounded-lg p-3 flex items-center justify-between text-sm">
                  <span class="text-gray-600">
                    <span class="font-semibold text-gray-900">{{
                      duplicatePreview?.files_with_duplicates?.length || 0
                    }}</span>
                    file{{
                      (duplicatePreview?.files_with_duplicates?.length || 0) !== 1 ? 's' : ''
                    }}
                    with existing documents
                  </span>
                  <span class="text-gray-600">
                    <span class="font-semibold text-gray-900">{{
                      duplicatePreview?.files_without_duplicates
                    }}</span>
                    new file{{ duplicatePreview?.files_without_duplicates !== 1 ? 's' : '' }}
                  </span>
                </div>

                <!-- Info note about document versioning (only for same-config duplicates) -->
                <div
                  v-if="hasSameConfigDuplicates"
                  class="bg-blue-50 border border-blue-200 rounded-lg p-3"
                >
                  <div class="flex items-start gap-2">
                    <svg
                      class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <p class="text-xs text-blue-800">
                      <strong>Document versioning:</strong> Previous versions are preserved with
                      <code class="bg-blue-100 px-1 rounded">is_latest=false</code> and can be
                      restored if needed. Only the latest version is shown in the document list by
                      default.
                    </p>
                  </div>
                </div>
              </div>

              <!-- Footer Actions -->
              <div class="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors text-sm font-medium"
                  @click="cancelDuplicatePreview"
                >
                  Cancel
                </button>
                <button
                  class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium flex items-center gap-2"
                  @click="confirmAndStartProcessing"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <template v-if="skipExisting">Process New Files Only</template>
                  <template v-else-if="hasSameConfigDuplicates">Archive & Continue</template>
                  <template v-else>Continue</template>
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'
import FilePreviewModal from './files/FilePreviewModal.vue'
import FilesTable from './files/FilesTable.vue'
import FileImportConfigModal from './files/FileImportConfigModal.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { setEngineLabels, getEngineLabel, getEngineSubtitle } from '@/utils/ocrLabels'
import { useScrollLock } from '@/composables/useScrollLock'
import { websocketService } from '@/services/websocket.js'

useScrollLock({ autoLock: false })

const props = defineProps({
  projectId: { type: [String, Number], required: true },
})

const emit = defineEmits(['files-changed'])
const toast = useToast()
const router = useRouter()

// State
const files = ref([])
const selectedFiles = ref([])
const searchQuery = ref('')
const filterStatus = ref('')
const showUnprocessedOnly = ref(false)
const isDragging = ref(false)
const showUploadModal = ref(false)
const showProcessingPanel = ref(false)
const showHistoryPanel = ref(false)
const historyFile = ref(null)
const previewingFile = ref(null)
const fileToDelete = ref(null)
const showImportConfigModal = ref(false)
const configuringFile = ref(null)
const expandedTasks = ref(new Set()) // Multi-expand accordion state
const isLoading = ref(true)

// Duplicate preview state
const showDuplicatePreviewModal = ref(false)
const duplicatePreview = ref(null)
const pendingProcessingSettings = ref(null)
const skipExisting = ref(false) // If true, only process files without existing documents

// "Select all" across all pages state
const selectAllMode = ref(false) // true = all files in project, false = only current page

// Pagination state
const pagination = ref({
  page: 1,
  page_size: 50,
  total: 0,
  total_pages: 0,
  start: 0,
  end: 0,
})

// Sorting state
const sortBy = ref('created_at')
const sortOrder = ref('desc')

// Processing config
const selectedEngine = ref('docling_tesseract')
const forceOcr = ref(false)
const tesseractLang = ref('auto')
const mistralApiKey = ref('')
const mistralModel = ref('')
const visionApiKey = ref('')
const visionBaseUrl = ref('')
const visionModel = ref('')
const visionPrompt = ref('Extract all text from this image and return it as clean markdown.')

// OCR engine availability (from server settings)
const visionOcrEnabled = ref(false)
const mistralOcrEnabled = ref(false)
const doclingOcrEnabled = ref(true)
const visionMaxImageDim = ref(0)
const showAdvanced = ref(false)
const isSubmitting = ref(false)

// Cache for preprocessing tasks to avoid refetching on every file refresh
let cachedTasks = null
let cachedTasksTimestamp = null
const TASKS_CACHE_TTL_MS = 30000 // 30 seconds cache (increased for 50k+ files scaling)

// Fetch files with preprocessing tasks (paginated)
const fetchFiles = async (options = {}) => {
  const { forceRefreshTasks = false } = options

  try {
    const params = new URLSearchParams({
      page: String(pagination.value.page),
      page_size: String(pagination.value.page_size),
      sort_by: sortBy.value,
      sort_order: sortOrder.value,
    })

    // Add search filter
    if (searchQuery.value) {
      params.append('search', searchQuery.value)
    }

    // Add status filter
    if (filterStatus.value) {
      params.append('status', filterStatus.value)
    }

    const response = await api.get(`/project/${props.projectId}/file?${params}`)
    const data = response.data

    // Update pagination
    pagination.value = {
      page: data.page || 1,
      page_size: data.page_size || 25,
      total: data.total || 0,
      total_pages: data.total_pages || 0,
      start: (data.page - 1) * data.page_size + 1,
      end: Math.min(data.page * data.page_size, data.total),
    }

    // Fetch preprocessing tasks with caching to avoid refetching on every file refresh
    const now = Date.now()
    const needTasks =
      forceRefreshTasks ||
      !cachedTasks ||
      !cachedTasksTimestamp ||
      now - cachedTasksTimestamp > TASKS_CACHE_TTL_MS

    let allTasks = []
    if (needTasks) {
      const tasksResponse = await api.get(`/project/${props.projectId}/preprocess?limit=100`)
      allTasks = tasksResponse.data || []
      cachedTasks = allTasks
      cachedTasksTimestamp = now
    } else {
      allTasks = cachedTasks
    }

    // Build a map: file_id -> [tasks]
    const tasksByFileId = new Map()
    for (const task of allTasks) {
      if (task.file_tasks && Array.isArray(task.file_tasks)) {
        for (const ft of task.file_tasks) {
          const fid = ft.file_id
          if (!tasksByFileId.has(fid)) {
            tasksByFileId.set(fid, [])
          }
          tasksByFileId.get(fid).push(task)
        }
      }
    }

    // Create new file objects with _status and preprocessing_tasks for proper reactivity
    const filesWithTasks = (data.items || []).map((file) => {
      const fileTasks = tasksByFileId.get(file.id) || []
      const sortedTasks = fileTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      return {
        ...file,
        preprocessing_tasks: sortedTasks,
        _status: getFileStatus({ ...file, preprocessing_tasks: sortedTasks }),
      }
    })

    files.value = filesWithTasks

    // Update historyFile if panel is open
    if (showHistoryPanel.value && historyFile.value) {
      const updatedHistoryFile = filesWithTasks.find((f) => f.id === historyFile.value.id)
      if (updatedHistoryFile) {
        historyFile.value = { ...updatedHistoryFile }
      }
    }
  } catch (err) {
    console.error('Failed to fetch files:', err)
    toast.error('Failed to load files')
  } finally {
    isLoading.value = false
  }
}

// Display files (for the table - just returns files.value since pagination is server-side)
const displayFiles = computed(() => files.value)

// Get file status based on latest preprocessing task
const getFileStatus = (file) => {
  if (!file || !Array.isArray(file.preprocessing_tasks) || file.preprocessing_tasks.length === 0) {
    return 'not_preprocessed'
  }

  const latestTask = [...file.preprocessing_tasks].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at),
  )[0]

  if (!latestTask) return 'not_preprocessed'

  const status = String(latestTask.status || '').toLowerCase()

  if (['pending', 'processing', 'in_progress'].includes(status)) {
    return 'processing'
  } else if (status === 'completed') {
    return 'completed'
  } else {
    return 'failed'
  }
}

// Pagination handlers
const handlePageChange = (newPage) => {
  if (newPage >= 1 && newPage <= pagination.value.total_pages) {
    pagination.value.page = newPage
    fetchFiles()
  }
}

const handlePageSizeChange = (newSize) => {
  pagination.value.page_size = Number(newSize)
  pagination.value.page = 1 // Reset to first page
  fetchFiles()
}

// Sorting handler
const handleSort = (field) => {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortOrder.value = 'desc'
  }
  pagination.value.page = 1 // Reset to first page
  fetchFiles()
}

// Toggle file selection
const toggleSelection = (fileId) => {
  const idx = selectedFiles.value.indexOf(fileId)
  if (idx > -1) {
    selectedFiles.value.splice(idx, 1)
  } else {
    selectedFiles.value.push(fileId)
  }
}

// Toggle select all (for current page only)
const toggleSelectAll = () => {
  if (selectedFiles.value.length === files.value.length) {
    selectedFiles.value = []
    selectAllMode.value = false
  } else {
    selectedFiles.value = files.value.map((f) => f.id)
    selectAllMode.value = false
  }
}

// Select ALL files across all pages (for 50k+ files)
const selectAllFiles = async () => {
  selectAllMode.value = true
  // Fetch all file IDs from the project (server-side)
  try {
    // We need to fetch all file IDs - use a minimal request
    // This is a one-time operation even for large projects
    const allFileIds = []
    let page = 1
    const pageSize = 250 // Max allowed per page

    while (true) {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
      })

      if (searchQuery.value) params.append('search', searchQuery.value)
      if (filterStatus.value) params.append('file_type', filterStatus.value)

      const response = await api.get(`/project/${props.projectId}/file?${params}`)
      const fileIds = response.data.items.map((f) => f.id)
      allFileIds.push(...fileIds)

      if (page >= response.data.total_pages) break
      page++
    }

    selectedFiles.value = allFileIds
    toast.success(`Selected all ${allFileIds.length} files`)
  } catch (err) {
    console.error('Failed to select all files:', err)
    toast.error('Failed to select all files')
    selectAllMode.value = false
  }
}

// Clear selection
const clearSelection = () => {
  selectedFiles.value = []
  selectAllMode.value = false
}

// Navigate to document
const navigateToDocument = (documentId) => {
  // Close the history panel and explicitly release scroll lock before navigating
  showHistoryPanel.value = false
  // Explicitly clear scroll lock
  document.body.style.overflow = ''
  // Switch to documents tab and highlight the document
  emit('files-changed') // Trigger parent to refresh if needed
  router.push({
    path: `/projects/${props.projectId}`,
    query: { tab: 'documents', highlight: documentId },
  })
}

// Confirm delete file
const confirmDeleteFile = (file) => {
  fileToDelete.value = file
  // Could open a confirmation modal here - for now we'll use browser confirm
  if (confirm(`Delete "${file.file_name}"? This action cannot be undone.`)) {
    deleteFile(file)
  }
  fileToDelete.value = null
}

// Delete file
const deleteFile = async (file) => {
  try {
    await api.delete(`/project/${props.projectId}/file/${file.id}`)
    toast.success(`Deleted ${file.file_name}`)
    // Invalidate task cache when files change
    cachedTasks = null
    cachedTasksTimestamp = null
    await fetchFiles({ forceRefreshTasks: true })
    emit('files-changed')
  } catch (err) {
    console.error('Failed to delete file:', err)
    toast.error(`Failed to delete ${file.file_name}`)
  }
}

// Open import config modal
const openImportConfigModal = (file) => {
  configuringFile.value = file
  showImportConfigModal.value = true
}

// Get file by ID (for panel display)
const getFileById = (id) => {
  return files.value.find((f) => f.id === id)
}

// Handle view preprocessing history
const handleViewHistory = (file) => {
  historyFile.value = file
  showHistoryPanel.value = true
}

// Process file and close history panel
const processFileAndClose = (file) => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Process file and close panel (for footer button)
const processFileAndClosePanel = (file) => {
  quickProcessFile(file)
  showHistoryPanel.value = false
}

// Get engine name from task
const getEngineName = (task) => {
  const settings = task.configuration?.additional_settings || {}
  const engine = settings.ocr_engine || 'local'

  if (engine === 'mistral_ocr') return 'Mistral OCR'
  if (engine === 'llm_vision') return 'Vision LLM'
  if (settings.force_ocr) return 'Local OCR + Force'
  return 'Local OCR'
}

// Helper to check task status (handles enum or string)
const isTaskStatus = (task, expectedStatus) => {
  if (!task || !task.status) return false
  return String(task.status).toLowerCase() === String(expectedStatus).toLowerCase()
}

// Format relative time
const formatRelativeTime = (dateString) => {
  if (!dateString) return ''
  const diff = new Date() - new Date(dateString)
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(dateString).toLocaleDateString()
}

// Format ETA seconds to HH:MM:SS
const prettyEta = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00:00'
  return new Date(seconds * 1000).toISOString().substring(11, 19)
}

// Retry failed files for a task
const retryFailedFiles = async (taskId) => {
  try {
    await api.get(`/project/${props.projectId}/preprocess/${taskId}/retry-failed`)
    toast.success('Retrying failed files...')
    // Refresh files to show new task
    await fetchFiles()
  } catch (err) {
    console.error('Failed to retry failed files:', err)
    toast.error('Failed to retry failed files')
  }
}

// Cancel preprocessing task
const cancelPreprocessingTask = async (task) => {
  if (
    !confirm(
      'Cancel this preprocessing task? Any files still being processed will be marked as failed.',
    )
  ) {
    return
  }
  try {
    await api.post(`/project/${props.projectId}/preprocess/${task.id}/cancel?keep_processed=true`)
    toast.success('Preprocessing cancelled')
    // Close the history panel if open
    showHistoryPanel.value = false
    historyFile.value = null
    // Full refresh to get updated state from server
    await fetchFiles()
  } catch (err) {
    console.error('Failed to cancel preprocessing:', err)
    toast.error('Failed to cancel preprocessing')
  }
}

// Preview file
const previewFile = (file) => {
  previewingFile.value = file
}

// Download file
const downloadFile = async (file) => {
  try {
    const response = await api.get(`/project/${props.projectId}/file/${file.id}/content`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', file.file_name)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch {
    toast.error(`Failed to download ${file.file_name}`)
  }
}

// Toggle accordion expansion for a task
const toggleTaskAccordion = (taskId) => {
  if (expandedTasks.value.has(taskId)) {
    expandedTasks.value.delete(taskId)
  } else {
    expandedTasks.value.add(taskId)
  }
}

// Format processing time in seconds to human readable
const formatProcessingTime = (seconds) => {
  if (!seconds && seconds !== 0) return ''
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

// Quick process single file
const quickProcessFile = (file) => {
  selectedFiles.value = [file.id]
  openProcessingPanel()
}

// Open processing panel
const openProcessingPanel = () => {
  showProcessingPanel.value = true
  showAdvanced.value = false
}

// Check if any selected CSV/XLSX files lack preprocessing strategy
const unconfiguredCsvXlsxFiles = computed(() => {
  return files.value.filter((f) => {
    if (!selectedFiles.value.includes(f.id)) return false
    const isCsvXlsx =
      f.file_type === 'text/csv' ||
      f.file_type === 'application/vnd.ms-excel' ||
      f.file_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return isCsvXlsx && !f.preprocessing_strategy
  })
})

// Can start processing
const canStartProcessing = computed(() => {
  return (
    selectedFiles.value.length > 0 &&
    !isSubmitting.value &&
    unconfiguredCsvXlsxFiles.value.length === 0
  )
})

// OCR engine availability
const anyOcrEnabled = computed(
  () => doclingOcrEnabled.value || mistralOcrEnabled.value || visionOcrEnabled.value,
)
const noOcrEnabled = computed(() => !anyOcrEnabled.value)

// Computed properties for modal display
const hasSameConfigDuplicates = computed(() => {
  return (
    duplicatePreview.value?.same_config_duplicates &&
    duplicatePreview.value.same_config_duplicates.length > 0
  )
})

const hasPdfsWithEmbeddedText = computed(() => {
  return (
    duplicatePreview.value?.pdfs_with_embedded_text &&
    duplicatePreview.value.pdfs_with_embedded_text.length > 0
  )
})

// Check for duplicates and start processing (or show confirmation)
const startProcessing = async () => {
  if (!canStartProcessing.value) return

  isSubmitting.value = true

  // Build processing settings
  const settings = {
    ocr_engine: selectedEngine.value,
    force_ocr: forceOcr.value,
  }

  if (selectedEngine.value === 'docling_tesseract' && tesseractLang.value !== 'auto') {
    settings.docling_ocr_languages = [tesseractLang.value]
  }

  if (selectedEngine.value === 'mistral_ocr') {
    if (mistralApiKey.value) settings.mistral_api_key = mistralApiKey.value
    if (mistralModel.value) settings.mistral_model = mistralModel.value
  }

  if (selectedEngine.value === 'llm_vision') {
    if (visionApiKey.value) settings.vision_api_key = visionApiKey.value
    if (visionBaseUrl.value) settings.vision_base_url = visionBaseUrl.value
    if (visionModel.value) settings.vision_model = visionModel.value
    if (visionPrompt.value) settings.vision_prompt = visionPrompt.value
    if (visionMaxImageDim.value > 0) settings.vision_max_image_dim = visionMaxImageDim.value
  }

  // Store settings for later use
  pendingProcessingSettings.value = {
    file_ids: selectedFiles.value,
    inline_config: {
      name: 'Quick Processing',
      additional_settings: settings,
    },
  }

  try {
    // First, check for duplicates
    const previewResponse = await api.post(
      `/project/${props.projectId}/preprocess/preview`,
      pendingProcessingSettings.value,
    )

    duplicatePreview.value = previewResponse.data

    // Only show modal if there are same-config duplicates (not just different OCR configs)
    // Also show if PDFs with embedded text exist (to inform user OCR won't affect result)
    const hasSameConfigDuplicates =
      previewResponse.data.same_config_duplicates &&
      previewResponse.data.same_config_duplicates.length > 0
    const hasPdfsWithEmbeddedText =
      previewResponse.data.pdfs_with_embedded_text &&
      previewResponse.data.pdfs_with_embedded_text.length > 0

    if (hasSameConfigDuplicates || hasPdfsWithEmbeddedText) {
      showDuplicatePreviewModal.value = true
      isSubmitting.value = false // Reset loading state while waiting for user confirmation
      return // Exit early - actual processing happens after confirmation
    }

    // No same-config duplicates - proceed directly
    await confirmAndStartProcessing()
  } catch (err) {
    console.error('Failed to check for duplicates:', err)
    isSubmitting.value = false
    const detail = err.response?.data?.detail
    let errorMsg = 'Failed to check for existing documents'
    if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0]
      errorMsg = firstError.msg || JSON.stringify(firstError)
    } else if (typeof detail === 'string') {
      errorMsg = detail
    }
    toast.error(errorMsg)
    pendingProcessingSettings.value = null
  }
}

// Cancel duplicate preview and close modal
const cancelDuplicatePreview = () => {
  showDuplicatePreviewModal.value = false
  duplicatePreview.value = null
  pendingProcessingSettings.value = null
  isSubmitting.value = false
}

// Confirm and start processing (called after user approves duplicate preview)
const confirmAndStartProcessing = async () => {
  if (!pendingProcessingSettings.value) return

  // Add skip_existing flag if user selected it
  if (skipExisting.value) {
    pendingProcessingSettings.value.skip_existing = true
  }

  try {
    await api.post(`/project/${props.projectId}/preprocess`, pendingProcessingSettings.value)

    const firstSelectedFileId = pendingProcessingSettings.value.file_ids[0]

    toast.success(
      `Preprocessing started for ${pendingProcessingSettings.value.file_ids.length} file(s)`,
    )
    showProcessingPanel.value = false
    showDuplicatePreviewModal.value = false
    selectedFiles.value = []
    duplicatePreview.value = null
    skipExisting.value = false
    pendingProcessingSettings.value = null

    // Invalidate task cache when starting new preprocessing
    cachedTasks = null
    cachedTasksTimestamp = null
    // Refresh files with forced task refresh to show the new task immediately
    await fetchFiles({ forceRefreshTasks: true })

    // Auto-open history panel for the first file to show the new task
    if (firstSelectedFileId) {
      const file = files.value.find((f) => f.id === firstSelectedFileId)
      if (file) {
        historyFile.value = file
        showHistoryPanel.value = true
      }
    }
  } catch (err) {
    console.error('Failed to start processing:', err)
    const detail = err.response?.data?.detail
    let errorMsg = 'Failed to start preprocessing'

    // Handle structured error response
    if (detail && typeof detail === 'object') {
      if (detail.code === 'csv_xlsx_needs_config') {
        errorMsg = detail.message || 'CSV/XLSX files need import configuration'
      } else if (detail.code === 'files_already_being_processed') {
        errorMsg = detail.message || 'One or more files are already being processed'
      } else if (detail.code === 'no_ocr_engine_enabled') {
        errorMsg = detail.message || 'No OCR engine enabled'
      } else if (detail.message) {
        errorMsg = detail.message
      }
    } else if (Array.isArray(detail) && detail.length > 0) {
      const firstError = detail[0]
      errorMsg = firstError.msg || JSON.stringify(firstError)
    } else if (typeof detail === 'string') {
      errorMsg = detail
    }

    toast.error(errorMsg)
  } finally {
    isSubmitting.value = false
  }
}

// Handle file drop
const handleDrop = (e) => {
  isDragging.value = false
  const droppedFiles = Array.from(e.dataTransfer.files)
  uploadFiles(droppedFiles)
}

// Handle file select
const handleFileSelect = (e) => {
  const selectedFiles = Array.from(e.target.files)
  uploadFiles(selectedFiles)
  e.target.value = null
}

// Upload files
const uploadFiles = async (fileList) => {
  if (!fileList.length) return

  isSubmitting.value = true

  for (const file of fileList) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append(
        'file_info',
        JSON.stringify({
          file_name: file.name,
          file_type: file.type,
          file_size: file.size,
        }),
      )

      await api.post(`/project/${props.projectId}/file`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      toast.success(`Uploaded ${file.name}`)
    } catch (err) {
      console.error(`Failed to upload ${file.name}:`, err)
      toast.error(`Failed to upload ${file.name}`)
    }
  }

  isSubmitting.value = false
  showUploadModal.value = false
  // Invalidate task cache when files change
  cachedTasks = null
  cachedTasksTimestamp = null
  await fetchFiles({ forceRefreshTasks: true })
  emit('files-changed')
}

// Lock body scroll when processing or history panel is open
watch([showProcessingPanel, showHistoryPanel], ([procVal, histVal]) => {
  document.body.style.overflow = procVal || histVal ? 'hidden' : ''
})

// Fetch OCR settings on mount to use server-provided display names
const fetchOcrSettings = async () => {
  try {
    const res = await api.get('/auth/settings')
    setEngineLabels(res.data)
    visionOcrEnabled.value = res.data.vision_ocr_enabled || false
    mistralOcrEnabled.value = res.data.mistral_ocr_enabled || false
    doclingOcrEnabled.value =
      res.data.docling_serve_enabled !== undefined ? res.data.docling_serve_enabled : true

    // Reset selected engine if current selection is disabled
    if (selectedEngine.value === 'llm_vision' && !visionOcrEnabled.value) {
      selectedEngine.value = 'docling_tesseract'
    } else if (selectedEngine.value === 'mistral_ocr' && !mistralOcrEnabled.value) {
      selectedEngine.value = 'docling_tesseract'
    }
    // If all OCR engines are disabled, reset to null to show warning
    if (!visionOcrEnabled.value && !mistralOcrEnabled.value && !doclingOcrEnabled.value) {
      selectedEngine.value = null
    }
  } catch (err) {
    console.error('Failed to fetch OCR settings:', err)
  }
}

// WebSocket subscription for preprocessing updates
let wsPreprocessingUnsubscribe = null
const seenTaskIds = new Set()

// Debounce for refresh triggers (prevents multiple rapid refetches)
let refreshDebounceTimer = null
const REFRESH_DEBOUNCE_MS = 500 // Wait 500ms after last trigger before refetching

const startWebSocket = () => {
  wsPreprocessingUnsubscribe = websocketService.onPreprocessingUpdate((data) => {
    // Only update if the task belongs to this project (handle string/number comparison)
    if (String(data.project_id) !== String(props.projectId)) return

    // Check if this is a new task we haven't seen before
    const taskId = data.task_id
    const isNewTask = !seenTaskIds.has(taskId)
    if (taskId) {
      seenTaskIds.add(taskId)
    }

    // Check for terminal states via event field or status
    const isTerminalState =
      ['completed', 'failed', 'cancelled'].includes(String(data.event || '')) ||
      ['completed', 'failed', 'cancelled'].includes(String(data.status || '').toLowerCase())

    if (isTerminalState || isNewTask) {
      // Invalidate task cache immediately for terminal states to force fresh fetch
      if (isTerminalState) {
        cachedTasks = null
        cachedTasksTimestamp = null
      }
      // Use debounced refresh to prevent rapid refetches when multiple tasks complete
      debouncedFetchFiles()
    } else {
      // For progress updates, merge the WebSocket data directly into files
      mergePreprocessingUpdate(data)
    }
  })
}

// Merge WebSocket preprocessing update into files array
const mergePreprocessingUpdate = (data) => {
  const taskId = data.task_id
  if (!taskId) return

  // Find the file that has this task in its preprocessing_tasks
  const fileIndex = files.value.findIndex((f) =>
    f.preprocessing_tasks?.some((t) => t.id === taskId),
  )

  if (fileIndex >= 0) {
    const file = files.value[fileIndex]

    // Update historyFile first if this file is currently being shown
    const isHistoryFile = historyFile.value?.id === file.id

    const taskIndex = file.preprocessing_tasks.findIndex((t) => t.id === taskId)

    if (taskIndex >= 0) {
      // Merge the update into the existing task
      const existingTask = file.preprocessing_tasks[taskIndex]
      const updatedTask = {
        ...existingTask,
        ...data,
        id: taskId,
        task_id: undefined, // Clean up the field
      }

      // Preserve and merge meta and configuration
      if (data.meta) {
        updatedTask.meta = { ...(existingTask.meta || {}), ...data.meta }
      }
      if (data.configuration) {
        updatedTask.configuration = data.configuration
      }

      // Calculate progress percentage if not provided but we have the data
      if (!updatedTask.meta?.progress && updatedTask.meta?.total_files > 0) {
        const completed = updatedTask.meta.completed_files || 0
        const total = updatedTask.meta.total_files
        updatedTask.meta = {
          ...(updatedTask.meta || {}),
          progress: (completed / total) * 100,
        }
      } else if (
        !updatedTask.meta?.progress &&
        updatedTask.processed_files > 0 &&
        updatedTask.total_files > 0
      ) {
        // Fallback: calculate from processed_files/total_files
        updatedTask.meta = {
          ...(updatedTask.meta || {}),
          progress: (updatedTask.processed_files / updatedTask.total_files) * 100,
        }
      }

      file.preprocessing_tasks[taskIndex] = updatedTask
      file._status = getFileStatus(file)

      // Trigger reactivity
      files.value = [...files.value]

      // Also update historyFile if this file is currently being shown
      if (isHistoryFile) {
        historyFile.value = { ...file }
      }
    }
  }
}

const stopWebSocket = () => {
  if (wsPreprocessingUnsubscribe) {
    wsPreprocessingUnsubscribe()
    wsPreprocessingUnsubscribe = null
  }
  if (refreshDebounceTimer) {
    clearTimeout(refreshDebounceTimer)
    refreshDebounceTimer = null
  }
}

// Debounced refresh to prevent rapid refetches when multiple tasks update simultaneously
const debouncedFetchFiles = () => {
  if (refreshDebounceTimer) {
    clearTimeout(refreshDebounceTimer)
  }
  refreshDebounceTimer = setTimeout(() => {
    // Always force refresh tasks when triggered by terminal state
    fetchFiles({ forceRefreshTasks: true })
    refreshDebounceTimer = null
  }, REFRESH_DEBOUNCE_MS)
}

// Start WebSocket on mount (no polling needed)
watch(
  () =>
    files.value.some((f) =>
      f.preprocessing_tasks?.some((t) =>
        ['pending', 'processing', 'in_progress'].includes(String(t.status || '').toLowerCase()),
      ),
    ),
  (hasActiveTasks) => {
    // With WebSocket, we don't need to start/stop anything
    // The connection is already established and listening
    if (hasActiveTasks && !websocketService.isConnected) {
      websocketService.connect()
    }
  },
  { immediate: true },
)

// Handle expand-preprocessing-task event from ActivityBell
const handleExpandTask = (event) => {
  const taskId = event.detail?.id
  if (!taskId) return

  // Try to find and expand the task, retrying a few times if files aren't loaded yet
  const tryExpandTask = (attempts = 0) => {
    const fileWithTask = files.value.find((f) =>
      f.preprocessing_tasks?.some((t) => t.id === Number(taskId)),
    )
    if (fileWithTask) {
      // Open the history panel for this file
      historyFile.value = fileWithTask
      showHistoryPanel.value = true
      // Expand the specific task
      expandedTasks.value.add(Number(taskId))
    } else if (attempts < 5) {
      // Retry after a short delay if files aren't loaded yet
      setTimeout(() => tryExpandTask(attempts + 1), 200)
    }
  }
  tryExpandTask()
}

onMounted(async () => {
  fetchFiles()
  fetchOcrSettings()
  startWebSocket()
  // Listen for expand event from ActivityBell
  document.addEventListener('expand-preprocessing-task', handleExpandTask)
})

onUnmounted(() => {
  stopWebSocket()
  document.removeEventListener('expand-preprocessing-task', handleExpandTask)
  // Ensure scroll lock is released when component unmounts
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* Smooth transitions */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* Fade transition for modals */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Panel slide-in animation */
.panel-slide-enter {
  transform: translateX(100%);
  animation: slideIn 0.3s ease-in-out forwards;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
</style>
