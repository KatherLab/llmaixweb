<template>
  <teleport to="body">
    <transition name="fade">
      <div
          v-if="open"
          class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
          @click="handleBackdropClick"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div
            class="relative bg-white rounded-3xl shadow-2xl max-w-5xl w-full max-h-[95vh] flex flex-col overflow-hidden ring-1 ring-blue-100"
            @click.stop
        >
          <div class="px-8 py-6 border-b flex justify-between items-center rounded-t-3xl bg-white">
            <h3 class="text-2xl font-bold tracking-tight">Start New Trial</h3>
            <button aria-label="Close modal" class="text-gray-500 hover:text-gray-700" @click="tryClose">
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
              </svg>
            </button>
          </div>
          <div class="flex-1 overflow-y-auto p-0 md:p-8 bg-white">
            <div class="grid md:grid-cols-2 gap-8">
              <div>
                <div
                    class="mb-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-xl border border-blue-100 shadow flex items-center px-6 py-5 gap-4">
                  <div class="flex-shrink-0">
                    <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"/>
                    </svg>
                  </div>
                  <div class="w-full">
                    <div class="grid grid-cols-1 gap-4">
                      <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide">Trial Name <span
                            class="text-gray-400 font-normal">(optional)</span></label>
                        <input
                            v-model="trialData.name"
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                            maxlength="100"
                            placeholder="E.g. Contract Extraction Run Q3"
                        />
                      </div>
                      <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide">Description <span
                            class="text-gray-400 font-normal">(optional)</span></label>
                        <textarea
                            v-model="trialData.description"
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                            maxlength="512"
                            placeholder="Short summary for this trial (e.g. doc type, goal, changes etc)"
                            rows="2"
                        ></textarea>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="mb-8 bg-white border rounded-xl p-6 shadow">
                  <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-1">Prompt <span
                        class="text-red-500">*</span></label>
                    <select
                        v-model="trialData.prompt_id"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                        @change="resetModelTest"
                    >
                      <option disabled value="">Select a prompt</option>
                      <option v-for="prompt in prompts" :key="prompt.id" :value="prompt.id.toString()">
                        {{ prompt.name }}
                      </option>
                    </select>
                    <details class="mt-1 text-xs">
                      <summary class="text-blue-700 cursor-pointer">Preview Prompt</summary>
                      <div v-if="selectedPrompt" class="mt-2 bg-gray-50 border rounded p-2">
                        <p v-if="selectedPrompt.description" class="mb-1 text-gray-600">{{
                            selectedPrompt.description
                          }}</p>
                        <div v-if="selectedPrompt.system_prompt" class="font-mono text-xs mb-1">Sys:
                          {{ selectedPrompt.system_prompt }}
                        </div>
                        <div v-if="selectedPrompt.user_prompt" class="font-mono text-xs">User:
                          {{ selectedPrompt.user_prompt }}
                        </div>
                      </div>
                    </details>
                  </div>
                  <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-1">Schema <span
                        class="text-red-500">*</span></label>
                    <select
                        v-model="trialData.schema_id"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                        @change="resetModelTest"
                    >
                      <option disabled value="">Select a schema</option>
                      <option v-for="schema in schemas" :key="schema.id" :value="schema.id.toString()">
                        {{ schema.schema_name }}
                      </option>
                    </select>
                    <details class="mt-1 text-xs">
                      <summary class="text-blue-700 cursor-pointer">Preview Schema</summary>
                      <pre v-if="selectedSchema"
                           class="bg-gray-50 border rounded p-2 mt-1 max-h-32 overflow-auto font-mono text-xs">
                        {{ JSON.stringify(selectedSchema.schema_definition, null, 2) }}
                      </pre>
                    </details>
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1">LLM Model <span
                        class="text-red-500">*</span></label>
                    <select
                        v-model="trialData.llm_model"
                        :disabled="isLoadingModels || isTestingConnection || availableModels.length === 0"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    >
                      <option disabled value="">
                        {{
                          isLoadingModels || isTestingConnection ? 'Loading models...' :
                              availableModels.length === 0 ? 'No models available' : 'Select a model'
                        }}
                      </option>
                      <option v-for="model in availableModels" :key="model" :value="model">
                        {{ model }}
                      </option>
                    </select>
                    <div v-if="configStatus.type === 'error'" class="text-xs text-red-500 mt-1">{{
                        configStatus.message
                      }}
                    </div>
                  </div>
                </div>
                <div>
                  <div class="flex items-center gap-4 mb-2">
                    <button
                        class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
                        type="button"
                        @click="advancedSettingsVisible = !advancedSettingsVisible"
                    >
                      <span>{{ advancedSettingsVisible ? 'Hide' : 'Show' }} Advanced Settings</span>
                      <svg :class="{ 'rotate-180': advancedSettingsVisible }" class="h-4 w-4 ml-1 transition-transform"
                           fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                    </button>
                    <button
                        class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
                        type="button"
                        @click="advancedOptionsVisible = !advancedOptionsVisible"
                    >
                      <span>{{ advancedOptionsVisible ? 'Hide' : 'Use' }} Custom API Settings</span>
                      <svg :class="{ 'rotate-180': advancedOptionsVisible }" class="h-4 w-4 ml-1 transition-transform"
                           fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                      </svg>
                    </button>
                  </div>
                  <div v-if="advancedSettingsVisible" class="mt-2 bg-gray-50 border rounded-lg p-4 grid gap-6">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Max Completion Tokens <span class="text-gray-400 font-normal">(optional)</span>
                      </label>
                      <input
                          v-model="maxCompletionTokens"
                          class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          min="1"
                          placeholder="e.g., 4096"
                          type="number"
                      />
                      <p class="mt-1 text-xs text-gray-500">
                        Limit the maximum tokens for model responses. Leave empty to use model defaults.
                      </p>
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Temperature <span class="text-gray-400 font-normal">(optional)</span>
                      </label>
                      <input
                        v-model="temperature"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        min="0"
                        max="2"
                        step="0.01"
                        placeholder="e.g., 0.7"
                        type="number"
                      />
                      <p class="mt-1 text-xs text-gray-500">
                        Controls randomness. Lower values make outputs more focused; higher values make them more random. Typical: 0.1–1.0
                      </p>
                    </div>
                  </div>
                  <div v-if="advancedOptionsVisible" class="mt-2 bg-gray-50 border rounded-lg p-4 grid gap-6">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                      <input
                          v-model="trialData.api_key"
                          class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          placeholder="e.g., sk-1234567890abcdef..."
                          type="password"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                      <input
                          v-model="trialData.base_url"
                          class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          placeholder="e.g., https://api.openai.com/v1"
                          type="text"
                      />
                    </div>
                  </div>
                </div>
                <div v-if="trialData.llm_model && trialData.schema_id && hasValidConfig" class="my-6">
                  <div
                      :class="[
                      'p-4 rounded-md border',
                      {
                        'bg-blue-50 border-blue-200': modelTestStatus.type === 'loading',
                        'bg-yellow-50 border-yellow-200': modelTestStatus.type === 'warning',
                        'bg-red-50 border-red-200': modelTestStatus.type === 'error',
                        'bg-green-50 border-green-200': modelTestStatus.type === 'success',
                        'bg-gray-50 border-gray-200': modelTestStatus.type === 'none'
                      }
                    ]"
                  >
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-2">
                        <svg v-if="modelTestStatus.type === 'loading'" class="animate-spin w-5 h-5 text-blue-500"
                             fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                  stroke-width="4"></circle>
                          <path class="opacity-75"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                fill="currentColor"></path>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'warning'" class="w-5 h-5 text-yellow-500" fill="none"
                             stroke="currentColor" viewBox="0 0 24 24">
                          <path
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 3 1.732 3z"
                              stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'error'" class="w-5 h-5 text-red-500" fill="none"
                             stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round"
                                stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'success'" class="w-5 h-5 text-green-500" fill="none"
                             stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round"
                                stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round"
                                stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <div>
                          <h4 class="font-medium text-gray-900">Model & Schema Compatibility Test</h4>
                          <p
                              :class="[
                              'text-sm',
                              {
                                'text-blue-700': modelTestStatus.type === 'loading',
                                'text-yellow-700': modelTestStatus.type === 'warning',
                                'text-red-700': modelTestStatus.type === 'error',
                                'text-green-700': modelTestStatus.type === 'success',
                                'text-gray-600': modelTestStatus.type === 'none'
                              }
                            ]"
                          >
                            {{ modelTestStatus.message }}
                          </p>
                        </div>
                      </div>
                      <button
                          :disabled="isTestingModel || !trialData.llm_model || !trialData.schema_id"
                          class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed flex items-center gap-2"
                          @click="testSelectedModel"
                      >
                        <svg v-if="isTestingModel" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"
                                  stroke-width="4"></circle>
                          <path class="opacity-75"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                fill="currentColor"></path>
                        </svg>
                        {{ isTestingModel ? 'Testing...' : 'Test Model' }}
                      </button>
                    </div>
                    <div v-if="modelTestStatus.type === 'warning'"
                         class="mt-3 p-3 bg-yellow-100 border border-yellow-200 rounded-md">
                      <p class="text-yellow-800 text-sm">
                        <strong>Required:</strong> You must test the selected model with the schema to ensure
                        compatibility before creating a trial.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <div class="bg-white border rounded-xl p-6 shadow flex flex-col h-full">
                  <div class="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <span class="block text-sm font-semibold text-gray-700">Select Documents <span class="text-red-500">*</span></span>
                    <span class="text-xs text-gray-500">{{ trialData.document_ids.length }} selected</span>
                  </div>
                  <div class="border-b mb-4 flex space-x-4">
                    <button
                        :class="[
                        'py-2 px-1 border-b-2 font-medium text-sm transition-all',
                        documentSelectionMode === 'individual'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      ]"
                        @click="documentSelectionMode = 'individual'"
                    >
                      Individual
                    </button>
                    <button
                        :class="[
                        'py-2 px-1 border-b-2 font-medium text-sm transition-all',
                        documentSelectionMode === 'groups'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      ]"
                        @click="documentSelectionMode = 'groups'"
                    >
                      Groups
                    </button>
                    <button
                        :class="[
                        'py-2 px-1 border-b-2 font-medium text-sm transition-all',
                        documentSelectionMode === 'smart'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      ]"
                        @click="documentSelectionMode = 'smart'"
                    >
                      Smart
                    </button>
                  </div>
                  <div v-if="documentSelectionMode === 'individual'" class="mt-4 flex-1 flex flex-col">
                    <div class="flex gap-2 mb-3">
                      <input
                          v-model="searchTerm"
                          class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          placeholder="Search documents..."
                          type="text"
                      />
                      <button
                          class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                          title="Select all visible documents"
                          @click="selectAllDocuments"
                      >
                        Select All
                      </button>
                      <button
                          class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                          title="Clear selection"
                          @click="clearDocumentSelection"
                      >
                        Clear
                      </button>
                    </div>

                    <div class="border rounded-md overflow-hidden flex-1 min-h-[100px] flex flex-col">
                      <div v-if="filteredDocuments.length === 0" class="p-4 text-center text-gray-500">
                        No documents match your search criteria
                      </div>
                      <div v-else class="max-h-[400px] overflow-y-auto">
                        <div
                            v-for="doc in filteredDocuments"
                            :key="doc.id"
                            :class="[
                              'p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 flex items-center',
                              {'bg-blue-50': trialData.document_ids.includes(doc.id)}
                            ]"
                            @click="toggleDocumentSelection(doc.id)"
                        >
                          <input
                            :checked="trialData.document_ids.includes(doc.id)"
                            class="mr-3"
                            type="checkbox"
                            @click.stop
                            @change="toggleDocumentSelection(doc.id)"
                          />

                          <div class="flex-1">
                            <!-- Main Document Name -->
                            <div class="font-medium">
                              {{ doc.document_name || doc.original_file?.file_name || `Document #${doc.id}` }}
                            </div>

                            <!-- Show original filename if different from document_name -->
                            <div v-if="doc.document_name && doc.original_file?.file_name && doc.document_name !== doc.original_file.file_name" class="text-xs text-gray-400 italic">
                              (Original: {{ doc.original_file.file_name }})
                            </div>

                            <!-- Existing info row -->
                            <div class="text-xs text-gray-500">
                              Config: {{ doc.preprocessing_config?.name || 'N/A' }} •
                              Created: {{ formatDate(doc.created_at) }}
                            </div>
                          </div>

                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="documentSelectionMode === 'groups'" class="mt-4 flex-1 flex flex-col">
                    <div v-if="loadingGroups" class="text-center py-8">
                      <LoadingSpinner/>
                    </div>
                    <div v-else-if="documentGroups.length === 0" class="text-center py-8 bg-gray-50 rounded-lg">
                      <p class="text-gray-500">No document groups available</p>
                    </div>
                    <div v-else class="space-y-2">
                      <div
                          v-for="group in documentGroups"
                          :key="group.id"
                          :class="{ 'ring-2 ring-blue-500 bg-blue-50': selectedGroupId === group.id }"
                          class="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                          @click="toggleGroupSelection(group)"
                      >
                        <div class="flex items-center justify-between">
                          <div class="flex-1">
                            <h4 class="font-medium text-gray-900">{{ group.name }}</h4>
                            <p v-if="group.description" class="text-sm text-gray-600 mt-1">{{ group.description }}</p>
                            <div class="flex items-center gap-4 mt-2 text-xs text-gray-500">
                              <span>{{ group.documents.length }} documents</span>
                              <span v-if="group.preprocessing_config">
                                Config: {{ group.preprocessing_config.name }}
                              </span>
                              <span v-if="group.created_at">
                                Created: {{ formatDate(group.created_at) }}
                              </span>
                            </div>
                            <div v-if="group.tags && group.tags.length > 0" class="mt-2 flex flex-wrap gap-1">
                              <span
                                  v-for="tag in group.tags"
                                  :key="tag"
                                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                              >
                                {{ tag }}
                              </span>
                            </div>
                          </div>
                          <div class="ml-4">
                            <input
                                :checked="selectedGroupId === group.id"
                                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                type="checkbox"
                                @change="toggleGroupSelection(group)"
                                @click.stop
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else-if="documentSelectionMode === 'smart'" class="mt-4 flex-1 flex flex-col gap-4">
                    <div>
                      <h4 class="text-sm font-medium text-gray-700 mb-2">Load from Previous Trial</h4>
                      <select
                          v-model="selectedTrialId"
                          class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          @change="loadDocumentsFromTrial"
                      >
                        <option value="">Select a previous trial...</option>
                        <option v-for="trial in previousTrials" :key="trial.id" :value="trial.id">
                          Trial #{{ trial.id }} - {{ formatDate(trial.created_at) }} ({{ trial.document_ids.length }}
                          docs)
                        </option>
                      </select>
                    </div>
                    <div>
                      <h4 class="text-sm font-medium text-gray-700 mb-2">Filter by Preprocessing Configuration</h4>
                      <select
                          v-model="selectedConfigId"
                          class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                          @change="filterByPreprocessingConfig"
                      >
                        <option value="">All configurations...</option>
                        <option v-for="config in preprocessingConfigs" :key="config.id" :value="config.id">
                          {{ config.name }}
                        </option>
                      </select>
                    </div>
                    <div>
                      <h4 class="text-sm font-medium text-gray-700 mb-2">Filter by Date Range</h4>
                      <div class="grid grid-cols-2 gap-2">
                        <input
                            v-model="dateRange.start"
                            class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            type="date"
                        />
                        <input
                            v-model="dateRange.end"
                            class="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            type="date"
                        />
                      </div>
                    </div>
                    <div class="flex flex-wrap gap-2 pt-2">
                      <button
                          class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                          @click="selectRecentDocuments(7)"
                      >
                        Last 7 days
                      </button>
                      <button
                          class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                          @click="selectRecentDocuments(30)"
                      >
                        Last 30 days
                      </button>
                      <button
                          class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                          @click="selectDocumentsByStatus('success')"
                      >
                        Successfully processed
                      </button>
                    </div>
                    <div v-if="trialData.document_ids.length > 0" class="mt-4 p-3 bg-blue-50 rounded-lg">
                      <div class="flex items-center justify-between">
                        <span class="text-sm font-medium text-blue-900">
                          {{ trialData.document_ids.length }} document{{ trialData.document_ids.length > 1 ? 's' : '' }} selected
                        </span>
                        <div class="flex items-center gap-2">
                          <button
                              class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                              type="button"
                              @click="showSelectedDocs = !showSelectedDocs"
                          >
                            <span v-if="!showSelectedDocs">Show</span>
                            <span v-else>Hide</span>
                            <svg :class="{ 'rotate-180': showSelectedDocs }" class="w-4 h-4 transition-transform"
                                 fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                            </svg>
                          </button>
                          <button
                              class="text-sm text-blue-600 hover:text-blue-800"
                              @click="clearDocumentSelection"
                          >
                            Clear
                          </button>
                        </div>
                      </div>
                      <transition name="fade">
                        <div v-show="showSelectedDocs"
                             class="mt-2 bg-white rounded shadow p-2 max-h-40 overflow-y-auto border border-blue-100">
                          <ul class="text-xs text-gray-800 space-y-1">
                            <li
                                v-for="docId in trialData.document_ids"
                                :key="docId"
                            >
                              {{
                                (documents.find(d => d.id === docId)?.original_file?.file_name) ||
                                `Document #${docId}`
                              }}
                            </li>
                          </ul>
                        </div>
                      </transition>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="px-8 py-6 border-t flex justify-end gap-2 bg-white rounded-b-3xl">
            <button class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md" @click="tryClose">
              Cancel
            </button>
            <button
                :disabled="!isFormValid"
                :title="!isFormValid ? 'Please ensure all required fields are filled, model is tested with schema, and configuration is valid' : ''"
                class="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md disabled:bg-blue-300 disabled:cursor-not-allowed"
                @click="handleSubmit"
            >
              Start Trial
            </button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>


<script setup>
import {computed, onMounted, onUnmounted, ref, watch} from 'vue';
import {formatDate} from '@/utils/formatters.js';
import {api} from '@/services/api.js';
import {useToast} from 'vue-toastification';
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";

const toast = useToast();

const props = defineProps({
  open: {
    type: Boolean,
    required: true
  },
  documents: {
    type: Array,
    required: true
  },
  schemas: {
    type: Array,
    required: true
  },
  prompts: {
    type: Array,
    default: () => []
  },
  projectId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['close', 'create']);

const trialData = ref({
  schema_id: '',
  prompt_id: '',
  document_ids: [],
  llm_model: '',
  api_key: '',
  base_url: '',
  advanced_options: {}
});

const documentSelectionMode = ref('individual');
const documentGroups = ref([]);
const loadingGroups = ref(false);
const selectedGroupId = ref(null);
const previousTrials = ref([]);
const selectedTrialId = ref('');
const preprocessingConfigs = ref([]);
const selectedConfigId = ref('');
const dateRange = ref({start: '', end: ''});
const showSelectedDocs = ref(false);

const lockScroll = () => {
  document.body.style.overflow = 'hidden';
};
const unlockScroll = () => {
  document.body.style.overflow = '';
};


const loadDocumentGroups = async () => {
  loadingGroups.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/document-set`);
    documentGroups.value = response.data;
  } catch (error) {
    toast.error('Failed to load document groups');
    console.error(error);
  } finally {
    loadingGroups.value = false;
  }
};

const loadPreviousTrials = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/trial`);
    previousTrials.value = response.data.filter(trial =>
        trial.status === 'completed' && trial.document_ids.length > 0
    );
  } catch (error) {
    console.error('Failed to load previous trials:', error);
  }
};

const loadPreprocessingConfigs = async () => {
  try {
    const response = await api.get(`/project/${props.projectId}/preprocessing-config`);
    preprocessingConfigs.value = response.data;
  } catch (error) {
    console.error('Failed to load preprocessing configs:', error);
  }
};

const toggleGroupSelection = (group) => {
  if (selectedGroupId.value === group.id) {
    selectedGroupId.value = null;
    trialData.value.document_ids = [];
  } else {
    selectedGroupId.value = group.id;
    trialData.value.document_ids = group.documents.map(doc => doc.id);
  }
};


const loadDocumentsFromTrial = async () => {
  if (!selectedTrialId.value) return;

  const trial = previousTrials.value.find(t => t.id === parseInt(selectedTrialId.value));
  if (trial) {
    trialData.value.document_ids = [...trial.document_ids];
    toast.success(`Loaded ${trial.document_ids.length} documents from previous trial`);
  }
};


const filterByPreprocessingConfig = () => {
  if (!selectedConfigId.value) {
    trialData.value.document_ids = [];
    return;
  }

  const configId = parseInt(selectedConfigId.value);
  const filteredDocs = props.documents.filter(doc =>
      doc.preprocessing_config?.id === configId
  );

  trialData.value.document_ids = filteredDocs.map(doc => doc.id);
  toast.success(`Selected ${filteredDocs.length} documents with this configuration`);
};

const selectRecentDocuments = (days) => {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);

  const recentDocs = props.documents.filter(doc =>
      new Date(doc.created_at) >= cutoffDate
  );

  trialData.value.document_ids = recentDocs.map(doc => doc.id);
  toast.success(`Selected ${recentDocs.length} documents from the last ${days} days`);
};

const selectDocumentsByStatus = (status) => {
  const filteredDocs = props.documents.filter(doc =>
      doc.preprocessing_status === status
  );

  trialData.value.document_ids = filteredDocs.map(doc => doc.id);
  toast.success(`Selected ${filteredDocs.length} ${status} documents`);
};

watch(documentSelectionMode, (newMode) => {
  if (newMode === 'groups' && documentGroups.value.length === 0) {
    loadDocumentGroups();
  } else if (newMode === 'smart') {
    if (previousTrials.value.length === 0) loadPreviousTrials();
    if (preprocessingConfigs.value.length === 0) loadPreprocessingConfigs();
  }
});

const createGroupFromSelection = () => {
  emit('create-group', trialData.value.document_ids);
};


const advancedOptionsVisible = ref(false);
const advancedSettingsVisible = ref(false);
const searchTerm = ref('');
const availableModels = ref([]);
const isLoadingModels = ref(false);
const isTestingConnection = ref(false);
const isTestingModel = ref(false);
const connectionTested = ref(false);
const connectionValid = ref(false);
const modelTested = ref(false);
const modelValid = ref(false);
const systemConfigError = ref(null);
const customConfigError = ref(null);
const modelTestError = ref(null);
const hasSystemConfig = ref(true);

// Advanced options
const maxCompletionTokens = ref('');
const temperature = ref('');

// Test connection first, then load models
const testAndLoadModels = async (apiKey = '', baseUrl = '') => {
  console.log('testAndLoadModels called with:', {apiKey: !!apiKey, baseUrl: !!baseUrl});

  isTestingConnection.value = true;
  connectionTested.value = false;
  connectionValid.value = false;
  availableModels.value = [];
  systemConfigError.value = null;
  customConfigError.value = null;

  // Reset model testing when connection changes
  resetModelTest();

  try {
    const params = {};
    if (apiKey.trim()) params.api_key = apiKey.trim();
    if (baseUrl.trim()) params.base_url = baseUrl.trim();

    console.log('Testing connection with params:', params);
    const testResponse = await api.post('/project/llm/test-connection', null, {params});

    console.log('Connection test response:', testResponse.data);

    if (testResponse.data.success) {
      connectionValid.value = true;
      connectionTested.value = true;

      // Connection successful, now load models
      await loadModels(apiKey, baseUrl);

      if (availableModels.value.length === 0) {
        const errorMsg = 'Connection successful but no models available';
        if (hasCustomApiSettings.value) {
          customConfigError.value = errorMsg;
          toast.error(errorMsg);
        } else {
          systemConfigError.value = errorMsg;
          toast.error('No models available. Please contact your administrator.');
        }
      } else {
        toast.success(`Connection successful. Loaded ${availableModels.value.length} models.`);
      }
    } else {
      connectionValid.value = false;
      connectionTested.value = true;

      const errorMsg = testResponse.data.message || 'Connection test failed';

      if (hasCustomApiSettings.value) {
        customConfigError.value = errorMsg;
        toast.error(errorMsg);
      } else {
        systemConfigError.value = errorMsg;
        hasSystemConfig.value = false;

        if (testResponse.data.error_type === 'incomplete_config') {
          toast.error('System LLM configuration is incomplete. Please contact your administrator or provide custom API settings.');
        } else {
          toast.error(`System LLM configuration error: ${errorMsg}. Please contact your administrator.`);
        }
      }
    }
  } catch (error) {
    console.error('Connection test failed:', error);
    connectionValid.value = false;
    connectionTested.value = true;

    const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message;

    if (hasCustomApiSettings.value) {
      customConfigError.value = errorMsg;
      toast.error(`Connection failed: ${errorMsg}`);
    } else {
      systemConfigError.value = errorMsg;
      hasSystemConfig.value = false;
      toast.error(`System configuration error: ${errorMsg}. Please contact your administrator.`);
    }
  } finally {
    isTestingConnection.value = false;
  }
};

// Load models from API
const loadModels = async (apiKey = '', baseUrl = '') => {
  console.log('loadModels called with:', {apiKey: !!apiKey, baseUrl: !!baseUrl});
  isLoadingModels.value = true;

  try {
    const params = {};
    if (apiKey.trim()) params.api_key = apiKey.trim();
    if (baseUrl.trim()) params.base_url = baseUrl.trim();

    console.log('Making API call to /project/llm/models with params:', params);
    const response = await api.get('/project/llm/models', {params});

    console.log('API response:', response.data);

    if (response.data.success) {
      availableModels.value = response.data.models || [];
      console.log('Loaded models:', availableModels.value);

      // Clear previous model selection when models change
      if (trialData.value.llm_model && !availableModels.value.includes(trialData.value.llm_model)) {
        trialData.value.llm_model = '';
        resetModelTest();
      }
    } else {
      console.error('API returned error:', response.data.message);
      availableModels.value = [];
      throw new Error(response.data.message || 'Failed to load models');
    }
  } catch (error) {
    console.error('Failed to load models:', error);
    availableModels.value = [];
    throw error;
  } finally {
    isLoadingModels.value = false;
  }
};

// Reset model test state
const resetModelTest = () => {
  modelTested.value = false;
  modelValid.value = false;
  modelTestError.value = null;
};

// Test specific model with schema - MANDATORY before submission
const testSelectedModel = async () => {
  if (!trialData.value.llm_model) {
    toast.error('Please select a model first');
    return;
  }

  if (!trialData.value.schema_id) {
    toast.error('Please select a schema first');
    return;
  }

  isTestingModel.value = true;
  modelTested.value = false;
  modelValid.value = false;
  modelTestError.value = null;

  try {
    const params = {
      llm_model: trialData.value.llm_model,
      schema_id: parseInt(trialData.value.schema_id)
    };

    if (trialData.value.api_key.trim()) {
      params.api_key = trialData.value.api_key.trim();
    }
    if (trialData.value.base_url.trim()) {
      params.base_url = trialData.value.base_url.trim();
    }

    console.log('Testing model with schema, params:', params);
    const response = await api.post('/project/llm/test-model-schema', null, {params});

    console.log('Model test response:', response.data);

    modelTested.value = true;

    if (response.data.success) {
      modelValid.value = true;
      toast.success(`Model '${trialData.value.llm_model}' supports structured output with the selected schema!`);
    } else {
      modelValid.value = false;
      modelTestError.value = response.data.message || 'Model test failed';

      if (response.data.error_type === 'structured_output_not_supported') {
        toast.error(`Model '${trialData.value.llm_model}' does not support structured output. Please select a different model.`);
      } else if (response.data.error_type === 'schema_validation_error') {
        toast.error(`Schema validation failed: ${response.data.message}`);
      } else {
        toast.error(response.data.message || 'Model test failed');
      }
    }
  } catch (error) {
    console.error('Model test failed:', error);
    modelTested.value = true;
    modelValid.value = false;

    const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message;
    modelTestError.value = errorMsg;
    toast.error(`Model test failed: ${errorMsg}`);
  } finally {
    isTestingModel.value = false;
  }
};

// Initialize form when modal opens
const initializeForm = () => {
  console.log('Initializing form...');

  trialData.value = {
    name: '',
    description: '',
    schema_id: props.schemas.length > 0 ? props.schemas[0].id.toString() : '',
    prompt_id: props.prompts.length > 0 ? props.prompts[0].id.toString() : '',
    document_ids: [],
    llm_model: '',
    api_key: '',
    base_url: '',
    advanced_options: {}
  };


  searchTerm.value = '';
  connectionTested.value = false;
  connectionValid.value = false;
  systemConfigError.value = null;
  customConfigError.value = null;
  hasSystemConfig.value = true;
  availableModels.value = [];
  advancedSettingsVisible.value = false;
  maxCompletionTokens.value = '';
  temperature.value = '';
  resetModelTest();

  // Always test connection and load models when modal opens
  testAndLoadModels();
};

// Watch for modal open/close
watch(() => props.open, (newValue) => {
  console.log('Modal open changed to:', newValue);
  if (newValue) {
    initializeForm();
  }
}, {immediate: true});

// Watch for changes in custom API settings
watch([() => trialData.value.api_key, () => trialData.value.base_url], () => {
  connectionTested.value = false;
  connectionValid.value = false;
  customConfigError.value = null;
  resetModelTest();

  // Clear model selection when settings change
  trialData.value.llm_model = '';
  availableModels.value = [];

  // If custom settings are provided, test them
  if (hasCustomApiSettings.value) {
    // Debounce the API call to avoid too many requests while typing
    clearTimeout(window.customSettingsTimeout);
    window.customSettingsTimeout = setTimeout(() => {
      testAndLoadModels(trialData.value.api_key, trialData.value.base_url);
    }, 1000);
  } else {
    // If custom settings are cleared, test system config
    testAndLoadModels();
  }
});

// Watch for model or schema selection changes - reset model test when either changes
watch([() => trialData.value.llm_model, () => trialData.value.schema_id], ([newModel, newSchema], [oldModel, oldSchema]) => {
  if (newModel !== oldModel || newSchema !== oldSchema) {
    resetModelTest();
  }
});

// Filter documents based on search term
const filteredDocuments = computed(() => {
  if (!searchTerm.value) {
    return props.documents;
  }
  const term = searchTerm.value.toLowerCase();
  return props.documents.filter(doc => {
    const fileName = doc.original_file?.file_name || '';
    return fileName.toLowerCase().includes(term);
  });
});

const selectedSchema = computed(() => {
  if (!trialData.value.schema_id) return null;
  return props.schemas.find(schema => schema.id.toString() === trialData.value.schema_id);
});

const selectedPrompt = computed(() => {
  if (!trialData.value.prompt_id) return null;
  return props.prompts.find(prompt => prompt.id.toString() === trialData.value.prompt_id);
});

// Check if custom API settings are provided
const hasCustomApiSettings = computed(() => {
  return trialData.value.api_key.trim() || trialData.value.base_url.trim();
});

// Check if system has valid configuration
const hasValidSystemConfig = computed(() => {
  return hasSystemConfig.value && !systemConfigError.value && !hasCustomApiSettings.value;
});

// Check if custom configuration is valid
const hasValidCustomConfig = computed(() => {
  return hasCustomApiSettings.value && connectionTested.value && connectionValid.value && !customConfigError.value;
});

// Check if any configuration is valid
const hasValidConfig = computed(() => {
  return hasValidSystemConfig.value || hasValidCustomConfig.value;
});

// Form validation - NOW REQUIRES MODEL TESTING
const isFormValid = computed(() => {
  const basicValidation = trialData.value.schema_id &&
      trialData.value.prompt_id &&
      trialData.value.document_ids.length > 0 &&
      trialData.value.llm_model &&
      availableModels.value.length > 0;

  // Must have valid configuration (either system or custom)
  const configValid = hasValidConfig.value;

  // MANDATORY: Model must be tested and valid
  const modelValidated = modelTested.value && modelValid.value;

  return basicValidation && configValid && modelValidated;
});

// Get current error message
const currentError = computed(() => {
  if (hasCustomApiSettings.value) {
    return customConfigError.value;
  }
  return systemConfigError.value;
});

// Get configuration status
const configStatus = computed(() => {
  if (isTestingConnection.value || isLoadingModels.value) {
    return {type: 'loading', message: 'Testing configuration...'};
  }

  if (hasCustomApiSettings.value) {
    if (!connectionTested.value) {
      return {type: 'warning', message: 'Custom API settings need to be tested'};
    }
    if (!connectionValid.value) {
      return {type: 'error', message: customConfigError.value || 'Custom API connection failed'};
    }
    if (availableModels.value.length === 0) {
      return {type: 'error', message: 'No models available with current settings'};
    }
    return {type: 'success', message: `Custom API connected - ${availableModels.value.length} models available`};
  } else {
    if (!hasSystemConfig.value) {
      return {
        type: 'error',
        message: 'System configuration incomplete - please contact administrator or use custom settings'
      };
    }
    if (systemConfigError.value) {
      return {
        type: 'error',
        message: `System configuration error - please contact administrator: ${systemConfigError.value}`
      };
    }
    if (availableModels.value.length === 0) {
      return {type: 'error', message: 'No models available - please contact administrator'};
    }
    return {type: 'success', message: `System configuration active - ${availableModels.value.length} models available`};
  }
});

// Get model test status
const modelTestStatus = computed(() => {
  if (!trialData.value.llm_model || !trialData.value.schema_id) {
    return {type: 'none', message: 'Select a model and schema first'};
  }

  if (isTestingModel.value) {
    return {type: 'loading', message: 'Testing model with schema...'};
  }

  if (!modelTested.value) {
    return {type: 'warning', message: 'Model must be tested with schema before creating trial'};
  }

  if (!modelValid.value) {
    return {type: 'error', message: modelTestError.value || 'Model test failed'};
  }

  return {type: 'success', message: `Model '${trialData.value.llm_model}' supports the selected schema`};
});

// Toggle document selection
const toggleDocumentSelection = (docId) => {
  const index = trialData.value.document_ids.indexOf(docId);
  if (index === -1) {
    trialData.value.document_ids.push(docId);
  } else {
    trialData.value.document_ids.splice(index, 1);
  }
};

// Select all documents
const selectAllDocuments = () => {
  trialData.value.document_ids = filteredDocuments.value.map(doc => doc.id);
};

// Clear document selection
const clearDocumentSelection = () => {
  trialData.value.document_ids = [];
};

// Handle create submission
const handleSubmit = () => {
  if (!isFormValid.value) {
    if (!modelTested.value || !modelValid.value) {
      toast.error('Please test the selected model with the schema before creating the trial');
    }
    return;
  }

  const formData = {
    name: trialData.value.name?.trim() || undefined,
    description: trialData.value.description?.trim() || undefined,
    schema_id: parseInt(trialData.value.schema_id),
    prompt_id: parseInt(trialData.value.prompt_id),
    document_ids: trialData.value.document_ids,
    llm_model: trialData.value.llm_model
  };

  // Only include custom API settings if they are provided and not empty
  if (trialData.value.api_key.trim()) {
    formData.api_key = trialData.value.api_key.trim();
  }
  if (trialData.value.base_url.trim()) {
    formData.base_url = trialData.value.base_url.trim();
  }

  // Add advanced options if any are set
  const advancedOptions = {};
  if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
    advancedOptions.max_completion_tokens = parseInt(maxCompletionTokens.value);
  }

  if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
    advancedOptions.temperature = Number(temperature.value);
  }


  if (Object.keys(advancedOptions).length > 0) {
    formData.advanced_options = advancedOptions;
  }

  emit('create', formData);
};

watch(() => open, (show) => {
  if (show) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
});

onMounted(() => {
  if (props.open) lockScroll();
});
watch(() => props.open, v => v ? lockScroll() : unlockScroll());
onUnmounted(unlockScroll);


const isDirty = computed(() => {
  // Example: check if anything in trialData is non-empty
  return !!(
      trialData.value.name ||
      trialData.value.description ||
      trialData.value.schema_id ||
      trialData.value.prompt_id ||
      trialData.value.document_ids.length > 0 ||
      trialData.value.llm_model ||
      trialData.value.api_key ||
      trialData.value.base_url
  );
});

// Ask for confirmation if dirty before close (background/cancel/close)
const tryClose = () => {
  if (isDirty.value) {
    if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close');
    }
  } else {
    emit('close');
  }
};

// Handle click on the glassy background to dismiss
const handleBackdropClick = (e) => {
  if (e.target === e.currentTarget) {
    tryClose();
  }
};

</script>


<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity .2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
