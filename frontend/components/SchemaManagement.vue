<template>
  <div class="p-6">
    <!-- Modern Tab Navigation -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex" aria-label="Tabs">
          <button
            @click="activeSection = 'schemas'"
            :class="[
              activeSection === 'schemas'
                ? 'border-indigo-500 text-indigo-600 bg-indigo-50/50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'group relative min-w-0 flex-1 overflow-hidden py-4 px-6 text-sm font-medium text-center border-b-2 hover:bg-gray-50 focus:z-10 transition-all duration-200'
            ]"
          >
            <div class="flex items-center justify-center space-x-2">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
              </svg>
              <span>JSON Schemas</span>
              <span v-if="schemas.length > 0" class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
                {{ schemas.length }}
              </span>
            </div>
          </button>

          <button
            @click="activeSection = 'prompts'"
            :class="[
              activeSection === 'prompts'
                ? 'border-indigo-500 text-indigo-600 bg-indigo-50/50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              'group relative min-w-0 flex-1 overflow-hidden py-4 px-6 text-sm font-medium text-center border-b-2 hover:bg-gray-50 focus:z-10 transition-all duration-200'
            ]"
          >
            <div class="flex items-center justify-center space-x-2">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span>Extraction Prompts</span>
              <span v-if="prompts.length > 0" class="ml-2 bg-gray-100 text-gray-600 py-0.5 px-2 rounded-full text-xs">
                {{ prompts.length }}
              </span>
            </div>
          </button>
        </nav>
      </div>
    </div>

    <!-- Schemas Section -->
    <div v-if="activeSection === 'schemas'">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-lg font-medium text-gray-900">JSON Schemas</h2>
          <p class="mt-1 text-sm text-gray-500">Define the structure for information extraction</p>
        </div>
        <button
          @click="showCreateModal = true"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition-colors duration-200"
        >
          <svg class="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          Create Schema
        </button>
      </div>

      <div v-if="isLoading" class="flex justify-center py-12">
        <svg class="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>

      <div v-else-if="schemas.length === 0" class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-xl p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
        <p class="mt-2 text-sm text-gray-600">No schemas created yet</p>
        <p class="mt-1 text-sm text-gray-500">Create a schema to define the structure for information extraction</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          v-for="schema in schemas"
          :key="schema.id"
          class="bg-white border rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow duration-200"
        >
          <div class="p-4 border-b">
            <div class="flex justify-between items-start">
              <h3 class="text-lg font-medium text-gray-900">{{ schema.schema_name }}</h3>
              <div class="flex space-x-2">
                <button
                  @click="viewSchema(schema)"
                  class="text-indigo-600 hover:text-indigo-800 transition-colors duration-200"
                  title="View Schema"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                    <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                  </svg>
                </button>
                <button
                  @click="editSchema(schema)"
                  class="text-gray-600 hover:text-gray-800 transition-colors duration-200"
                  title="Edit Schema"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button
                  @click="confirmDelete(schema)"
                  class="text-gray-600 hover:text-red-600 transition-colors duration-200"
                  title="Delete Schema"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
            <p class="mt-1 text-sm text-gray-500">Created: {{ formatDate(schema.created_at) }}</p>
          </div>
          <div class="bg-gray-50 p-4 max-h-64 overflow-auto">
            <pre class="text-xs text-gray-700">{{ formatJSON(schema.schema_definition) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- Prompts Section -->
    <div v-if="activeSection === 'prompts'">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-lg font-medium text-gray-900">Extraction Prompts</h2>
          <p class="mt-1 text-sm text-gray-500">Configure how the LLM extracts information from documents</p>
        </div>
        <button
          @click="showCreatePromptModal = true"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 transition-colors duration-200"
        >
          <svg class="h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          Create Prompt
        </button>
      </div>

      <div v-if="isLoadingPrompts" class="flex justify-center py-12">
        <svg class="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>

      <div v-else-if="prompts.length === 0" class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-xl p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        <p class="mt-2 text-sm text-gray-600">No prompts created yet</p>
        <p class="mt-1 text-sm text-gray-500">Create a prompt to guide the LLM in extracting information</p>
      </div>

      <div v-else class="grid grid-cols-1 gap-6">
        <div
          v-for="prompt in prompts"
          :key="prompt.id"
          class="bg-white border rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow duration-200"
        >
          <div class="p-6">
            <div class="flex justify-between items-start mb-4">
              <div>
                <h3 class="text-lg font-medium text-gray-900">{{ prompt.name }}</h3>
                <p v-if="prompt.description" class="mt-1 text-sm text-gray-500">{{ prompt.description }}</p>
                <p class="mt-2 text-xs text-gray-400">Created: {{ formatDate(prompt.created_at) }}</p>
              </div>
              <div class="flex space-x-2">
                <button
                  @click="viewPrompt(prompt)"
                  class="text-indigo-600 hover:text-indigo-800 transition-colors duration-200"
                  title="View Prompt"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                    <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                  </svg>
                </button>
                <button
                  @click="editPrompt(prompt)"
                  class="text-gray-600 hover:text-gray-800 transition-colors duration-200"
                  title="Edit Prompt"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button
                  @click="confirmDeletePrompt(prompt)"
                  class="text-gray-600 hover:text-red-600 transition-colors duration-200"
                  title="Delete Prompt"
                >
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Prompt Preview Cards -->
            <div class="space-y-3">
              <div v-if="prompt.system_prompt" class="bg-gray-50 rounded-lg p-4">
                <div class="flex items-center mb-2">
                  <span class="text-xs font-medium text-gray-500 uppercase tracking-wider">System Prompt</span>
                  <span v-if="prompt.system_prompt.includes('{document_content}')" class="ml-2 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                    Contains placeholder
                  </span>
                </div>
                <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ truncateText(prompt.system_prompt, 200) }}</p>
              </div>
              <div v-if="prompt.user_prompt" class="bg-blue-50 rounded-lg p-4">
                <div class="flex items-center mb-2">
                  <span class="text-xs font-medium text-blue-600 uppercase tracking-wider">User Prompt</span>
                  <span v-if="prompt.user_prompt.includes('{document_content}')" class="ml-2 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                    Contains placeholder
                  </span>
                </div>
                <p class="text-sm text-gray-700 whitespace-pre-wrap">{{ truncateText(prompt.user_prompt, 200) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Schema Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal || showEditModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md z-50"
        @click="cancelSchemaModal"
      >
        <div class="bg-white rounded-lg w-full h-[90vh] max-w-[1600px] my-8 flex flex-col mx-auto" @click.stop>
          <div class="p-6 border-b flex items-center justify-between flex-shrink-0">
            <h3 class="text-lg font-medium text-gray-900">
              {{ showEditModal ? 'Edit Schema' : 'Create New Schema' }}
            </h3>
          </div>

          <form @submit.prevent="showEditModal ? updateSchema() : createSchema()" class="flex flex-col flex-1 min-h-0">
            <div class="flex-1 flex flex-col min-h-0">
              <!-- Schema Name Input -->
              <div class="px-6 pt-4 pb-2 flex-shrink-0">
                <label for="schema-name" class="block text-sm font-medium text-gray-700">Schema Name</label>
                <input
                  id="schema-name"
                  v-model="schemaForm.schema_name"
                  class="mt-1 block w-full max-w-md border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="Enter schema name"
                  required
                />
              </div>

              <!-- Schema validation indicator -->
              <div class="px-6 pb-2 flex items-center space-x-2">
                <div v-if="schemaForm.schema_definition" class="flex items-center space-x-2 text-sm">
                  <div v-if="!schemaError" class="flex items-center text-green-600">
                    <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Valid JSON Schema</span>
                  </div>
                  <div v-else class="flex items-center text-red-600">
                    <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Invalid Schema</span>
                  </div>
                </div>
              </div>

              <!-- Tab Navigation -->
              <div class="px-6 border-b border-gray-200 flex-shrink-0">
                <nav class="-mb-px flex items-center justify-between">
                  <div class="flex space-x-8">
                    <button
                      type="button"
                      @click="activeTab = 'visual'"
                      :class="[
                        activeTab === 'visual'
                          ? 'border-indigo-500 text-indigo-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                        'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm'
                      ]"
                    >
                      <svg class="h-4 w-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zM21 5a2 2 0 00-2-2h-4a2 2 0 00-2 2v12a4 4 0 004 4h4a2 2 0 002-2V5z" />
                      </svg>
                      Visual Editor
                    </button>
                    <button
                      type="button"
                      @click="activeTab = 'raw'"
                      :class="[
                        activeTab === 'raw'
                          ? 'border-indigo-500 text-indigo-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                        'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm'
                      ]"
                    >
                      <svg class="h-4 w-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      Raw JSON
                    </button>
                  </div>

                  <div class="flex items-center space-x-4">
                    <!-- Advanced Features Toggle - Only show in Visual tab -->
                    <label v-if="activeTab === 'visual'" class="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        v-model="advancedMode"
                        class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span class="text-gray-700">Enable advanced features</span>
                    </label>

                    <!-- Split View Toggle - Only show in Visual tab -->
                    <label v-if="activeTab === 'visual'" class="flex items-center space-x-2 text-sm">
                      <input
                        type="checkbox"
                        v-model="splitView"
                        class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span class="text-gray-700">Split view</span>
                    </label>

                    <!-- Templates Button -->
                    <button
                      type="button"
                      @click="showTemplates = true"
                      class="text-sm text-indigo-600 hover:text-indigo-800 flex items-center"
                    >
                      <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      Templates
                    </button>
                  </div>
                </nav>
              </div>

              <!-- Tab Content -->
              <div class="flex-1 min-h-0" :class="splitView && activeTab === 'visual' ? 'flex' : ''">
                <!-- Visual Editor Tab -->
                <div
                  v-if="activeTab === 'visual' || (splitView && activeTab === 'visual')"
                  :class="[
                    'bg-gray-50',
                    splitView && activeTab === 'visual' ? 'w-1/2 border-r' : 'h-full'
                  ]"
                >
                  <VisualSchemaEditor
                    :schema="visualSchema"
                    @update:schema="updateVisualSchema"
                    :advanced-mode="advancedMode"
                  />
                </div>

                <!-- Raw JSON Tab -->
                <div
                  v-if="activeTab === 'raw' || (splitView && activeTab === 'visual')"
                  :class="[
                    'relative flex flex-col',
                    splitView && activeTab === 'visual' ? 'w-1/2' : 'h-full'
                  ]"
                >
                  <div class="flex-1 p-6 min-h-0">
                    <textarea
                      ref="rawJsonTextarea"
                      v-model="schemaForm.schema_definition"
                      @input="onRawSchemaChange"
                      @keydown="preserveCursorPosition"
                      class="block w-full h-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono resize-none"
                      placeholder='{"type": "object", "properties": {...}}'
                      required
                    ></textarea>
                    <button
                      type="button"
                      @click="formatJsonInput"
                      class="absolute top-8 right-8 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                      title="Format JSON"
                    >
                      Format
                    </button>
                  </div>
                </div>
              </div>

              <p v-if="schemaError" class="px-6 py-2 text-sm text-red-600 flex-shrink-0">{{ schemaError }}</p>
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t flex justify-end space-x-3 flex-shrink-0">
              <button
                type="button"
                class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                @click="cancelSchemaModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                :disabled="isSubmitting"
              >
                                <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ showEditModal ? 'Update' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Create/Edit Prompt Modal -->
    <Teleport to="body">
      <div
        v-if="showCreatePromptModal || showEditPromptModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md z-50"
        @click="cancelPromptModal"
      >
        <div class="bg-white rounded-xl w-full max-w-4xl my-8 mx-auto max-h-[90vh] flex flex-col shadow-2xl" @click.stop>
          <div class="p-6 border-b flex items-center justify-between flex-shrink-0">
            <h3 class="text-lg font-medium text-gray-900">
              {{ showEditPromptModal ? 'Edit Prompt' : 'Create New Prompt' }}
            </h3>
            <button @click="cancelPromptModal" class="text-gray-400 hover:text-gray-500">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="showEditPromptModal ? updatePrompt() : createPrompt()" class="flex flex-col flex-1 min-h-0">
            <div class="flex-1 overflow-y-auto p-6 space-y-6">
              <!-- Prompt Name and Description -->
              <div class="grid grid-cols-1 gap-4">
                <div>
                  <label for="prompt-name" class="block text-sm font-medium text-gray-700 mb-1">
                    Prompt Name <span class="text-red-500">*</span>
                  </label>
                  <input
                    id="prompt-name"
                    v-model="promptForm.name"
                    class="block w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    :class="{ 'border-red-300': !promptForm.name && isSubmitting }"
                    placeholder="e.g., Medical Document Extraction"
                    required
                    @blur="() => { if (!promptForm.name) toast.warning('Prompt name is required') }"
                  />
                  <p v-if="!promptForm.name && isSubmitting" class="mt-1 text-sm text-red-600">
                    This field is required
                  </p>
                </div>

                <div>
                  <label for="prompt-description" class="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    id="prompt-description"
                    v-model="promptForm.description"
                    rows="2"
                    class="block w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    placeholder="Describe what this prompt is designed to extract..."
                  />
                </div>
              </div>

              <!-- Placeholder Info Banner -->
              <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-blue-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-blue-800">Document Content Placeholder</h3>
                    <p class="mt-1 text-sm text-blue-700">
                      Use <code class="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded font-mono text-xs">{document_content}</code>
                      in your prompts where you want the document text to be inserted.
                    </p>
                  </div>
                </div>
              </div>

              <!-- System Prompt -->
              <div>
                <div class="flex items-center justify-between mb-2">
                  <label for="system-prompt" class="block text-sm font-medium text-gray-700">
                    System Prompt
                  </label>
                  <span v-if="promptForm.system_prompt?.includes('{document_content}')"
                        class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full flex items-center">
                    <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    Contains placeholder
                  </span>
                </div>
                <div class="relative">
                  <textarea
                    id="system-prompt"
                    v-model="promptForm.system_prompt"
                    @input="validatePromptPlaceholder"
                    rows="6"
                    class="block w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono text-sm"
                    :class="{
                      'pr-20': showPreviewSystem,
                      'border-amber-300': promptError && !promptForm.system_prompt?.includes('{document_content}') && !promptForm.user_prompt?.includes('{document_content}')
                    }"
                    placeholder="You are an AI assistant specialized in extracting structured information from documents..."
                  />
                  <button
                    v-if="promptForm.system_prompt"
                    type="button"
                    @click="togglePreview('system')"
                    class="absolute top-2 right-2 text-xs text-indigo-600 hover:text-indigo-800 bg-white px-2 py-1 rounded border border-gray-300"
                  >
                    {{ showPreviewSystem ? 'Hide' : 'Preview' }}
                  </button>
                </div>
              </div>


              <!-- User Prompt -->
              <div>
                <div class="flex items-center justify-between mb-2">
                  <label for="user-prompt" class="block text-sm font-medium text-gray-700">
                    User Prompt
                  </label>
                  <span v-if="promptForm.user_prompt?.includes('{document_content}')"
                        class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full flex items-center">
                    <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    Contains placeholder
                  </span>
                </div>
                <div class="relative">
                  <textarea
                    id="user-prompt"
                    v-model="promptForm.user_prompt"
                    @input="validatePromptPlaceholder"
                    rows="6"
                    class="block w-full border-gray-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono text-sm"
                    :class="{ 'pr-20': showPreviewUser }"
                    placeholder="Extract the following information from this document:&#10;&#10;{document_content}"
                  />
                  <button
                    v-if="promptForm.user_prompt"
                    type="button"
                    @click="togglePreview('user')"
                    class="absolute top-2 right-2 text-xs text-indigo-600 hover:text-indigo-800 bg-white px-2 py-1 rounded border border-gray-300"
                  >
                    {{ showPreviewUser ? 'Hide' : 'Preview' }}
                  </button>
                </div>
              </div>

              <!-- Preview Section -->
              <div v-if="showPreviewSystem || showPreviewUser" class="space-y-4">
                <h4 class="text-sm font-medium text-gray-700">Preview with Sample Document</h4>
                <div class="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div v-if="showPreviewSystem && promptForm.system_prompt" class="space-y-2">
                    <span class="text-xs font-medium text-gray-500 uppercase tracking-wider">System Message Preview</span>
                    <div class="bg-white rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap border border-gray-200">
                      {{ promptForm.system_prompt.replace('{document_content}', sampleDocument) }}
                    </div>
                  </div>
                  <div v-if="showPreviewUser && promptForm.user_prompt" class="space-y-2">
                    <span class="text-xs font-medium text-blue-600 uppercase tracking-wider">User Message Preview</span>
                    <div class="bg-blue-50 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap border border-blue-200">
                      {{ promptForm.user_prompt.replace('{document_content}', sampleDocument) }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- Validation Error -->
              <div v-if="promptError" class="bg-red-50 border border-red-200 rounded-lg p-4">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <p class="text-sm text-red-800">{{ promptError }}</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Modal Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t flex justify-between items-center flex-shrink-0">
              <div class="flex items-center space-x-2">
                <button
                  type="button"
                  @click="useTemplate"
                  class="text-sm text-indigo-600 hover:text-indigo-800 flex items-center"
                >
                  <svg class="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Use Template
                </button>
              </div>
              <div class="flex space-x-3">
                <button
                  type="button"
                  class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50"
                  @click="cancelPromptModal"
                >
                  Cancel
                </button>
                <div class="relative inline-flex">
                  <button
                      :disabled="isSubmitting || !isPromptValid"
                      class="inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      type="submit"
                      @mouseenter="showButtonTooltip = !isPromptValid"
                      @mouseleave="showButtonTooltip = false"
                  >
                    <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                         fill="none" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            fill="currentColor"></path>
                    </svg>
                    {{ showEditPromptModal ? 'Update' : 'Create' }}
                  </button>

                  <!-- Tooltip -->
                  <div v-if="showButtonTooltip && formErrors.length > 0"
                       class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 z-10">
                    <div class="bg-gray-900 text-white text-xs rounded-lg py-2 px-3 max-w-xs">
                      <div class="font-semibold mb-1">Please fix the following:</div>
                      <ul class="list-disc list-inside">
                        <li v-for="error in formErrors" :key="error">{{ error }}</li>
                      </ul>
                      <div class="absolute top-full left-1/2 transform -translate-x-1/2">
                        <div class="border-4 border-transparent border-t-gray-900"></div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- View Prompt Modal -->
    <Teleport to="body">
      <div
        v-if="showViewPromptModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showViewPromptModal = false"
      >
        <div class="bg-white rounded-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto" @click.stop>
          <div class="flex justify-between items-start mb-6">
            <div>
              <h3 class="text-lg font-medium text-gray-900">{{ currentPrompt?.name }}</h3>
              <p v-if="currentPrompt?.description" class="mt-1 text-sm text-gray-500">{{ currentPrompt.description }}</p>
            </div>
            <button @click="showViewPromptModal = false" class="text-gray-400 hover:text-gray-500">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="space-y-4">
            <div v-if="currentPrompt?.system_prompt" class="bg-gray-50 rounded-lg p-4">
              <h4 class="text-sm font-medium text-gray-700 mb-2">System Prompt</h4>
              <pre class="text-sm text-gray-700 whitespace-pre-wrap">{{ currentPrompt.system_prompt }}</pre>
            </div>
            <div v-if="currentPrompt?.user_prompt" class="bg-blue-50 rounded-lg p-4">
              <h4 class="text-sm font-medium text-blue-700 mb-2">User Prompt</h4>
              <pre class="text-sm text-gray-700 whitespace-pre-wrap">{{ currentPrompt.user_prompt }}</pre>
            </div>
          </div>

          <div class="mt-6 flex justify-end">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50"
              @click="showViewPromptModal = false"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Prompt Modal -->
    <Teleport to="body">
      <div
        v-if="showDeletePromptModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showDeletePromptModal = false"
      >
        <div class="bg-white rounded-xl max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900">Delete Prompt</h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete the prompt "{{ promptToDelete?.name }}"? This action cannot be undone.
          </p>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50"
              @click="showDeletePromptModal = false"
            >
              Cancel
            </button>
            <button
              class="inline-flex justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-700"
              @click="deletePrompt"
              :disabled="isDeleting"
            >
              <svg v-if="isDeleting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Templates Modal (existing) -->
    <Teleport to="body">
      <div
        v-if="showTemplates"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showTemplates = false"
      >
        <div class="bg-white rounded-lg max-w-4xl w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900 mb-4">Schema Templates</h3>
          <p class="text-sm text-gray-600 mb-6">Select a template for common medical document structures</p>

          <div class="grid grid-cols-2 gap-4">
            <button
              v-for="template in schemaTemplates"
              :key="template.name"
              @click="applyTemplate(template)"
              class="p-4 border rounded-lg hover:border-indigo-500 hover:bg-indigo-50 text-left transition-colors"
            >
              <h4 class="font-medium text-gray-900">{{ template.name }}</h4>
              <p class="text-sm text-gray-600 mt-1">{{ template.description }}</p>
            </button>
          </div>

          <div class="mt-6 flex justify-end">
            <button
              class="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showTemplates = false"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- View Schema Modal (existing) -->
    <Teleport to="body">
      <div
        v-if="showViewModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showViewModal = false"
      >
        <div class="bg-white rounded-lg max-w-2xl w-full p-6" @click.stop>
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">{{ currentSchema?.schema_name }}</h3>
            <button @click="showViewModal = false" class="text-gray-400 hover:text-gray-500">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="bg-gray-50 p-4 rounded-md overflow-auto max-h-96">
            <pre class="text-sm text-gray-700">{{ formatJSON(currentSchema?.schema_definition) }}</pre>
          </div>
          <div class="mt-6 flex justify-end">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showViewModal = false"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Schema Modal (existing) -->
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50"
        @click="showDeleteModal = false"
      >
        <div class="bg-white rounded-lg max-w-md w-full p-6" @click.stop>
          <h3 class="text-lg font-medium text-gray-900">Delete Schema</h3>
          <p class="mt-2 text-sm text-gray-500">
            Are you sure you want to delete the schema "{{ schemaToDelete?.schema_name }}"? This action cannot be undone.
          </p>
          <div class="mt-6 flex justify-end space-x-3">
            <button
              class="inline-flex justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              @click="showDeleteModal = false"
            >
              Cancel
            </button>
            <button
              class="inline-flex justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
              @click="deleteSchema"
              :disabled="isDeleting"
            >
              <svg v-if="isDeleting" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import { api } from '@/services/api';
import { useToast } from 'vue-toastification';
import VisualSchemaEditor from './VisualSchemaEditor.vue';

const props = defineProps({
  projectId: {
    type: [String, Number],
    required: true
  }
});

const toast = useToast();

// Add new refs for prompts
const prompts = ref([]);
const isLoadingPrompts = ref(false);
const showCreatePromptModal = ref(false);
const showEditPromptModal = ref(false);
const showViewPromptModal = ref(false);
const showDeletePromptModal = ref(false);
const currentPrompt = ref(null);
const promptToDelete = ref(null);
const promptError = ref('');
const showPreviewSystem = ref(false);
const showPreviewUser = ref(false);
const showButtonTooltip = ref(false);

const promptForm = ref({
  name: '',
  description: '',
  system_prompt: '',
  user_prompt: ''
});

// Add active section ref
const activeSection = ref('schemas');

// Sample document for preview
const sampleDocument = "Patient Name: John Doe\nDate of Birth: 1985-03-15\nMedical Record Number: MRN-123456\n\nChief Complaint: Persistent cough and fever for 3 days\n\nHistory of Present Illness: The patient reports experiencing a dry cough that started 3 days ago...";

// Prompt templates (can be expanded later)
const promptTemplates = {
  medical: {
    name: 'Medical Document Extraction',
    description: 'Extract structured medical information from clinical documents',
    system_prompt: `You are a medical information extraction specialist. Your task is to carefully analyze medical documents and extract structured information according to the provided JSON schema.

Important guidelines:
- Extract only information that is explicitly stated in the document
- Do not infer or assume information that is not clearly mentioned
- Use null for missing values
- Maintain medical terminology accuracy
- Preserve dates and numerical values exactly as written

Document to analyze:
{document_content}`,
    user_prompt: `Please extract the structured information from the medical document according to the JSON schema. Return only the JSON object with the extracted data.`
  }
};

const hasUnsavedChanges = ref(false);
const originalSchemaForm = ref({});
const rawJsonTextarea = ref(null);
const cursorPosition = ref(0);
const schemas = ref([]);
const isLoading = ref(true);
const error = ref('');
const isSubmitting = ref(false);
const isDeleting = ref(false);
const schemaError = ref('');
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showViewModal = ref(false);
const showDeleteModal = ref(false);
const showTemplates = ref(false);
const currentSchema = ref(null);
const schemaToDelete = ref(null);
const schemaForm = ref({
  schema_name: '',
  schema_definition: ''
});

let isUpdating = false;
let isUpdatingFromWatch = false;
let updateTimeout = null;

const activeTab = ref('visual');
const visualSchema = ref({
  type: 'object',
  properties: {}
});
const advancedMode = ref(false);
const splitView = ref(false);

// Schema templates for medical documents
const schemaTemplates = [
  {
    name: 'Patient Information',
    description: 'Basic patient demographics and contact details',
    schema: {
      type: 'object',
      properties: {
        patient_id: { type: 'string', title: 'Patient ID' },
        first_name: { type: 'string', title: 'First Name' },
        last_name: { type: 'string', title: 'Last Name' },
        date_of_birth: { type: 'string', format: 'date', title: 'Date of Birth' },
        gender: {
          type: 'string',
          title: 'Gender',
          enum: ['Male', 'Female', 'Other']
        },
        contact: {
          type: 'object',
          title: 'Contact Information',
          properties: {
            phone: { type: 'string', title: 'Phone Number' },
            email: { type: 'string', format: 'email', title: 'Email' },
            address: { type: 'string', title: 'Address' }
          }
        }
      }
    }
  },
  {
    name: 'Medical History',
    description: 'Patient medical history and conditions',
    schema: {
      type: 'object',
      properties: {
        conditions: {
          type: 'array',
          title: 'Medical Conditions',
          items: {
            type: 'object',
            properties: {
              condition_name: { type: 'string', title: 'Condition' },
              diagnosis_date: { type: 'string', format: 'date', title: 'Diagnosis Date' },
              status: {
                type: 'string',
                title: 'Status',
                enum: ['Active', 'Resolved', 'Chronic']
              }
            }
          }
        },
                allergies: {
          type: 'array',
          title: 'Allergies',
          items: {
            type: 'object',
            properties: {
              allergen: { type: 'string', title: 'Allergen' },
              severity: {
                type: 'string',
                title: 'Severity',
                enum: ['Mild', 'Moderate', 'Severe']
              },
              reaction: { type: 'string', title: 'Reaction Type' }
            }
          }
        },
        medications: {
          type: 'array',
          title: 'Current Medications',
          items: {
            type: 'object',
            properties: {
              medication_name: { type: 'string', title: 'Medication' },
              dosage: { type: 'string', title: 'Dosage' },
              frequency: { type: 'string', title: 'Frequency' }
            }
          }
        }
      }
    }
  },
  {
    name: 'Lab Results',
    description: 'Laboratory test results and measurements',
    schema: {
      type: 'object',
      properties: {
        test_date: { type: 'string', format: 'date', title: 'Test Date' },
        lab_name: { type: 'string', title: 'Laboratory Name' },
        results: {
          type: 'array',
          title: 'Test Results',
          items: {
            type: 'object',
            properties: {
              test_name: { type: 'string', title: 'Test Name' },
              value: { type: 'number', title: 'Value' },
              unit: { type: 'string', title: 'Unit' },
              reference_range: { type: 'string', title: 'Reference Range' },
              abnormal: { type: 'boolean', title: 'Abnormal' }
            }
          }
        }
      }
    }
  },
  {
    name: 'Prescription',
    description: 'Medication prescriptions and dosage information',
    schema: {
      type: 'object',
      properties: {
        prescription_date: { type: 'string', format: 'date', title: 'Prescription Date' },
        prescriber: { type: 'string', title: 'Prescriber Name' },
        medications: {
          type: 'array',
          title: 'Medications',
          items: {
            type: 'object',
            properties: {
              medication_name: { type: 'string', title: 'Medication' },
              dosage: { type: 'string', title: 'Dosage' },
              frequency: { type: 'string', title: 'Frequency' },
              duration: { type: 'string', title: 'Duration' },
              instructions: { type: 'string', title: 'Instructions' }
            }
          }
        }
      }
    }
  }
];

// Computed property for prompt validation
const isPromptValid = computed(() => {
  if (!promptForm.value.name) return false;
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) return false;

  const hasPlaceholder =
    (promptForm.value.system_prompt && promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'));

  return hasPlaceholder;
});

const formErrors = computed(() => {
  const errors = [];
  if (!promptForm.value.name || promptForm.value.name.trim() === '') {
    errors.push('Prompt name is required');
  }
  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) {
    errors.push('At least one prompt must be provided');
  }
  const hasPlaceholder =
    (promptForm.value.system_prompt && promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'));
  if ((promptForm.value.system_prompt || promptForm.value.user_prompt) && !hasPlaceholder) {
    errors.push('The {document_content} placeholder must be present');
  }
  return errors;
});


// Prompt-related functions
const fetchPrompts = async () => {
  isLoadingPrompts.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/prompt`);
    prompts.value = response.data;
  } catch (err) {
    console.error('Failed to load prompts:', err);
    toast.error('Failed to load prompts. Please try again.');
  } finally {
    isLoadingPrompts.value = false;
  }
};


const validatePromptPlaceholder = () => {
  promptError.value = ''; // Clear previous errors

  if (!promptForm.value.system_prompt && !promptForm.value.user_prompt) {
    promptError.value = 'At least one prompt (system or user) must be provided';
    return false;
  }

  const hasPlaceholder =
    (promptForm.value.system_prompt && promptForm.value.system_prompt.includes('{document_content}')) ||
    (promptForm.value.user_prompt && promptForm.value.user_prompt.includes('{document_content}'));

  if (!hasPlaceholder) {
    promptError.value = 'The placeholder {document_content} must be present in either system or user prompt';
    return false;
  }

  promptError.value = '';
  return true;
};


const createPrompt = async () => {
  // Check if name is provided
  if (!promptForm.value.name || promptForm.value.name.trim() === '') {
    toast.error('Prompt name is required');
    return;
  }

  // Validate prompts
  if (!validatePromptPlaceholder()) {
    toast.error(promptError.value || 'Please check the prompt requirements');
    return;
  }

  isSubmitting.value = true;
  try {
    const response = await api.post(`/project/${props.projectId}/prompt`, {
      ...promptForm.value,
      project_id: props.projectId
    });
    prompts.value.push(response.data);
    showCreatePromptModal.value = false;
    resetPromptForm();
    toast.success('Prompt created successfully');
  } catch (err) {
    console.error('Failed to create prompt:', err);
    toast.error(err.response?.data?.detail || 'Failed to create prompt');
  } finally {
    isSubmitting.value = false;
  }
};


const editPrompt = (prompt) => {
  currentPrompt.value = prompt;
  promptForm.value = {
    name: prompt.name,
    description: prompt.description || '',
    system_prompt: prompt.system_prompt || '',
    user_prompt: prompt.user_prompt || ''
  };
  showEditPromptModal.value = true;
};

const updatePrompt = async () => {
  if (!validatePromptPlaceholder()) {
    toast.error(promptError.value || 'Please check the prompt requirements');
    return;
  }

  isSubmitting.value = true;
  try {
    const response = await api.put(`/project/${props.projectId}/prompt/${currentPrompt.value.id}`, promptForm.value);
    const index = prompts.value.findIndex(p => p.id === currentPrompt.value.id);
    if (index !== -1) {
      prompts.value[index] = response.data;
    }
    showEditPromptModal.value = false;
    resetPromptForm();
    toast.success('Prompt updated successfully');
  } catch (err) {
    console.error('Failed to update prompt:', err);
    toast.error(err.response?.data?.detail || 'Failed to update prompt');
  } finally {
    isSubmitting.value = false;
  }
};


const viewPrompt = (prompt) => {
  currentPrompt.value = prompt;
  showViewPromptModal.value = true;
};

const confirmDeletePrompt = (prompt) => {
  promptToDelete.value = prompt;
  showDeletePromptModal.value = true;
};

const deletePrompt = async () => {
  if (!promptToDelete.value) return;

  isDeleting.value = true;
  try {
    await api.delete(`/project/${props.projectId}/prompt/${promptToDelete.value.id}`);
    prompts.value = prompts.value.filter(p => p.id !== promptToDelete.value.id);
    showDeletePromptModal.value = false;
    toast.success(`Prompt "${promptToDelete.value.name}" deleted successfully`);
  } catch (err) {
    console.error('Failed to delete prompt:', err);
    const errorMessage = err.response?.data?.detail || 'Failed to delete prompt';
    toast.error(errorMessage);
  } finally {
    isDeleting.value = false;
    promptToDelete.value = null;
  }
};


const togglePreview = (type) => {
  if (type === 'system') {
    showPreviewSystem.value = !showPreviewSystem.value;
  } else {
    showPreviewUser.value = !showPreviewUser.value;
  }
};

const useTemplate = () => {
  const template = promptTemplates.medical;
  promptForm.value = {
    name: template.name,
    description: template.description,
    system_prompt: template.system_prompt,
    user_prompt: template.user_prompt
  };
  validatePromptPlaceholder();
  toast.info('Medical extraction template applied');
};


const resetPromptForm = () => {
  promptForm.value = {
    name: '',
    description: '',
    system_prompt: '',
    user_prompt: ''
  };
  promptError.value = '';
  showPreviewSystem.value = false;
  showPreviewUser.value = false;
  currentPrompt.value = null;
};

const cancelPromptModal = () => {
  showCreatePromptModal.value = false;
  showEditPromptModal.value = false;
  resetPromptForm();
};

const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// Existing schema-related functions...
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const formatJSON = (json) => {
  try {
    if (typeof json === 'string') {
      json = JSON.parse(json);
    }
    return JSON.stringify(json, null, 2);
  } catch (err) {
    return json || '{}';
  }
};

const formatJsonInput = () => {
  try {
    const parsedJson = JSON.parse(schemaForm.value.schema_definition);
    schemaForm.value.schema_definition = JSON.stringify(parsedJson, null, 2);
    visualSchema.value = parsedJson;
    schemaError.value = '';
  } catch (err) {
    schemaError.value = 'Invalid JSON: ' + err.message;
  }
};

const fetchSchemas = async () => {
  isLoading.value = true;
  try {
    const response = await api.get(`/project/${props.projectId}/schema`);
    schemas.value = response.data;
  } catch (err) {
    error.value = 'Failed to load schemas';
    toast.error('Failed to load schemas. Please try again.');
    console.error(err);
  } finally {
    isLoading.value = false;
  }
};


const cancelSchemaModal = () => {
  if (hasUnsavedChanges.value) {
    if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
      return;
    }
  }

  showCreateModal.value = false;
  showEditModal.value = false;
  schemaError.value = '';
  activeTab.value = 'visual';
  schemaForm.value = {
    schema_name: '',
    schema_definition: ''
  };
  visualSchema.value = { type: 'object', properties: {} };
  currentSchema.value = null;
  hasUnsavedChanges.value = false;
};

const createSchema = async () => {
  schemaError.value = '';
  isSubmitting.value = true;
  let response;
  try {
    let schemaDefinition;
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition);
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message;
      toast.error('Invalid JSON format. Please check your schema definition.');
      isSubmitting.value = false;
      return;
    }
    if (!validateSchema(schemaDefinition)) {
      toast.error(schemaError.value || 'Schema validation failed');
      isSubmitting.value = false;
      return;
    }
    response = await api.post(`/project/${props.projectId}/schema`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition
    });
    schemas.value.push(response.data);
    showCreateModal.value = false;
    hasUnsavedChanges.value = false;
    cancelSchemaModal();
    toast.success(`Schema "${schemaForm.value.schema_name}" created successfully`);
  } catch (err) {
    schemaError.value = err.response?.data?.detail || 'Failed to create schema';
    toast.error(schemaError.value);
    console.error(err);
  } finally {
    isSubmitting.value = false;
  }
};


const updateSchema = async () => {
  schemaError.value = '';
  isSubmitting.value = true;
  let response;
  try {
    let schemaDefinition;
    try {
      schemaDefinition = JSON.parse(schemaForm.value.schema_definition);
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message;
      toast.error('Invalid JSON format. Please check your schema definition.');
      isSubmitting.value = false;
      return;
    }
    if (!validateSchema(schemaDefinition)) {
      toast.error(schemaError.value || 'Schema validation failed');
      isSubmitting.value = false;
      return;
    }
    response = await api.put(`/project/${props.projectId}/schema/${currentSchema.value.id}`, {
      schema_name: schemaForm.value.schema_name,
      schema_definition: schemaDefinition
    });
    const index = schemas.value.findIndex(s => s.id === currentSchema.value.id);
    if (index !== -1) {
      schemas.value[index] = response.data;
    }
    showEditModal.value = false;
    hasUnsavedChanges.value = false;
    cancelSchemaModal();
    toast.success(`Schema "${schemaForm.value.schema_name}" updated successfully`);
  } catch (err) {
    schemaError.value = err.response?.data?.detail || 'Failed to update schema';
    toast.error(schemaError.value);
    console.error(err);
  } finally {
    isSubmitting.value = false;
  }
};


const deleteSchema = async () => {
  if (!schemaToDelete.value) return;
  isDeleting.value = true;
  try {
    await api.delete(`/project/${props.projectId}/schema/${schemaToDelete.value.id}`);
    schemas.value = schemas.value.filter(s => s.id !== schemaToDelete.value.id);
    showDeleteModal.value = false;
    toast.success(`Schema "${schemaToDelete.value.schema_name}" deleted successfully`);
  } catch (err) {
    const errorMessage = err.response?.data?.detail || 'Failed to delete schema';
    toast.error(errorMessage);
    console.error(err);
  } finally {
    isDeleting.value = false;
    schemaToDelete.value = null;
  }
};


const viewSchema = (schema) => {
  currentSchema.value = schema;
  showViewModal.value = true;
};

const editSchema = (schema) => {
  currentSchema.value = schema;
  const formattedJson = formatJSON(schema.schema_definition);
  schemaForm.value = {
    schema_name: schema.schema_name,
    schema_definition: formattedJson
  };

  // Initialize visual schema
  try {
    visualSchema.value = JSON.parse(formattedJson);
  } catch (err) {
    console.warn('Failed to parse existing schema for visual editor:', err);
    visualSchema.value = { type: 'object', properties: {} };
  }

  showEditModal.value = true;
};

const validateSchema = (schema) => {
  try {
    console.log("Validating schema:", schema);
    const schemaCopy = JSON.parse(JSON.stringify(schema));
    delete schemaCopy.$schema;
    schemaError.value = '';
    return true;
  } catch (err) {
    schemaError.value = 'Invalid JSON: ' + err.message;
    return false;
  }
};

const onRawSchemaChange = () => {
  if (isUpdatingFromWatch) return;

  // Clear any pending updates
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }

  // Store cursor position
  const textarea = rawJsonTextarea.value;
  const savedPosition = textarea ? textarea.selectionStart : 0;

  updateTimeout = setTimeout(() => {
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition);
      isUpdatingFromWatch = true;

      // Deep clone to break reference
      visualSchema.value = JSON.parse(JSON.stringify(parsed));
      schemaError.value = '';

      nextTick(() => {
        isUpdatingFromWatch = false;
        // Restore cursor position
        if (textarea && textarea === document.activeElement) {
          textarea.setSelectionRange(savedPosition, savedPosition);
        }
      });
    } catch (err) {
      schemaError.value = 'Invalid JSON: ' + err.message;
    }
  }, 300);
};

const confirmDelete = (schema) => {
  schemaToDelete.value = schema;
  showDeleteModal.value = true;
};

const applyTemplate = (template) => {
  visualSchema.value = template.schema;
  schemaForm.value.schema_definition = JSON.stringify(template.schema, null, 2);
  schemaForm.value.schema_name = template.name;
  showTemplates.value = false;
  toast.info(`Template "${template.name}" applied`);
};


const updateVisualSchema = (newSchema) => {
  if (isUpdatingFromWatch) return;

  // Clear any pending updates
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }

  isUpdatingFromWatch = true;
  visualSchema.value = JSON.parse(JSON.stringify(newSchema)); // Deep clone
  schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2);
  schemaError.value = '';

  nextTick(() => {
    isUpdatingFromWatch = false;
  });
};

const preserveCursorPosition = (event) => {
  cursorPosition.value = event.target.selectionStart;
};

// Initialize on mount
onMounted(() => {
  fetchSchemas();
  fetchPrompts();
});

// Cleanup on unmount
onUnmounted(() => {
  document.body.style.overflow = '';
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }
});

// Watch for tab changes to sync data
watch(activeTab, (newTab) => {
  if (newTab === 'visual' && !splitView.value) {
    // Convert raw JSON to visual schema
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition || '{"type": "object", "properties": {}}');
      visualSchema.value = parsed;
    } catch (err) {
      console.warn('Invalid JSON, using default schema');
      visualSchema.value = { type: 'object', properties: {} };
    }
  } else if (newTab === 'raw' && !splitView.value) {
    // Convert visual schema to raw JSON
    schemaForm.value.schema_definition = JSON.stringify(visualSchema.value, null, 2);
  }
});

// Watch for modal changes
watch([showCreateModal, showEditModal], ([create, edit]) => {
  if (create || edit) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
});

// Initialize visual schema when opening create modal
watch(showCreateModal, (newValue) => {
  if (newValue) {
    activeTab.value = 'visual';
    visualSchema.value = { type: 'object', properties: {} };
    schemaForm.value = {
      schema_name: '',
      schema_definition: JSON.stringify({ type: 'object', properties: {} }, null, 2)
    };
  }
});

// Initialize visual schema when opening edit modal
watch(showEditModal, (newValue) => {
  if (newValue && currentSchema.value) {
    activeTab.value = 'visual';
    try {
      const parsed = JSON.parse(schemaForm.value.schema_definition);
      visualSchema.value = parsed;
    } catch (err) {
      visualSchema.value = { type: 'object', properties: {} };
    }
  }
});

// Watch for changes to track unsaved state
watch([schemaForm, visualSchema], () => {
  if (isUpdating) return;
  hasUnsavedChanges.value = true;
}, { deep: true });

// Watch visual schema changes
watch(visualSchema, (newSchema) => {
  if (isUpdatingFromWatch) return;

  // Clear any pending updates
  if (updateTimeout) {
    clearTimeout(updateTimeout);
  }

  // Debounce updates
  updateTimeout = setTimeout(() => {
    if (document.activeElement !== rawJsonTextarea.value) {
      isUpdatingFromWatch = true;
      schemaForm.value.schema_definition = JSON.stringify(newSchema, null, 2);
      nextTick(() => {
        isUpdatingFromWatch = false;
      });
    }
  }, 300);
}, { deep: true });


watch(() => promptForm.value.name, (newValue) => {
  if (newValue && promptError.value && promptError.value.includes('name')) {
    validatePromptPlaceholder();
  }
});

watch([() => promptForm.value.system_prompt, () => promptForm.value.user_prompt], () => {
  if (promptForm.value.system_prompt || promptForm.value.user_prompt) {
    validatePromptPlaceholder();
  }
});

</script>

<style scoped>
/* Add any custom styles here if needed */
</style>


