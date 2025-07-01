<template>
  <div
    v-if="isModal"
    class="fixed inset-0 bg-black/40 backdrop-blur-md flex items-center justify-center p-4 z-50"
    @click="$emit('close')"
  >
    <div
      class="bg-white rounded-lg shadow-2xl max-w-8xl w-full max-h-[95vh] flex flex-col"
      @click.stop
    >
      <div class="px-6 py-4 border-b flex justify-between items-center bg-gradient-to-r from-blue-50 to-white">
        <h3 class="text-xl font-semibold text-gray-800">Trial Results</h3>
        <button @click="$emit('close')" class="text-gray-500 hover:text-gray-700 transition-colors duration-200">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="overflow-y-auto flex-1 p-6">
        <div v-if="isLoading" class="text-center py-12">
          <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
          <p class="mt-2 text-gray-500">Loading trial results...</p>
        </div>

        <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded-r-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm text-red-700">{{ error }}</p>
            </div>
          </div>
        </div>

        <template v-else-if="trial">
          <!-- Trial information -->
          <div class="bg-white shadow-sm rounded-lg p-5 mb-6 border border-gray-100">
            <div class="flex flex-col md:flex-row md:justify-between">
              <div>
                <h2 class="text-lg font-medium text-gray-800">Trial #{{ trial.id }}</h2>
                <div class="text-sm text-gray-500 mt-2">
                  <div class="mb-1">Started: {{ formatDate(trial.created_at, true) }}</div>
                  <div class="mb-1">Status:
                    <span class="px-2 py-1 rounded-full text-xs font-medium"
                      :class="{
                        'bg-green-100 text-green-800': trial.status === 'completed',
                        'bg-blue-100 text-blue-800': trial.status === 'processing',
                        'bg-yellow-100 text-yellow-800': trial.status === 'pending',
                        'bg-red-100 text-red-800': trial.status === 'failed'
                      }">{{ trial.status }}</span>
                  </div>
                  <div>Model: <span class="font-medium text-gray-700">{{ trial.llm_model }}</span></div>
                </div>
              </div>
              <div class="mt-4 md:mt-0">
                <div class="text-sm bg-blue-50 px-4 py-2 rounded-lg">
                  <div class="font-medium text-blue-800">{{ trial.results?.length || 0 }} documents processed</div>
                </div>
              </div>
            </div>
          </div>

          <!-- No results message -->
          <div v-if="!trial.results || trial.results.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-gray-500 mt-3">No results available for this trial.</p>
            <p v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-gray-400">
              Please wait for the trial to complete.
            </p>
          </div>

          <!-- Accordion-style results -->
          <div v-else class="grid grid-cols-1 gap-4">
            <div v-for="(result, index) in trial.results" :key="index"
                 class="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-100 hover:shadow-md transition-shadow duration-200">
              <div
                @click="toggleResultExpansion(index)"
                class="p-4 cursor-pointer border-b flex justify-between items-center hover:bg-gray-50 transition-colors duration-150"
              >
                <div class="flex flex-col">
                  <div class="flex items-center mb-1">
                    <span class="w-7 h-7 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center mr-2 text-sm font-bold">
                      {{ index + 1 }}
                    </span>
                    <h3 class="font-medium text-gray-800">Document #{{ index + 1 }}</h3>
                  </div>
                  <p class="text-sm text-gray-500 ml-9 line-clamp-1">
                    {{ documentNames[index] || 'Loading document name...' }}
                  </p>
                </div>
                <svg
                  class="w-5 h-5 transition-transform duration-200 text-gray-500"
                  :class="{ 'transform rotate-180': expandedResults[index] }"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </div>

              <div v-if="expandedResults[index]" class="p-5">
                <div
                  class="flex gap-5"
                  :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col lg:flex-row'"
                >
                  <!-- Document content panel -->
                  <div class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                    <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Document Content
                    </h4>
                    <div v-if="isMarkdown(documentContents[index])" class="markdown-content" v-html="renderMarkdown(documentContents[index])"></div>
                    <pre v-else class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContents[index] }}</pre>
                  </div>

                  <!-- Extracted data panel -->
                  <div class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                    <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      Extracted Information
                    </h4>
                    <JsonViewer :data="result.result" />
                  </div>

                  <!-- Original document panel -->
                  <div v-if="showDocumentPanel[index]" class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                    <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                      </svg>
                      Original Document
                    </h4>
                    <iframe v-if="documentPdfUrls[index]" :src="documentPdfUrls[index]" frameborder="0" width="100%" height="400px" class="rounded-md"></iframe>
                    <div v-else-if="documentPdfLoading[index]" class="text-center py-12">
                      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                      <p class="mt-2 text-gray-500">Loading PDF...</p>
                    </div>
                    <p v-else class="text-gray-500">Failed to load PDF</p>
                  </div>
                </div>

                <div class="mt-5 flex justify-end gap-3">
                  <button
                    @click="toggleViewMode(index)"
                    class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm flex items-center transition-colors duration-150"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
                    </svg>
                    {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
                  </button>
                  <button
                    @click="toggleDocumentPanel(index)"
                    class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md text-sm flex items-center transition-colors duration-150"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-if="showDocumentPanel[index]" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-else d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-else d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    {{ showDocumentPanel[index] ? 'Hide Original Document' : 'View Original Document' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="text-center py-12">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-gray-500 mt-3">Trial not found</p>
          <button @click="$emit('close')" class="mt-4 inline-block px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors duration-150">
            Return to trials
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="trial-results container mx-auto px-4 py-6">
    <div class="mb-6 flex items-center">
      <button @click="goBack" class="mr-4 text-gray-500 hover:text-gray-700 transition-colors duration-150">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd"
            d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
            clip-rule="evenodd" />
        </svg>
      </button>
      <h1 class="text-2xl font-bold text-gray-800">Trial Results</h1>
    </div>

    <div v-if="isLoading" class="text-center py-12">
      <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
      <p class="mt-2 text-gray-500">Loading trial results...</p>
    </div>

    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 mb-4 rounded-r-md">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{{ error }}</p>
        </div>
      </div>
    </div>

    <template v-else-if="trial">
      <!-- Trial information -->
      <div class="bg-white shadow-sm rounded-lg p-5 mb-6 border border-gray-100">
        <div class="flex flex-col md:flex-row md:justify-between">
          <div>
            <h2 class="text-lg font-medium text-gray-800">Trial #{{ trial.id }}</h2>
            <div class="text-sm text-gray-500 mt-2">
              <div class="mb-1">Started: {{ formatDate(trial.created_at, true) }}</div>
              <div class="mb-1">Status:
                <span class="px-2 py-1 rounded-full text-xs font-medium"
                  :class="{
                    'bg-green-100 text-green-800': trial.status === 'completed',
                    'bg-blue-100 text-blue-800': trial.status === 'processing',
                    'bg-yellow-100 text-yellow-800': trial.status === 'pending',
                    'bg-red-100 text-red-800': trial.status === 'failed'
                  }">{{ trial.status }}</span>
              </div>
              <div>Model: <span class="font-medium text-gray-700">{{ trial.llm_model }}</span></div>
            </div>
          </div>
          <div class="mt-4 md:mt-0">
            <div class="text-sm bg-blue-50 px-4 py-2 rounded-lg">
              <div class="font-medium text-blue-800">{{ trial.results?.length || 0 }} documents processed</div>
            </div>
          </div>
        </div>
      </div>

      <!-- No results message -->
      <div v-if="!trial.results || trial.results.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-gray-500 mt-3">No results available for this trial.</p>
        <p v-if="trial.status === 'processing' || trial.status === 'pending'" class="text-sm mt-2 text-gray-400">
          Please wait for the trial to complete.
        </p>
      </div>

      <!-- Accordion-style results -->
      <div v-else class="grid grid-cols-1 gap-4">
        <div v-for="(result, index) in trial.results" :key="index"
            class="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-100 hover:shadow-md transition-shadow duration-200">
          <div
            @click="toggleResultExpansion(index)"
            class="p-4 cursor-pointer border-b flex justify-between items-center hover:bg-gray-50 transition-colors duration-150"
          >
            <div class="flex flex-col">
              <div class="flex items-center mb-1">
                <span class="w-7 h-7 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center mr-2 text-sm font-bold">
                  {{ index + 1 }}
                </span>
                <h3 class="font-medium text-gray-800">Document #{{ index + 1 }}</h3>
              </div>
              <p class="text-sm text-gray-500 ml-9 line-clamp-1">
                {{ documentNames[index] || 'Loading document name...' }}
              </p>
            </div>
            <svg
              class="w-5 h-5 transition-transform duration-200 text-gray-500"
              :class="{ 'transform rotate-180': expandedResults[index] }"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </div>

          <div v-if="expandedResults[index]" class="p-5">
            <div
              class="flex gap-5"
              :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
            >
              <!-- Document content panel -->
              <div class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Document Content
                </h4>
                <div v-if="isMarkdown(documentContents[index])" class="markdown-content" v-html="renderMarkdown(documentContents[index])"></div>
                <pre v-else class="text-xs text-gray-800 whitespace-pre-wrap">{{ documentContents[index] }}</pre>
              </div>

              <!-- Extracted data panel -->
              <div class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  Extracted Information
                </h4>
                <JsonViewer :data="result.result" />
              </div>

              <!-- Original document panel (only in non-modal view) -->
              <div v-if="showDocumentPanel[index]" class="bg-gray-50 p-5 rounded-md overflow-auto flex-1 max-h-[500px] border border-gray-200">
                <h4 class="text-sm font-medium mb-3 text-gray-700 flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                  </svg>
                  Original Document
                </h4>
                <iframe v-if="documentPdfUrls[index]" :src="documentPdfUrls[index]" frameborder="0" width="100%" height="400px" class="rounded-md"></iframe>
                <div v-else-if="documentPdfLoading[index]" class="text-center py-12">
                  <div class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                  <p class="mt-2 text-gray-500">Loading PDF...</p>
                </div>
                <p v-else class="text-gray-500">Failed to load PDF</p>
              </div>
            </div>

            <div class="mt-5 flex justify-end gap-3">
              <button
                @click="toggleViewMode(index)"
                class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm flex items-center transition-colors duration-150"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
                </svg>
                {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
              </button>
              <button
                @click="toggleDocumentPanel(index)"
                class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md text-sm flex items-center transition-colors duration-150"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-if="showDocumentPanel[index]" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-else d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" v-else d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                {{ showDocumentPanel[index] ? 'Hide Original Document' : 'View Original Document' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="text-center py-12">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-gray-500 mt-3">Trial not found</p>
      <router-link :to="`/projects/${props.projectId}/trials`" class="mt-4 inline-block px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors duration-150">
        Return to trials
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '@/services/api';
import { formatDate } from '@/utils/formatters.js';
import { useToast } from 'vue-toastification';
import JsonViewer from './JsonViewer.vue';
import { marked } from 'marked';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  },
  trialId: {
    type: [String, Number],
    required: true
  },
  isModal: {
    type: Boolean,
    default: false
  }
});

defineEmits(['close']);

const route = useRoute();
const router = useRouter();
const toast = useToast();

const trialId = computed(() => props.trialId || parseInt(route.params.trialId));
const isLoading = ref(true);
const error = ref(null);
const trial = ref(null);
const selectedResultIndex = ref(0);

// New state variables for accordion and document content
const expandedResults = ref({});
const documentContents = ref({});
const documentNames = ref({});
const viewMode = ref({}); // 'vertical' or 'horizontal'
const documentPdfUrls = ref({});
const documentPdfLoading = ref({});
const showDocumentPanel = ref({});

const renderMarkdown = (text) => {
  try {
    return marked(text);
  } catch (e) {
    return text;
  }
};

const isMarkdown = (text) => {
  if (!text) return false;

  try {
    // Simple check for markdown patterns
    return text.includes('#') ||
           text.includes('**') ||
           text.includes('*') ||
           text.includes('[') ||
           text.includes('```') ||
           /\n\s*-\s/.test(text) ||  // Bullet points
           /\n\s*\d+\.\s/.test(text); // Numbered lists
  } catch (e) {
    return false;
  }
};

// Fetch trial data
const fetchData = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    // Load trial data
    const response = await api.get(`/project/${props.projectId}/trial/${trialId.value}`);
    trial.value = response.data;

    // Start loading document names
    if (trial.value?.document_ids) {
      loadDocumentNames();
    }
  } catch (err) {
    console.error('Error loading trial data:', err);
    error.value = err.message || 'Failed to load trial data';
  } finally {
    isLoading.value = false;
  }
};

// Load document names
const loadDocumentNames = async () => {
  if (!trial.value?.document_ids) return;

  for (let i = 0; i < trial.value.document_ids.length; i++) {
    try {
      const docId = trial.value.document_ids[i];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);

      // Extract filename from either original_file or metadata
      let documentName = '';
      if (response.data.original_file && response.data.original_file.file_name) {
        documentName = response.data.original_file.file_name;
      } else if (response.data.metadata && response.data.metadata.title) {
        documentName = response.data.metadata.title;
      } else {
        documentName = `Document ${docId}`;
      }

      documentNames.value[i] = documentName;
    } catch (err) {
      console.error(`Error loading document name for index ${i}:`, err);
      documentNames.value[i] = `Document (ID: ${trial.value.document_ids[i]})`;
    }
  }
};

// Navigation functions
const goBack = () => {
  if (props.isModal) {
    $emit('close');
  } else {
    router.push(`/projects/${props.projectId}/trials`);
  }
};

// Toggle results expansion
const toggleResultExpansion = async (index) => {
  // Toggle expansion state
  expandedResults.value[index] = !expandedResults.value[index];

  // Set default view mode if not set
  if (viewMode.value[index] === undefined) {
    viewMode.value[index] = 'horizontal';
  }

  // Load document content if expanded and not already loaded
  if (expandedResults.value[index] && !documentContents.value[index]) {
    try {
      const docId = trial.value.document_ids[index];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      documentContents.value[index] = response.data.text || 'No text content available';
    } catch (err) {
      documentContents.value[index] = 'Error loading document content';
      console.error(err);
    }
  }
};

// Toggle view mode between vertical and horizontal
const toggleViewMode = (index) => {
  viewMode.value[index] = viewMode.value[index] === 'vertical' ? 'horizontal' : 'vertical';
};

// Toggle document panel with proper authentication
const toggleDocumentPanel = async (index) => {
  showDocumentPanel.value[index] = !showDocumentPanel.value[index];

  if (showDocumentPanel.value[index] && !documentPdfUrls.value[index] && !documentPdfLoading.value[index]) {
    documentPdfLoading.value[index] = true;
    try {
      const docId = trial.value.document_ids[index];
      const response = await api.get(`/project/${props.projectId}/document/${docId}`);
      const document = response.data;
      let fileId;

      if (document.preprocessed_file_id && document.preprocessed_file.file_type === 'application/pdf') {
        fileId = document.preprocessed_file_id;
      } else if (['application/pdf', 'image/png', 'image/jpeg'].includes(document.original_file.file_type)) {
        fileId = document.original_file_id;
      }

      if (fileId) {
        // Create a blob URL using an authenticated request
        const fileResponse = await api.get(`/project/${props.projectId}/file/${fileId}/content?preview=true`, {
          responseType: 'blob'
        });
        const blob = new Blob([fileResponse.data], { type: fileResponse.headers['content-type'] });
        documentPdfUrls.value[index] = URL.createObjectURL(blob);
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to load document");
    } finally {
      documentPdfLoading.value[index] = false;
    }
  }
};

// Load data on mount
onMounted(() => {
  fetchData();
});
</script>

<style>
.json-viewer {
  font-family: monospace;
  font-size: 14px;
}

.json-item {
  margin: 2px 0;
}

.json-key {
  cursor: pointer;
  display: flex;
  align-items: flex-start;
}

.toggle-icon {
  width: 16px;
  display: inline-block;
}

.key-name {
  color: #881391;
  margin-right: 5px;
}

.json-value {
  color: #1a1aa6;
}

.json-children {
  border-left: 1px dashed #ccc;
  padding-left: 1rem;
}

/* Truncate text on a single line */
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Markdown styling */
.markdown-content {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #333;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.25em; }
.markdown-content h3 { font-size: 1.125em; }

.markdown-content p {
  margin-bottom: 1em;
}

.markdown-content ul,
.markdown-content ol {
  margin-bottom: 1em;
  padding-left: 1.5em;
}

.markdown-content li {
  margin-bottom: 0.25em;
}

.markdown-content code {
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 85%;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
}

.markdown-content pre {
  background-color: #f6f8fa;
  border-radius: 3px;
  padding: 1em;
  overflow: auto;
  margin-bottom: 1em;
}

.markdown-content pre code {
  background-color: transparent;
  padding: 0;
}

.markdown-content a {
  color: #0366d6;
  text-decoration: none;
}

.markdown-content a:hover {
  text-decoration: underline;
}

.markdown-content img {
  max-width: 100%;
}

.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.markdown-content table th,
.markdown-content table td {
  border: 1px solid #ddd;
  padding: 0.5em;
}

.markdown-content table th {
  background-color: #f6f8fa;
  font-weight: 600;
}

.markdown-content blockquote {
  border-left: 4px solid #dfe2e5;
  padding-left: 1em;
  color: #6a737d;
  margin: 0 0 1em;
}
</style>
