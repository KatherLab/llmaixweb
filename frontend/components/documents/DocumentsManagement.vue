<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-start">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Documents</h2>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          View and manage processed documents and document groups
        </p>
      </div>
    </div>

    <div class="border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-8">
        <button
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm',
            activeTab === 'documents'
              ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600',
          ]"
          @click="activeTab = 'documents'"
        >
          All Documents
          <span
            class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs dark:bg-gray-800 dark:text-gray-300"
          >
            {{ totalCount }}
          </span>
        </button>
        <button
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm',
            activeTab === 'groups'
              ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600',
          ]"
          @click="activeTab = 'groups'"
        >
          Document Groups
          <span
            class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs dark:bg-gray-800 dark:text-gray-300"
          >
            {{ documentGroupsCount }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div v-if="activeTab === 'documents'">
      <!-- Filters and Search -->
      <div
        class="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700 mb-4"
      >
        <!-- Top row: Search + Filters -->
        <div class="flex items-center gap-3">
          <!-- Search -->
          <div class="relative flex-1 max-w-sm">
            <input
              v-model="filters.search"
              type="text"
              placeholder="Search documents..."
              class="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              @input="debouncedFetchDocuments"
            />
            <svg
              class="absolute left-3 top-2.5 h-4 w-4 text-gray-400 dark:text-gray-500"
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

          <!-- OCR Engine Filter -->
          <select
            v-model="filters.ocrEngine"
            class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            @change="fetchDocuments"
          >
            <option value="">All OCR Engines</option>
            <option value="pypdf">Embedded Text (pypdf)</option>
            <option value="tesseract">Local OCR (Tesseract)</option>
            <option value="mistral_ocr">Mistral OCR</option>
            <option value="llm_vision">Vision LLM</option>
          </select>

          <!-- Date Range Filter -->
          <select
            v-model="filters.dateRange"
            class="px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            @change="handleDateRangeChange"
          >
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="yesterday">Yesterday</option>
            <option value="week">Last 7 Days</option>
            <option value="month">Last 30 Days</option>
            <option value="custom">Custom Range...</option>
          </select>

          <!-- Clear Filters -->
          <button
            v-if="hasActiveFilters"
            class="px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title="Clear all filters"
            @click="clearFilters"
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

          <div class="ml-auto text-sm text-gray-500 dark:text-gray-400">
            {{ totalCount }} documents
          </div>
        </div>

        <!-- Custom Date Range Picker (shown when "Custom Range" is selected) -->
        <div
          v-if="filters.dateRange === 'custom'"
          class="flex items-center gap-3 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
        >
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600 dark:text-gray-300">From:</label>
            <input
              v-model="customDateFrom"
              type="date"
              class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              @change="applyCustomDateRange"
            />
          </div>
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600 dark:text-gray-300">To:</label>
            <input
              v-model="customDateTo"
              type="date"
              class="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              @change="applyCustomDateRange"
            />
          </div>
          <button
            class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
            @click="applyCustomDateRange"
          >
            Apply
          </button>
        </div>

        <!-- Active Filters Summary -->
        <div
          v-if="hasActiveFilters"
          class="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
        >
          <span class="text-xs text-gray-500 dark:text-gray-400">Active filters:</span>
          <span
            v-if="filters.search"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full"
          >
            Search: "{{ filters.search }}"
            <button class="hover:text-red-600" @click="clearSearchFilter()">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </span>
          <span
            v-if="filters.ocrEngine"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full"
          >
            OCR: {{ getOcrEngineLabel(filters.ocrEngine) }}
            <button class="hover:text-red-600" @click="clearOcrEngineFilter()">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </span>
          <span
            v-if="filters.dateRange && filters.dateRange !== 'custom'"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
          >
            Date: {{ getDateRangeLabel(filters.dateRange) }}
            <button class="hover:text-red-600" @click="clearDateRangeFilter()">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </span>
          <span
            v-if="filters.dateRange === 'custom' && customDateFrom"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full"
          >
            Date: {{ customDateFrom }} → {{ customDateTo || 'present' }}
            <button class="hover:text-red-600" @click="clearCustomDateRange()">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </span>
          <span
            v-if="filters.includeArchived"
            class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full"
          >
            Archived
            <button class="hover:text-red-600" @click="clearArchivedFilter()">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </span>
        </div>

        <!-- Archived Toggle (inline with other filters) -->
        <div
          class="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-slate-600"
        >
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="filters.includeArchived"
              type="checkbox"
              class="rounded text-blue-600 focus:ring-blue-500"
              @change="fetchDocuments"
            />
            <span class="text-sm text-gray-700 dark:text-gray-300">
              Include archived versions
              <span v-if="filters.includeArchived" class="text-xs text-gray-500 ml-1">
                (showing document history)
              </span>
            </span>
          </label>
        </div>
      </div>

      <!-- Batch Actions -->
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center space-x-3">
          <span class="text-sm text-gray-500 dark:text-gray-400">
            {{ totalCount }} document{{ totalCount !== 1 ? 's' : '' }}
          </span>

          <div v-if="selectedDocuments.length > 0" class="flex items-center space-x-2">
            <span class="text-sm text-gray-700 dark:text-gray-300">
              {{ selectedDocuments.length }} selected
            </span>
            <button
              class="text-sm text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 font-medium"
              @click="createGroupFromSelection"
            >
              Create Group
            </button>
            <span class="text-gray-300 dark:text-gray-600">|</span>
            <button
              class="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              @click="performBatchAction('reprocess')"
            >
              Reprocess
            </button>
            <button
              class="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
              @click="performBatchAction('export')"
            >
              Export
            </button>
            <button
              class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 font-medium"
              @click="performBatchAction('delete')"
            >
              Delete
            </button>
            <button
              class="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300"
              @click="selectedDocuments = []"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <!-- Documents Grid/List -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>

      <!-- Empty State: No documents (either no documents exist or filters returned no results) -->
      <div
        v-else-if="hasLoadedDocuments && serverItems.length === 0"
        class="bg-gray-50 dark:bg-slate-800 rounded-lg p-12 text-center"
      >
        <svg
          class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500"
          xmlns="http://www.w3.org/2000/svg"
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
        <h3 class="mt-2 text-lg font-medium text-gray-900 dark:text-white">
          {{ hasActiveFilters ? 'No documents match your filters' : 'No documents found' }}
        </h3>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{
            hasActiveFilters
              ? 'Try adjusting or clearing your filters to see more results'
              : filters.search
                ? 'Try adjusting your search or filters'
                : 'Process some files to see documents here'
          }}
        </p>
        <button
          v-if="hasActiveFilters"
          class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          @click="clearFilters"
        >
          Clear All Filters
        </button>
      </div>

      <!-- True Empty State: No documents processed yet -->
      <div
        v-else-if="!hasLoadedDocuments && serverItems.length === 0"
        class="bg-gray-50 dark:bg-slate-800 rounded-lg p-12 text-center"
      >
        <svg
          class="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">No documents yet</h3>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Process some files in the Files & Preprocessing tab to see documents here
        </p>
      </div>

      <!-- Documents Table -->
      <div
        v-else
        class="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-slate-800">
            <tr>
              <th class="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  :checked="areAllDocumentsSelected"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600"
                  @change="toggleSelectAll"
                />
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Document
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Configuration
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Model
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                Created
              </th>
              <th class="relative px-6 py-3">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-slate-900 divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="doc in serverItems"
              :key="doc.id"
              class="hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <input
                  type="checkbox"
                  :checked="selectedDocuments.includes(doc.id)"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600"
                  @change="toggleDocumentSelection(doc.id)"
                />
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center">
                  <FileIcon :file-type="doc.original_file?.file_type" :size="40" />
                  <div class="ml-3">
                    <p class="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                      {{
                        doc.document_name || doc.original_file?.file_name || `Document #${doc.id}`
                      }}
                    </p>
                    <p
                      v-if="
                        doc.document_name &&
                        doc.original_file?.file_name &&
                        doc.document_name !== doc.original_file?.file_name
                      "
                      class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs"
                    >
                      {{ doc.original_file?.file_name }}
                    </p>
                    <p v-else class="text-xs text-gray-500 dark:text-gray-400">
                      {{ formatFileSize(doc.original_file?.file_size) }}
                    </p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 dark:text-white">
                  {{ doc.preprocessing_config?.name || 'Custom Config' }}
                </div>
                <div v-if="getOcrDisplay(doc)" class="text-xs text-gray-500 dark:text-gray-400">
                  {{ getOcrDisplay(doc) }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 dark:text-white">
                  {{ getModelName(doc) }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {{ formatDate(doc.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end space-x-2">
                  <button
                    class="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                    title="View"
                    @click="viewDocument(doc)"
                  >
                    <svg
                      class="h-5 w-5"
                      xmlns="http://www.w3.org/2000/svg"
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
                  </button>
                  <button
                    class="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                    title="Download"
                    @click="downloadDocument(doc)"
                  >
                    <svg
                      class="h-5 w-5"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                      />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="totalPages > 1"
        class="bg-white dark:bg-slate-900 px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 sm:px-6"
      >
        <div class="flex-1 flex justify-between sm:hidden">
          <button
            :disabled="currentPage === 1"
            class="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="currentPage--"
          >
            Previous
          </button>
          <button
            :disabled="currentPage === totalPages"
            class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="currentPage++"
          >
            Next
          </button>
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <!-- ✅ Server-side version -->
            <p class="text-sm text-gray-700 dark:text-gray-300">
              Showing
              <span class="font-medium">{{ (currentPage - 1) * itemsPerPage + 1 }}</span>
              to
              <span class="font-medium">{{
                Math.min(currentPage * itemsPerPage, totalCount)
              }}</span>
              of
              <span class="font-medium">{{ totalCount }}</span>
              results
            </p>
          </div>
          <div>
            <nav
              class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
              aria-label="Pagination"
            >
              <button
                :disabled="currentPage === 1"
                class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-slate-900 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                @click="currentPage = 1"
              >
                <span class="sr-only">First</span>
                <svg
                  class="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                  />
                </svg>
              </button>
              <button
                v-for="page in visiblePages"
                :key="page"
                :class="[
                  'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                  page === currentPage
                    ? 'z-10 bg-blue-50 dark:bg-blue-900 border-blue-500 dark:border-blue-400 text-blue-600 dark:text-blue-400'
                    : 'bg-white dark:bg-slate-900 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800',
                ]"
                @click="currentPage = page"
              >
                {{ page }}
              </button>
              <button
                :disabled="currentPage === totalPages"
                class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-slate-900 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                @click="currentPage = totalPages"
              >
                <span class="sr-only">Last</span>
                <svg
                  class="h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 5l7 7-7 7M5 5l7 7-7 7"
                  />
                </svg>
              </button>
            </nav>
          </div>
        </div>
      </div>

      <!-- Batch Actions Modal -->
      <BatchActionsModal
        v-if="showBatchActions"
        :action="batchAction"
        :documents="selectedDocuments"
        :project-id="projectId"
        @close="showBatchActions = false"
        @complete="handleBatchComplete"
        @deleted="handleDocumentsDeleted"
      />

      <!-- Create Document Group Modal (from documents tab) -->
      <CreateDocumentGroupModal
        v-if="showCreateGroupModal"
        :documents="documents"
        :project-id="projectId"
        :selected-document-ids="createGroupWithDocs"
        @close="handleCreateGroupModalClose"
        @save="handleCreateGroupModalSave"
      />
    </div>

    <div v-else-if="activeTab === 'groups'">
      <DocumentGroups
        :project-id="projectId"
        @refresh="handleGroupsRefresh"
        @view-document="viewDocument"
      />
    </div>

    <!-- Document Viewer Modal (moved outside tabs to be always available) -->
    <DocumentViewer
      v-if="viewingDocument"
      :document="viewingDocument"
      :project-id="projectId"
      @close="viewingDocument = null"
      @reprocess="reprocessDocument"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api.js'
import { useToast } from 'vue-toastification'
import { debounce } from 'perfect-debounce'
import { setEngineLabels } from '@/utils/ocrLabels'
import FileIcon from '../common/FileIcon.vue'
import LoadingSpinner from '../common/LoadingSpinner.vue'
import DocumentViewer from './DocumentViewer.vue'
import BatchActionsModal from './BatchActionsModal.vue'
import DocumentGroups from './DocumentsGroups.vue'
import CreateDocumentGroupModal from './CreateDocumentGroupModal.vue'

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true,
  },
})

const route = useRoute()
const router = useRouter()
const toast = useToast()

// State
const documents = ref([]) // All documents for groups modal
const allDocumentsLoaded = ref(false) // Track if we've fetched all documents
const isLoading = ref(true)
const selectedDocuments = ref([])
const viewingDocument = ref(null)
const showBatchActions = ref(false)
const batchAction = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(50)
const activeTab = ref('documents')
const showCreateGroupModal = ref(false)
const createGroupWithDocs = ref([]) // Documents to pre-select when creating group
const serverItems = ref([]) // current page rows from the server
const totalCount = ref(0) // total rows on the server (after filters)
const documentGroupsCount = ref(0) // count of document groups

// Filters
const filters = ref({
  search: '',
  dateRange: '',
  ocrEngine: '',
  includeArchived: false,
})

// Custom date range state
const customDateFrom = ref('')
const customDateTo = ref('')

// Debounce timer for search
let searchDebounceTimer = null

// Track if we've ever loaded documents (for filter UX)
const hasLoadedDocuments = ref(false)

// OCR engine labels mapping
const ocrEngineLabels = {
  pypdf: 'Embedded Text',
  tesseract: 'Local OCR',
  mistral_ocr: 'Mistral OCR',
  llm_vision: 'Vision LLM',
}

// Date range labels mapping
const dateRangeLabels = {
  today: 'Today',
  yesterday: 'Yesterday',
  week: 'Last 7 Days',
  month: 'Last 30 Days',
  custom: 'Custom Range',
}

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return (
    filters.value.search ||
    filters.value.dateRange ||
    filters.value.ocrEngine ||
    (filters.value.dateRange === 'custom' && customDateFrom.value) ||
    filters.value.includeArchived
  )
})

// Get OCR engine label
const getOcrEngineLabel = (engine) => {
  return ocrEngineLabels[engine] || engine
}

// Get date range label
const getDateRangeLabel = (range) => {
  return dateRangeLabels[range] || range
}

// Compute date bounds for date range filter
const computeDateBounds = (range) => {
  const now = new Date()
  const start = new Date(now)

  if (range === 'today') {
    start.setHours(0, 0, 0, 0)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'yesterday') {
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    yesterday.setHours(0, 0, 0, 0)
    start.setHours(23, 59, 59, 999)
    return { date_from: yesterday.toISOString(), date_to: start.toISOString() }
  } else if (range === 'week') {
    start.setDate(now.getDate() - 7)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'month') {
    start.setDate(now.getDate() - 30)
    return { date_from: start.toISOString(), date_to: now.toISOString() }
  } else if (range === 'custom' && customDateFrom.value) {
    const from = new Date(customDateFrom.value)
    from.setHours(0, 0, 0, 0)
    const to = customDateTo.value ? new Date(customDateTo.value) : now
    to.setHours(23, 59, 59, 999)
    return { date_from: from.toISOString(), date_to: to.toISOString() }
  }
  return {}
}

// Handle date range change
const handleDateRangeChange = () => {
  if (filters.value.dateRange === 'custom') {
    // Don't fetch yet - wait for user to select dates
    return
  }
  currentPage.value = 1
  fetchDocuments()
}

// Apply custom date range
const applyCustomDateRange = () => {
  currentPage.value = 1
  fetchDocuments()
}

// Clear custom date range
const clearCustomDateRange = () => {
  customDateFrom.value = ''
  customDateTo.value = ''
  filters.value.dateRange = ''
  fetchDocuments()
}

// Debounced fetch for search
const debouncedFetchDocuments = () => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 1
    fetchDocuments()
  }, 300)
}

// Stats - using server-side totalCount
const totalDocuments = computed(() => totalCount.value)

// Server-side pagination - totalPages is already computed from totalCount
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / itemsPerPage.value)))

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 2) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i)
      }
      pages.push('...')
      pages.push(total)
    }
  }

  return pages.filter((p) => p === '...' || (p >= 1 && p <= total))
})

// Handle highlight query parameter (from preprocessing history "Go to Document" navigation)
const handleHighlight = async () => {
  const highlightId = route.query.highlight
  if (!highlightId) return

  try {
    // Fetch the specific document by ID
    const { data } = await api.get(`/project/${props.projectId}/document/${highlightId}`)
    if (data) {
      // Open the document viewer
      viewingDocument.value = data
      // Clear the highlight parameter without reloading
      router.replace({ query: { ...route.query, highlight: undefined } })
    }
  } catch (error) {
    console.error('Failed to load highlighted document:', error)
    toast.error('Failed to load document')
    // Still clear the parameter to avoid repeated errors
    router.replace({ query: { ...route.query, highlight: undefined } })
  }
}

// Watch for route query changes (e.g., highlight parameter from navigation)
watch(
  () => route.query.highlight,
  (newHighlight) => {
    if (newHighlight) {
      handleHighlight()
    }
  },
  { immediate: true },
)

// Methods
const fetchDocuments = async () => {
  isLoading.value = true
  try {
    const { date_from, date_to } = computeDateBounds(filters.value.dateRange)
    const params = {
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value,
      search: filters.value.search || undefined,
      date_from: date_from || undefined,
      date_to: date_to || undefined,
      include_archived: filters.value.includeArchived || undefined,
      ocr_engine: filters.value.ocrEngine || undefined,
      compute_stats: true, // Get server-side stats
    }

    const { data } = await api.get(`/project/${props.projectId}/document`, { params })
    serverItems.value = data.items
    totalCount.value = data.total

    // Mark that we've loaded documents at least once (for filter UX)
    hasLoadedDocuments.value = true

    // Safety: if you navigated beyond last page due to a filter change, pull back
    if (
      serverItems.value.length === 0 &&
      totalCount.value > 0 &&
      currentPage.value > totalPages.value
    ) {
      currentPage.value = totalPages.value
      await fetchDocuments()
    }
  } catch (error) {
    toast.error('Failed to load documents')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

const toggleDocumentSelection = (docId) => {
  const index = selectedDocuments.value.indexOf(docId)
  if (index > -1) {
    selectedDocuments.value.splice(index, 1)
  } else {
    selectedDocuments.value.push(docId)
  }
}

const toggleSelectAll = () => {
  if (areAllDocumentsSelected.value) {
    // Deselect all - remove current page items from selection
    const currentPageIds = serverItems.value.map((doc) => doc.id)
    selectedDocuments.value = selectedDocuments.value.filter((id) => !currentPageIds.includes(id))
  } else {
    // Select all items on current page
    const currentPageIds = serverItems.value.map((doc) => doc.id)
    const newIds = currentPageIds.filter((id) => !selectedDocuments.value.includes(id))
    selectedDocuments.value = [...selectedDocuments.value, ...newIds]
  }
}

const areAllDocumentsSelected = computed(() => {
  return (
    serverItems.value.length > 0 &&
    serverItems.value.every((doc) => selectedDocuments.value.includes(doc.id))
  )
})

const viewDocument = (doc) => {
  viewingDocument.value = doc
}

const downloadDocument = async (doc) => {
  try {
    const fileId = doc.preprocessed_file?.id || doc.original_file?.id
    if (!fileId) {
      toast.error('No file available for download')
      return
    }

    const response = await api.get(`/project/${props.projectId}/file/${fileId}/content`, {
      responseType: 'blob',
    })

    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', doc.original_file?.file_name || `document_${doc.id}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    toast.error('Failed to download document')
    console.error(error)
  }
}

const performBatchAction = (action) => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }

  batchAction.value = action
  showBatchActions.value = true
}

const createGroupFromSelection = () => {
  if (selectedDocuments.value.length === 0) {
    toast.warning('Please select documents first')
    return
  }
  createGroupWithDocs.value = [...selectedDocuments.value]
  showCreateGroupModal.value = true
}

const handleCreateGroupModalClose = () => {
  showCreateGroupModal.value = false
  createGroupWithDocs.value = []
}

const handleCreateGroupModalSave = async (groupData) => {
  try {
    await api.post(`/project/${props.projectId}/document-set`, groupData)
    toast.success('Document group created successfully')
    showCreateGroupModal.value = false
    createGroupWithDocs.value = []
    selectedDocuments.value = []
  } catch (error) {
    toast.error('Failed to create document group')
    console.error(error)
  }
}

// Fetch all documents for the CreateDocumentGroupModal
const fetchAllDocuments = async () => {
  if (allDocumentsLoaded.value) {
    return
  }
  try {
    const PAGE_SIZE = 500
    let offset = 0
    let allDocs = []
    let hasMore = true

    while (hasMore) {
      const { data } = await api.get(`/project/${props.projectId}/document`, {
        params: { limit: PAGE_SIZE, offset },
      })
      allDocs = allDocs.concat(data.items || [])
      hasMore = data.items && data.items.length === PAGE_SIZE
      offset += PAGE_SIZE
    }

    documents.value = allDocs
    allDocumentsLoaded.value = true
  } catch (error) {
    console.error('Failed to fetch all documents:', error)
    documents.value = []
  }
}

const handleDocumentsDeleted = (deletedIds) => {
  // Remove successfully deleted documents from selection
  selectedDocuments.value = selectedDocuments.value.filter((id) => !deletedIds.includes(id))
}

const handleBatchComplete = () => {
  // Clear selection and close modal - fetchDocuments will be called separately
  selectedDocuments.value = []
  showBatchActions.value = false
  // Refresh the document list
  fetchDocuments()
}

const handleGroupsRefresh = async () => {
  // Refresh both groups and documents (since documents may have been deleted too)
  await fetchDocumentGroupsCount()
  await fetchDocuments()
}

const reprocessDocument = async (doc) => {
  try {
    const fileId = doc.original_file?.id
    if (!fileId) {
      console.error('Original file id not found for this document!')
      toast.error('Original file id not found for this document!')
      return
    }
    const payload = {
      file_ids: [fileId],
      inline_config: {
        name: `Reprocess ${new Date().toISOString().slice(0, 16).replace('T', ' ')}`,
        additional_settings: {},
      },
      force_reprocess: true,
    }
    await api.post(`/project/${props.projectId}/preprocess`, payload)
    toast.success('Document reprocessing started!')
    fetchDocuments()
  } catch (error) {
    toast.error(error?.response?.data?.detail?.[0]?.msg || 'Failed to start reprocessing')
    console.error(error)
  }
}

const clearFilters = () => {
  filters.value = {
    search: '',
    dateRange: '',
    ocrEngine: '',
    includeArchived: false,
  }
  customDateFrom.value = ''
  customDateTo.value = ''
  currentPage.value = 1
  fetchDocuments()
}

const clearSearchFilter = () => {
  filters.value.search = ''
  debouncedFetchDocuments()
}

const clearOcrEngineFilter = () => {
  filters.value.ocrEngine = ''
  fetchDocuments()
}

const clearDateRangeFilter = () => {
  filters.value.dateRange = ''
  fetchDocuments()
}

const clearArchivedFilter = () => {
  filters.value.includeArchived = false
  fetchDocuments()
}

const getStatusClass = (status) => {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
    case 'partial':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString()
}

const getModelName = (doc) => {
  const metaData = doc.meta_data || {}
  // Check for specific model fields first
  if (metaData.mistral_model) return metaData.mistral_model
  if (metaData.vision_model) return metaData.vision_model
  // Fallback to generic model field
  if (metaData.model) return metaData.model
  // No model for local OCR
  return '—'
}

/**
 * Returns OCR display string only if OCR was actually used.
 * Checks meta_data.ocr_engine to determine if OCR was applied.
 * Returns null if no OCR was used (e.g., embedded text extraction, plain text files, CSV).
 */
const getOcrDisplay = (doc) => {
  const metaData = doc.meta_data || {}
  const ocrEngine = metaData.ocr_engine
  const extractionMethod = metaData.extraction_method
  const file_type = metaData.file_type

  // If ocr_engine is explicitly set, show the appropriate label
  if (ocrEngine) {
    // Map internal engine names to display names
    const engineLabels = {
      tesseract: 'Tesseract OCR',
      docling_tesseract: 'Tesseract OCR',
      mistral_ocr: 'Mistral OCR',
      llm_vision: 'Vision LLM OCR',
    }

    // Special case: pypdf is not OCR, it's embedded text extraction
    if (ocrEngine === 'pypdf') {
      return null
    }

    const label = engineLabels[ocrEngine]
    if (label) {
      return label
    }
  }

  // No ocr_engine set - check extraction_method as fallback
  if (extractionMethod) {
    // Known non-OCR methods - return null
    const nonOcrMethods = [
      'docling_serve_no_ocr',
      'pypdf_embedded_text',
      'text_file_extraction',
      'csv_full_document',
      'csv_row_by_row',
      'xlsx_full_document',
      'xlsx_row_by_row',
    ]
    if (nonOcrMethods.includes(extractionMethod)) {
      return null
    }

    // OCR methods
    const ocrMethods = [
      'docling_serve_tesseract_ocr',
      'docling_serve_tesseract_force_ocr',
      'docling_serve_tesseract_image_ocr',
      'mistral_ocr',
      'llm_vision_ocr',
    ]
    if (ocrMethods.includes(extractionMethod)) {
      const engineLabels = {
        tesseract: 'Tesseract OCR',
        mistral_ocr: 'Mistral OCR',
        llm_vision: 'Vision LLM OCR',
      }
      // Extract engine from method name
      for (const [engine, label] of Object.entries(engineLabels)) {
        if (extractionMethod.includes(engine)) {
          return label
        }
      }
      return 'OCR Applied'
    }
  }

  // Check file_type - table and text files never need OCR
  if (file_type === 'table' || file_type === 'text') {
    return null
  }

  // Default: show nothing if we can't determine OCR was used
  return null
}

// Debounced search
const debouncedSearch = debounce(() => {
  currentPage.value = 1
  fetchDocuments()
}, 300)

// Watchers
watch(() => filters.value.search, debouncedSearch)

watch(
  () => filters.value.dateRange,
  () => {
    currentPage.value = 1
    fetchDocuments()
  },
)

watch([currentPage, itemsPerPage], fetchDocuments)

// Watch for create group modal - fetch all documents when opened
watch(
  () => showCreateGroupModal.value,
  (isOpen) => {
    if (isOpen && !allDocumentsLoaded.value) {
      fetchAllDocuments()
    }
  },
)

// Fetch document groups count
const fetchDocumentGroupsCount = async () => {
  try {
    const { data } = await api.get(`/project/${props.projectId}/document-set`, {
      params: { include_auto_generated: true },
    })
    documentGroupsCount.value = data.total
  } catch (error) {
    console.error('Failed to fetch document groups count:', error)
  }
}

// Lifecycle
onMounted(() => {
  fetchDocuments()
  fetchDocumentGroupsCount()
  // Load OCR display names from server
  api
    .get('/auth/settings')
    .then((r) => setEngineLabels(r.data))
    .catch(() => {})
})
</script>
