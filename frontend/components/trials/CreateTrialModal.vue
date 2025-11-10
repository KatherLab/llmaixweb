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
                <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
              </svg>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-0 md:p-8 bg-white">
            <div class="grid md:grid-cols-2 gap-8">
              <!-- LEFT COLUMN -->
              <div>
                <!-- Name / Description -->
                <div
                  class="mb-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-xl border border-blue-100 shadow flex items-center px-6 py-5 gap-4"
                >
                  <div class="flex-shrink-0">
                    <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                      />
                    </svg>
                  </div>
                  <div class="w-full">
                    <div class="grid grid-cols-1 gap-4">
                      <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide"
                          >Trial Name <span class="text-gray-400 font-normal">(optional)</span></label
                        >
                        <input
                          v-model="trialData.name"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                          maxlength="100"
                          placeholder="E.g. Contract Extraction Run Q3"
                        />
                      </div>
                      <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-1 tracking-wide"
                          >Description <span class="text-gray-400 font-normal">(optional)</span></label
                        >
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

                <!-- Prompt / Schema / Model -->
                <div class="mb-8 bg-white border rounded-xl p-6 shadow">
                  <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-1"
                      >Prompt <span class="text-red-500">*</span></label
                    >
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
                        <p v-if="selectedPrompt.description" class="mb-1 text-gray-600">
                          {{ selectedPrompt.description }}
                        </p>
                        <div v-if="selectedPrompt.system_prompt" class="font-mono text-xs mb-1">
                          Sys: {{ selectedPrompt.system_prompt }}
                        </div>
                        <div v-if="selectedPrompt.user_prompt" class="font-mono text-xs">
                          User: {{ selectedPrompt.user_prompt }}
                        </div>
                      </div>
                    </details>
                  </div>

                  <div class="mb-4">
                    <label class="block text-sm font-semibold text-gray-700 mb-1"
                      >Schema <span class="text-red-500">*</span></label
                    >
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
                      <pre
                        v-if="selectedSchema"
                        class="bg-gray-50 border rounded p-2 mt-1 max-h-32 overflow-auto font-mono text-xs"
                      >{{ JSON.stringify(selectedSchema.schema_definition, null, 2) }}</pre>
                    </details>
                  </div>

                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-1"
                      >LLM Model <span class="text-red-500">*</span></label
                    >
                    <select
                      v-model="trialData.llm_model"
                      :disabled="isLoadingModels || isTestingConnection || availableModels.length === 0"
                      class="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    >
                      <option disabled value="">
                        {{
                          isLoadingModels || isTestingConnection
                            ? 'Loading models...'
                            : availableModels.length === 0
                            ? 'No models available'
                            : 'Select a model'
                        }}
                      </option>
                      <option v-for="model in availableModels" :key="model" :value="model">
                        {{ model }}
                      </option>
                    </select>
                    <div v-if="configStatus.type === 'error'" class="text-xs text-red-500 mt-1">
                      {{ configStatus.message }}
                    </div>
                  </div>
                </div>

                <!-- Advanced toggles + sections -->
                <div>
                  <div class="flex items-center gap-4 mb-2">
                    <button
                      class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
                      type="button"
                      @click="advancedSettingsVisible = !advancedSettingsVisible"
                    >
                      <span>{{ advancedSettingsVisible ? 'Hide' : 'Show' }} Advanced Settings</span>
                      <svg
                        :class="{ 'rotate-180': advancedSettingsVisible }"
                        class="h-4 w-4 ml-1 transition-transform"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                      </svg>
                    </button>
                    <button
                      class="text-blue-600 hover:text-blue-800 text-sm flex items-center"
                      type="button"
                      @click="advancedOptionsVisible = !advancedOptionsVisible"
                    >
                      <span>{{ advancedOptionsVisible ? 'Hide' : 'Use' }} Custom API Settings</span>
                      <svg
                        :class="{ 'rotate-180': advancedOptionsVisible }"
                        class="h-4 w-4 ml-1 transition-transform"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                      </svg>
                    </button>
                  </div>

                  <!-- Advanced Settings -->
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
                        Controls randomness. Lower values make outputs more focused; higher values make them more
                        random. Typical: 0.0–1.0
                      </p>
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Reasoning Effort <span class="text-gray-400 font-normal">(optional)</span>
                      </label>
                      <select
                        v-model="reasoningEffort"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">Use model default</option>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                      <p class="mt-1 text-xs text-gray-500">
                        Hints the model how much compute to spend on chain-of-thought/reasoning. Not all models/APIs
                        support this.
                      </p>
                    </div>
                  </div>

                  <!-- Custom API Settings -->
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

                <!-- Model test card -->
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
                        <svg v-if="modelTestStatus.type === 'loading'" class="animate-spin w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'warning'" class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 3 1.732 3z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'error'" class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else-if="modelTestStatus.type === 'success'" class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                        </svg>
                        <svg v-else class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
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
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
                        </svg>
                        {{ isTestingModel ? 'Testing...' : 'Test Model' }}
                      </button>
                    </div>
                    <div v-if="modelTestStatus.type === 'warning'" class="mt-3 p-3 bg-yellow-100 border border-yellow-200 rounded-md">
                      <p class="text-yellow-800 text-sm">
                        <strong>Required:</strong> You must test the selected model with the schema to ensure
                        compatibility before creating a trial.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- RIGHT COLUMN -->
              <div>
                <div class="bg-white border rounded-xl p-6 shadow flex flex-col h-full">
                  <div class="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                    <span class="block text-sm font-semibold text-gray-700"
                      >Select Documents <span class="text-red-500">*</span></span
                    >
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

                  <!-- INDIVIDUAL (server-side pagination) -->
                  <div v-if="documentSelectionMode === 'individual'" class="mt-4 flex-1 flex flex-col">
                    <div class="flex gap-2 mb-3">
                      <input
                        v-model="searchTerm"
                        class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Search documents (text or filename)…"
                        type="text"
                      />
                      <button
                        class="px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md"
                        title="Select all matching documents"
                        @click="selectAllDocuments"
                        :disabled="isSelectingAll || isLoadingDocs"
                      >
                        {{ isSelectingAll ? 'Selecting…' : 'Select All' }}
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
                      <div v-if="docsError" class="p-4 text-center text-red-600 text-sm">
                        {{ docsError }}
                      </div>

                      <div v-else-if="isLoadingDocs" class="p-6 text-center text-gray-500">
                        <LoadingSpinner />
                      </div>

                      <div v-else-if="docsPage.length === 0" class="p-4 text-center text-gray-500">
                        No documents match your criteria
                      </div>

                      <div v-else class="max-h-[400px] overflow-y-auto">
                        <div
                          v-for="doc in docsPage"
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
                            <div class="font-medium">
                              {{ doc.document_name || doc.original_file?.file_name || `Document #${doc.id}` }}
                            </div>

                            <div
                              v-if="doc.document_name && doc.original_file?.file_name && doc.document_name !== doc.original_file.file_name"
                              class="text-xs text-gray-400 italic"
                            >
                              (Original: {{ doc.original_file.file_name }})
                            </div>

                            <div class="text-xs text-gray-500">
                              Config: {{ doc.preprocessing_config?.name || 'N/A' }} •
                              Created: {{ formatDate(doc.created_at) }}
                            </div>
                          </div>
                        </div>
                      </div>

                      <!-- Pager -->
                      <div class="px-3 py-2 flex items-center justify-between text-sm bg-white">
                        <div>
                          <span class="font-medium">{{ totalDocs }}</span> total
                          <span class="text-gray-400">•</span>
                          page <span class="font-medium">{{ page }}</span>
                          /
                          {{ Math.max(1, Math.ceil(totalDocs / pageSize)) }}
                        </div>
                        <div class="flex items-center gap-2">
                          <button
                            class="px-3 py-1 rounded-md bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
                            :disabled="page <= 1 || isLoadingDocs"
                            @click="page = Math.max(1, page - 1)"
                          >
                            Prev
                          </button>
                          <button
                            class="px-3 py-1 rounded-md bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
                            :disabled="page >= Math.ceil(totalDocs / pageSize) || isLoadingDocs"
                            @click="page = page + 1"
                          >
                            Next
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- GROUPS -->
                  <div v-else-if="documentSelectionMode === 'groups'" class="mt-4 flex-1 flex flex-col">
                    <div v-if="loadingGroups" class="text-center py-8">
                      <LoadingSpinner />
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

                  <!-- SMART -->
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
                      <button class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md" @click="selectRecentDocuments(7)">
                        Last 7 days
                      </button>
                      <button class="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded-md" @click="selectRecentDocuments(30)">
                        Last 30 days
                      </button>
                      <button
                        class="px-3 py-1 bg-blue-600 text-white hover:bg-blue-700 text-sm rounded-md"
                        @click="applySmartDateRange"
                        :disabled="!dateRange.start && !dateRange.end"
                        title="Apply explicit date range"
                      >
                        Apply Date Range
                      </button>
                    </div>

                    <div v-if="trialData.document_ids.length > 0" class="mt-4 p-3 bg-blue-50 rounded-lg">
                      <div class="flex items-center justify-between">
                        <span class="text-sm font-medium text-blue-900">
                          {{ trialData.document_ids.length }}
                          document{{ trialData.document_ids.length > 1 ? 's' : '' }} selected
                        </span>
                        <div class="flex items-center gap-2">
                          <button
                            class="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                            type="button"
                            @click="showSelectedDocs = !showSelectedDocs"
                          >
                            <span v-if="!showSelectedDocs">Show</span>
                            <span v-else>Hide</span>
                            <svg :class="{ 'rotate-180': showSelectedDocs }" class="w-4 h-4 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path d="M19 9l-7 7-7-7" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
                            </svg>
                          </button>
                          <button class="text-sm text-blue-600 hover:text-blue-800" @click="clearDocumentSelection">
                            Clear
                          </button>
                        </div>
                      </div>
                      <transition name="fade">
                        <div
                          v-show="showSelectedDocs"
                          class="mt-2 bg-white rounded shadow p-2 max-h-40 overflow-y-auto border border-blue-100"
                        >
                          <ul class="text-xs text-gray-800 space-y-1">
                            <li v-for="docId in trialData.document_ids" :key="docId">
                              {{ getDocLabel(docId) }}
                            </li>
                          </ul>
                        </div>
                      </transition>
                    </div>
                  </div>
                </div>
              </div>
              <!-- end right -->
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { formatDate } from '@/utils/formatters.js';
import { api } from '@/services/api.js';
import { useToast } from 'vue-toastification';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const toast = useToast();

const props = defineProps({
  open: { type: Boolean, required: true },
  documents: { type: Array, required: true }, // kept for compatibility; Individual tab now uses backend pagination
  schemas: { type: Array, required: true },
  prompts: { type: Array, default: () => [] },
  projectId: { type: [String, Number], required: true }
});

const emit = defineEmits(['close', 'create', 'create-group']);

/* -------------------------------------------------------
 * General trial state
 * -----------------------------------------------------*/
const trialData = ref({
  name: '',
  description: '',
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
const dateRange = ref({ start: '', end: '' });
const showSelectedDocs = ref(false);
const isSelectingAll = ref(false);

/* -------------------------------------------------------
 * Scroll lock
 * -----------------------------------------------------*/
const lockScroll = () => { document.body.style.overflow = 'hidden'; };
const unlockScroll = () => { document.body.style.overflow = ''; };

/* -------------------------------------------------------
 * Backend-driven: Document groups / previous trials / configs
 * -----------------------------------------------------*/
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
    previousTrials.value = response.data.filter(trial => trial.status === 'completed' && trial.document_ids.length > 0);
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

/* -------------------------------------------------------
 * Server-side pagination for Individual tab
 * -----------------------------------------------------*/
const docsPage = ref([]);     // current page items
const totalDocs = ref(0);
const pageSize = ref(50);     // tweak as needed (API allows up to 500)
const page = ref(1);          // 1-based
const isLoadingDocs = ref(false);
const docsError = ref(null);

const documentLookup = ref(new Map()); // id -> label cache

let debounceTimer;
const debounce = (fn, ms = 350) => {
  return (...args) => {
    if (debounceTimer) window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => fn(...args), ms);
  };
};

const toISODateStart = (d) => (d ? new Date(`${d}T00:00:00.000Z`).toISOString() : undefined);
const toISODateEndExclusive = (d) => (d ? new Date(`${d}T23:59:59.999Z`).toISOString() : undefined);

const buildDocQueryParams = (opts = {}) => {
  const params = {
    limit: opts.limit != null ? opts.limit : pageSize.value,
    offset: opts.offset != null ? opts.offset : (page.value - 1) * pageSize.value
  };
  if (opts.search && opts.search.trim()) params.search = opts.search.trim();
  if (opts.config_id != null) params.config_id = opts.config_id;
  if (opts.date_from) params.date_from = opts.date_from;
  if (opts.date_to) params.date_to = opts.date_to;
  return params;
};

const fetchDocuments = async ({ reset = false } = {}) => {
  if (documentSelectionMode.value !== 'individual') return;
  if (reset) page.value = 1;

  isLoadingDocs.value = true;
  docsError.value = null;

  try {
    const params = buildDocQueryParams({ search: searchTerm.value });
    const { data } = await api.get(`/project/${props.projectId}/document`, { params });
    docsPage.value = data.items || [];
    totalDocs.value = data.total || 0;

    for (const d of docsPage.value) {
      const label = d.document_name || d?.original_file?.file_name || `Document #${d.id}`;
      documentLookup.value.set(d.id, label);
    }
  } catch (e) {
    console.error('Failed to fetch documents page:', e);
    docsError.value = e?.response?.data?.detail || e?.message || 'Failed to load documents';
    docsPage.value = [];
    totalDocs.value = 0;
  } finally {
    isLoadingDocs.value = false;
  }
};

// Fetch all matching IDs for Smart selections (looped pages)
const fetchAllDocumentIds = async (q = {}) => {
  const ids = [];
  let offset = 0;
  const limit = 500; // API max

  try {
    let params = buildDocQueryParams({ ...q, limit, offset });
    let resp = await api.get(`/project/${props.projectId}/document`, { params });
    const total = resp.data.total ?? (resp.data.items?.length ?? 0);

    const pushIds = (items) => {
      for (const d of items) {
        ids.push(d.id);
        const label = d.document_name || d?.original_file?.file_name || `Document #${d.id}`;
        documentLookup.value.set(d.id, label);
      }
    };

    pushIds(resp.data.items ?? []);

    while (ids.length < total) {
      offset += limit;
      params = buildDocQueryParams({ ...q, limit, offset });
      resp = await api.get(`/project/${props.projectId}/document`, { params });
      pushIds(resp.data.items ?? []);
    }
  } catch (e) {
    console.error('fetchAllDocumentIds error:', e);
    toast.error('Failed to load matching documents');
  }

  return ids;
};

const getDocLabel = (docId) => documentLookup.value.get(docId) || `Document #${docId}`;

/* -------------------------------------------------------
 * Smart tab actions now call backend
 * -----------------------------------------------------*/
const filterByPreprocessingConfig = async () => {
  if (!selectedConfigId.value) {
    trialData.value.document_ids = [];
    toast.info('Showing all configurations — selection cleared.');
    return;
  }
  const configId = parseInt(selectedConfigId.value);
  const ids = await fetchAllDocumentIds({ config_id: configId });
  trialData.value.document_ids = ids;
  toast.success(`Selected ${ids.length} documents for this configuration`);
};

const selectRecentDocuments = async (days) => {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  const ids = await fetchAllDocumentIds({ date_from: cutoff.toISOString() });
  trialData.value.document_ids = ids;
  toast.success(`Selected ${ids.length} documents from the last ${days} days`);
};

const applySmartDateRange = async () => {
  const fromISO = toISODateStart(dateRange.value.start);
  const toISO = toISODateEndExclusive(dateRange.value.end);
  const ids = await fetchAllDocumentIds({ date_from: fromISO, date_to: toISO });
  trialData.value.document_ids = ids;
  toast.success(`Selected ${ids.length} documents in date range`);
};

/* -------------------------------------------------------
 * Advanced options / Model testing (unchanged logic)
 * -----------------------------------------------------*/
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
const reasoningEffort = ref('');

// Connection + models
const testAndLoadModels = async (apiKey = '', baseUrl = '') => {
  isTestingConnection.value = true;
  connectionTested.value = false;
  connectionValid.value = false;
  availableModels.value = [];
  systemConfigError.value = null;
  customConfigError.value = null;

  resetModelTest();

  try {
    const params = {};
    if ((apiKey || '').trim()) params.api_key = apiKey.trim();
    if ((baseUrl || '').trim()) params.base_url = baseUrl.trim();

    const testResponse = await api.post('/project/llm/test-connection', null, { params });

    if (testResponse.data.success) {
      connectionValid.value = true;
      connectionTested.value = true;

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
    connectionValid.value = false;
    connectionTested.value = true;
    const errorMsg = error?.response?.data?.message || error?.response?.data?.detail || error?.message;
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

const loadModels = async (apiKey = '', baseUrl = '') => {
  isLoadingModels.value = true;
  try {
    const params = {};
    if ((apiKey || '').trim()) params.api_key = apiKey.trim();
    if ((baseUrl || '').trim()) params.base_url = baseUrl.trim();

    const response = await api.get('/project/llm/models', { params });

    if (response.data.success) {
      availableModels.value = response.data.models || [];

      // Clear previous model selection when models change
      if (trialData.value.llm_model && !availableModels.value.includes(trialData.value.llm_model)) {
        trialData.value.llm_model = '';
        resetModelTest();
      }
    } else {
      availableModels.value = [];
      throw new Error(response.data.message || 'Failed to load models');
    }
  } catch (error) {
    availableModels.value = [];
    throw error;
  } finally {
    isLoadingModels.value = false;
  }
};

const resetModelTest = () => {
  modelTested.value = false;
  modelValid.value = false;
  modelTestError.value = null;
};

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

    if ((trialData.value.api_key || '').trim()) params.api_key = trialData.value.api_key.trim();
    if ((trialData.value.base_url || '').trim()) params.base_url = trialData.value.base_url.trim();

    if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
      params.max_completion_tokens = parseInt(maxCompletionTokens.value);
    }
    if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
      params.temperature = Number(temperature.value);
    }
    if (reasoningEffort.value) {
      params.reasoning_effort = reasoningEffort.value;
    }

    const response = await api.post('/project/llm/test-model-schema', null, { params });

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
    modelTested.value = true;
    modelValid.value = false;
    const errorMsg = error?.response?.data?.message || error?.response?.data?.detail || error?.message;
    modelTestError.value = errorMsg;
    toast.error(`Model test failed: ${errorMsg}`);
  } finally {
    isTestingModel.value = false;
  }
};

/* -------------------------------------------------------
 * Initialize form on open
 * -----------------------------------------------------*/
const initializeForm = () => {
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
  reasoningEffort.value = '';
  resetModelTest();

  testAndLoadModels();
};

/* -------------------------------------------------------
 * Selections & helpers
 * -----------------------------------------------------*/
const selectedSchema = computed(() => {
  if (!trialData.value.schema_id) return null;
  return props.schemas.find(schema => schema.id.toString() === trialData.value.schema_id);
});

const selectedPrompt = computed(() => {
  if (!trialData.value.prompt_id) return null;
  return props.prompts.find(prompt => prompt.id.toString() === trialData.value.prompt_id);
});

const hasCustomApiSettings = computed(() => {
  return (trialData.value.api_key || '').trim() || (trialData.value.base_url || '').trim();
});
const hasValidSystemConfig = computed(() => hasSystemConfig.value && !systemConfigError.value && !hasCustomApiSettings.value);
const hasValidCustomConfig = computed(() => hasCustomApiSettings.value && connectionTested.value && connectionValid.value && !customConfigError.value);
const hasValidConfig = computed(() => hasValidSystemConfig.value || hasValidCustomConfig.value);

const isFormValid = computed(() => {
  const basicValidation =
    trialData.value.schema_id &&
    trialData.value.prompt_id &&
    trialData.value.document_ids.length > 0 &&
    trialData.value.llm_model &&
    availableModels.value.length > 0;

  const configValid = hasValidConfig.value;
  const modelValidated = modelTested.value && modelValid.value;

  return basicValidation && configValid && modelValidated;
});

const currentError = computed(() => (hasCustomApiSettings.value ? customConfigError.value : systemConfigError.value));

const configStatus = computed(() => {
  if (isTestingConnection.value || isLoadingModels.value) {
    return { type: 'loading', message: 'Testing configuration...' };
  }

  if (hasCustomApiSettings.value) {
    if (!connectionTested.value) return { type: 'warning', message: 'Custom API settings need to be tested' };
    if (!connectionValid.value) return { type: 'error', message: customConfigError.value || 'Custom API connection failed' };
    if (availableModels.value.length === 0) return { type: 'error', message: 'No models available with current settings' };
    return { type: 'success', message: `Custom API connected - ${availableModels.value.length} models available` };
  } else {
    if (!hasSystemConfig.value) return { type: 'error', message: 'System configuration incomplete - please contact administrator or use custom settings' };
    if (systemConfigError.value) return { type: 'error', message: `System configuration error - please contact administrator: ${systemConfigError.value}` };
    if (availableModels.value.length === 0) return { type: 'error', message: 'No models available - please contact administrator' };
    return { type: 'success', message: `System configuration active - ${availableModels.value.length} models available` };
  }
});

const modelTestStatus = computed(() => {
  if (!trialData.value.llm_model || !trialData.value.schema_id) {
    return { type: 'none', message: 'Select a model and schema first' };
  }
  if (isTestingModel.value) return { type: 'loading', message: 'Testing model with schema...' };
  if (!modelTested.value) return { type: 'warning', message: 'Model must be tested with schema before creating trial' };
  if (!modelValid.value) return { type: 'error', message: modelTestError.value || 'Model test failed' };
  return { type: 'success', message: `Model '${trialData.value.llm_model}' supports the selected schema` };
});

const toggleDocumentSelection = (docId) => {
  const i = trialData.value.document_ids.indexOf(docId);
  if (i === -1) trialData.value.document_ids.push(docId);
  else trialData.value.document_ids.splice(i, 1);
};

const selectAllDocuments = async () => {
  if (isSelectingAll.value) return;
  isSelectingAll.value = true;
  try {
    // Use the backend to fetch ALL matching IDs (ignores pagination)
    const ids = await fetchAllDocumentIds({ search: searchTerm.value });
    trialData.value.document_ids = Array.from(new Set([
      ...trialData.value.document_ids,
      ...ids
    ]));
    toast.success(`Selected all ${ids.length} matching documents`);
  } catch (e) {
    console.error(e);
    toast.error('Could not select all documents');
  } finally {
    isSelectingAll.value = false;
  }
};


const clearDocumentSelection = () => {
  trialData.value.document_ids = [];
};

/* -------------------------------------------------------
 * Submission
 * -----------------------------------------------------*/
const handleSubmit = () => {
  if (!isFormValid.value) {
    if (!modelTested.value || !modelValid.value) toast.error('Please test the selected model with the schema before creating the trial');
    return;
  }

  const formData = {
    name: (trialData.value.name || '').trim() || undefined,
    description: (trialData.value.description || '').trim() || undefined,
    schema_id: parseInt(trialData.value.schema_id),
    prompt_id: parseInt(trialData.value.prompt_id),
    document_ids: trialData.value.document_ids,
    llm_model: trialData.value.llm_model
  };

  if ((trialData.value.api_key || '').trim()) formData.api_key = trialData.value.api_key.trim();
  if ((trialData.value.base_url || '').trim()) formData.base_url = trialData.value.base_url.trim();

  const advancedOptions = {};
  if (maxCompletionTokens.value && parseInt(maxCompletionTokens.value) > 0) {
    advancedOptions.max_completion_tokens = parseInt(maxCompletionTokens.value);
  }
  if (temperature.value !== '' && !isNaN(Number(temperature.value))) {
    advancedOptions.temperature = Number(temperature.value);
  }
  if (reasoningEffort.value) {
    advancedOptions.reasoning_effort = reasoningEffort.value;
  }
  if (Object.keys(advancedOptions).length > 0) {
    formData.advanced_options = advancedOptions;
  }

  emit('create', formData);
};

/* -------------------------------------------------------
 * Close with confirmation
 * -----------------------------------------------------*/
const isDirty = computed(() => {
  return !!(
    trialData.value.name ||
    trialData.value.description ||
    trialData.value.schema_id ||
    trialData.value.prompt_id ||
    (trialData.value.document_ids && trialData.value.document_ids.length > 0) ||
    trialData.value.llm_model ||
    trialData.value.api_key ||
    trialData.value.base_url
  );
});

const tryClose = () => {
  if (isDirty.value) {
    if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
      emit('close');
    }
  } else {
    emit('close');
  }
};

const handleBackdropClick = (e) => {
  if (e.target === e.currentTarget) {
    tryClose();
  }
};

/* -------------------------------------------------------
 * Watchers
 * -----------------------------------------------------*/
watch(() => props.open, (newValue) => {
  if (newValue) {
    initializeForm();
  }
}, { immediate: true });

watch([() => trialData.value.api_key, () => trialData.value.base_url], () => {
  connectionTested.value = false;
  connectionValid.value = false;
  customConfigError.value = null;
  resetModelTest();

  trialData.value.llm_model = '';
  availableModels.value = [];

  if (hasCustomApiSettings.value) {
    clearTimeout(window.customSettingsTimeout);
    window.customSettingsTimeout = setTimeout(() => {
      testAndLoadModels(trialData.value.api_key, trialData.value.base_url);
    }, 1000);
  } else {
    testAndLoadModels();
  }
});

watch([() => trialData.value.llm_model, () => trialData.value.schema_id], ([newModel, newSchema], [oldModel, oldSchema]) => {
  if (newModel !== oldModel || newSchema !== oldSchema) {
    resetModelTest();
  }
});

watch([() => maxCompletionTokens.value, () => temperature.value, () => reasoningEffort.value], () => {
  resetModelTest();
});

// NEW: when switching tabs
watch(documentSelectionMode, (mode) => {
  if (mode === 'individual') fetchDocuments({ reset: true });
  if (mode === 'groups' && documentGroups.value.length === 0) loadDocumentGroups();
  if (mode === 'smart') {
    if (previousTrials.value.length === 0) loadPreviousTrials();
    if (preprocessingConfigs.value.length === 0) loadPreprocessingConfigs();
  }
});

// NEW: debounced search for Individual tab
const debouncedSearch = debounce(() => fetchDocuments({ reset: true }), 400);
watch(() => searchTerm.value, () => {
  if (documentSelectionMode.value === 'individual') debouncedSearch();
});

// NEW: react to page changes
watch(() => page.value, () => {
  if (documentSelectionMode.value === 'individual') fetchDocuments();
});

// keep original scroll lock
watch(() => props.open, v => v ? lockScroll() : unlockScroll());

onMounted(() => {
  if (props.open) lockScroll();
  if (documentSelectionMode.value === 'individual') fetchDocuments({ reset: true });
});
onUnmounted(unlockScroll);
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
