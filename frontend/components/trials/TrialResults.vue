<template>
  <teleport to="body">
    <transition name="fade">
      <div
        v-if="isModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
        @click="handleBackdropClick"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div
          class="relative bg-white rounded-3xl shadow-2xl max-w-8xl w-full max-h-[95vh] flex flex-col ring-1 ring-blue-100 overflow-hidden"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between gap-4 px-8 py-6 border-b rounded-t-3xl bg-white/90"
          >
            <h3 class="text-2xl font-bold tracking-tight text-gray-800">Trial Results</h3>
            <button
              class="text-gray-400 hover:text-blue-700 hover:bg-blue-50 rounded-full p-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close"
              autofocus
              @click="$emit('close')"
            >
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-8 bg-white/70">
            <!-- Loading / Error -->
            <div v-if="isLoading" class="flex flex-col items-center justify-center py-16">
              <span
                class="inline-block animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mb-3"
              ></span>
              <span class="mt-2 text-gray-500">Loading trial results…</span>
            </div>
            <div
              v-else-if="error"
              class="bg-red-50 border-l-4 border-red-400 p-5 mb-5 rounded-lg flex items-start gap-2"
            >
              <svg class="h-6 w-6 mt-1 text-red-400" fill="none" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 00-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 101.4 1.4L10 11.4l1.3 1.3a1 1 0 001.4-1.4L11.4 10l1.3-1.3a1 1 0 00-1.4-1.4L10 8.6 8.7 7.3z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="text-sm text-red-700">{{ error }}</span>
            </div>

            <!-- Content -->
            <template v-else-if="trial">
              <!-- Trial meta -->
              <div
                class="bg-gradient-to-br from-white via-blue-50 to-white shadow-inner rounded-xl p-6 mb-7 border border-gray-100"
              >
                <div class="flex flex-col md:flex-row md:justify-between gap-6">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <h2 class="text-xl font-bold text-blue-900 truncate">
                        {{ trial.name || `Trial #${trial.id}` }}
                      </h2>
                      <span
                        v-if="trial.status"
                        class="ml-2 px-2 py-0.5 rounded-full text-xs font-semibold shadow"
                        :class="{
                          'bg-green-100 text-green-700': trial.status === 'completed',
                          'bg-blue-100 text-blue-700': trial.status === 'processing',
                          'bg-yellow-100 text-yellow-700': trial.status === 'pending',
                          'bg-red-100 text-red-700': trial.status === 'failed',
                          'bg-gray-100 text-gray-700': trial.status === 'cancelled',
                        }"
                        >{{ trial.status }}</span
                      >
                    </div>
                    <div v-if="trial.description" class="text-gray-700 text-sm mb-1">
                      {{ trial.description }}
                    </div>
                    <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600 mt-1">
                      <span
                        ><span class="font-semibold">Started:</span>
                        {{ formatDate(trial.created_at, true) }}</span
                      >
                      <span><span class="font-semibold">Model:</span> {{ trial.llm_model }}</span>
                      <span v-if="trial.prompt"
                        ><span class="font-semibold">Prompt:</span>
                        <span class="text-gray-800">{{
                          trial.prompt.name || '[unnamed prompt]'
                        }}</span></span
                      >
                      <span v-if="trial.document_set"
                        ><span class="font-semibold">Document Set:</span>
                        <span class="text-gray-800">{{
                          trial.document_set.name || 'Set #' + trial.document_set.id
                        }}</span></span
                      >
                      <span
                        ><span class="font-semibold">Documents:</span>
                        {{ trial.document_ids?.length || 0 }}</span
                      >
                    </div>
                  </div>
                  <div class="flex flex-col items-start md:items-end gap-2 min-w-[200px]">
                    <div class="flex gap-2">
                      <button
                        class="px-3 py-1.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                        @click="openSchemaModal"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                          />
                        </svg>
                        View Schema
                      </button>
                      <button
                        class="px-3 py-1.5 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                        @click="openPromptModal"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M8 9h8m-8 4h8m-8 4h5M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z"
                          />
                        </svg>
                        View Prompt
                      </button>
                    </div>
                    <span
                      class="text-sm bg-blue-50 px-4 py-2 rounded-lg font-medium text-blue-800 shadow-sm"
                    >
                      {{ trial.results?.length || 0 }} documents processed
                    </span>
                    <span
                      v-if="totalUsage.total_tokens !== undefined"
                      class="text-xs bg-blue-100 px-3 py-1 rounded-lg font-semibold text-blue-800 mt-1"
                      title="Sum of prompt and completion tokens across all results"
                    >
                      Usage: {{ totalUsage.prompt_tokens || 0 }} prompt /
                      {{ totalUsage.completion_tokens || 0 }} completion /
                      <b>{{ totalUsage.total_tokens || 0 }}</b> total tokens
                    </span>
                    <div
                      v-if="trial.advanced_options && Object.keys(trial.advanced_options).length"
                      class="mt-2 bg-white rounded-lg border border-blue-100 px-4 py-2 shadow text-xs max-w-xs"
                    >
                      <div class="text-xs font-semibold text-blue-700 mb-1">
                        LLM Advanced Options
                      </div>
                      <ul>
                        <li
                          v-for="(value, key) in trial.advanced_options"
                          :key="key"
                          class="flex items-center gap-1 mb-0.5"
                        >
                          <span class="font-medium capitalize">{{ key.replace(/_/g, ' ') }}:</span>
                          <span class="text-blue-900">{{ value }}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Document Errors summary -->
              <div
                v-if="trial?.meta?.failures && Object.keys(trial.meta.failures).length"
                class="bg-red-50 border border-red-200 rounded-xl p-5 mb-6"
              >
                <div class="flex items-center gap-2 mb-2">
                  <svg
                    class="w-5 h-5 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span class="font-semibold text-red-700"
                    >{{ Object.keys(trial.meta.failures).length }} document error{{
                      Object.keys(trial.meta.failures).length === 1 ? '' : 's'
                    }}</span
                  >
                </div>
                <details class="mt-1">
                  <summary class="text-sm text-red-700 cursor-pointer">View error details</summary>
                  <ul class="list-disc list-inside mt-2 text-sm text-red-800">
                    <li v-for="(err, docId) in trial.meta.failures" :key="docId">
                      <span class="font-semibold">Doc {{ docId }}:</span> {{ err }}
                    </li>
                  </ul>
                </details>
              </div>

              <!-- Results list -->
              <div
                v-if="!trial.results || trial.results.length === 0"
                class="flex flex-col items-center justify-center py-16 bg-gray-50 rounded-lg border border-gray-200"
              >
                <svg
                  class="h-14 w-14 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span class="text-gray-500 mt-3">No results available for this trial.</span>
                <span
                  v-if="trial.status === 'processing' || trial.status === 'pending'"
                  class="text-sm mt-2 text-gray-400"
                  >Please wait for the trial to complete.</span
                >
              </div>

              <div v-else class="grid grid-cols-1 gap-5">
                <div
                  v-for="(res, index) in trial.results"
                  :key="index"
                  class="bg-white shadow border border-gray-100 rounded-xl transition-shadow hover:shadow-lg"
                >
                  <!-- Row header -->
                  <div
                    class="cursor-pointer flex items-center justify-between px-6 py-4 border-b hover:bg-gray-50/70 transition-colors rounded-t-xl select-none"
                    @click="toggleResultExpansion(index)"
                  >
                    <div class="flex flex-col gap-0.5">
                      <div class="flex items-center flex-wrap gap-2">
                        <span
                          class="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-base font-bold"
                          >{{ index + 1 }}</span
                        >
                        <span class="font-medium text-gray-800">{{
                          documentLabels[index]?.name || 'Loading document name...'
                        }}</span>

                        <!-- Status pills -->
                        <span
                          v-if="res.result"
                          class="text-[10px] uppercase tracking-wide bg-green-100 text-green-700 px-2 py-0.5 rounded"
                          >OK</span
                        >
                        <span
                          v-else
                          class="text-[10px] uppercase tracking-wide bg-red-100 text-red-700 px-2 py-0.5 rounded"
                          >Error</span
                        >

                        <span
                          v-if="
                            res.additional_content?.finish_reason &&
                            res.additional_content.finish_reason !== 'stop'
                          "
                          class="text-[10px] uppercase tracking-wide bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded"
                        >
                          {{ res.additional_content.finish_reason }}
                        </span>
                        <span
                          v-if="res.additional_content?.truncation_analysis?.likely_truncated"
                          class="text-[10px] uppercase tracking-wide bg-orange-100 text-orange-800 px-2 py-0.5 rounded"
                        >
                          Truncated
                        </span>
                      </div>
                      <span
                        v-if="
                          documentLabels[index]?.original &&
                          documentLabels[index]?.original !== documentLabels[index]?.name
                        "
                        class="text-xs text-gray-400 italic ml-10 truncate max-w-xs"
                        >(Original: {{ documentLabels[index].original }})</span
                      >
                    </div>
                    <svg
                      class="w-5 h-5 text-gray-400 transition-transform duration-200"
                      :class="{ 'rotate-180': expandedResults[index] }"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </div>

                  <!-- Row body -->
                  <div
                    v-if="expandedResults[index]"
                    class="p-6 bg-gradient-to-b from-white to-blue-50/20"
                  >
                    <!-- Inline error panel -->
                    <div
                      v-if="!res.result || res.additional_content?.json_error"
                      class="mb-4 bg-red-50 border border-red-200 text-red-800 text-sm rounded-lg p-4"
                    >
                      <div class="font-semibold mb-1">This document has no structured result.</div>
                      <div v-if="res.additional_content?.user_guidance?.user_message" class="mb-1">
                        {{ res.additional_content.user_guidance.user_message }}
                      </div>
                      <div v-else-if="res.additional_content?.json_error" class="mb-1">
                        Parser error: {{ res.additional_content.json_error }}
                      </div>
                      <details v-if="res.additional_content?.tuning_advice" class="mt-2">
                        <summary class="cursor-pointer">Tuning advice</summary>
                        <ul class="list-disc list-inside mt-1">
                          <li
                            v-for="(rec, i) in res.additional_content.tuning_advice.recommendations"
                            :key="i"
                          >
                            <span class="font-medium">{{ rec.action }}</span>
                            <span v-if="rec.suggested_value">
                              → <code>{{ rec.suggested_value }}</code></span
                            >
                            <span v-if="rec.rationale"> — {{ rec.rationale }}</span>
                          </li>
                        </ul>
                      </details>
                    </div>

                    <div
                      class="flex gap-6"
                      :class="viewMode[index] === 'vertical' ? 'flex-col' : 'flex-col md:flex-row'"
                    >
                      <div
                        class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100"
                      >
                        <h4
                          class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5"
                        >
                          <svg
                            class="h-4 w-4"
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
                          Document Content
                        </h4>
                        <div
                          v-if="isMarkdown(documentContents[index])"
                          class="markdown-content"
                          v-html="renderMarkdown(documentContents[index])"
                        ></div>
                        <pre v-else class="text-xs text-gray-800 whitespace-pre-wrap">{{
                          documentContents[index]
                        }}</pre>
                      </div>

                      <div
                        class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100"
                      >
                        <h4
                          class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5"
                        >
                          <svg
                            class="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                            />
                          </svg>
                          Extracted Information
                        </h4>
                        <template v-if="res.result">
                          <JsonViewer :data="res.result" />
                        </template>
                        <template v-else>
                          <div class="text-xs text-gray-500 italic">
                            No structured output for this document.
                          </div>
                        </template>
                      </div>

                      <div
                        v-if="showDocumentPanel[index]"
                        class="bg-gray-50 p-5 rounded-xl overflow-auto flex-1 max-h-[480px] border border-gray-100"
                      >
                        <h4
                          class="text-sm font-semibold mb-3 text-gray-700 flex items-center gap-1.5"
                        >
                          <svg
                            class="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              stroke-width="2"
                              d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"
                            />
                          </svg>
                          Original Document
                        </h4>
                        <iframe
                          v-if="documentPdfUrls[index]"
                          :src="documentPdfUrls[index]"
                          frameborder="0"
                          width="100%"
                          height="400px"
                          class="rounded-md"
                        ></iframe>
                        <div v-else-if="documentPdfLoading[index]" class="text-center py-10">
                          <span
                            class="inline-block animate-spin h-8 w-8 border-4 border-blue-400 border-t-transparent rounded-full"
                          ></span>
                          <span class="mt-2 text-gray-500 block">Loading preview…</span>
                        </div>
                        <span v-else class="text-gray-500">Failed to load preview</span>
                      </div>
                    </div>

                    <!-- Reasoning & Metadata -->
                    <div
                      v-if="
                        getReasoningContent(index) ||
                        getAdditionalContent(index)?.usage ||
                        getAdditionalContent(index)?.finish_reason
                      "
                      class="mt-6"
                    >
                      <button
                        class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                        @click="showReasoningPanel[index] = !showReasoningPanel[index]"
                      >
                        <svg
                          :class="showReasoningPanel[index] ? 'rotate-90' : ''"
                          class="h-4 w-4 transition-transform duration-200"
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
                        <span
                          >{{ showReasoningPanel[index] ? 'Hide' : 'Show' }} LLM Reasoning &
                          Metadata</span
                        >
                      </button>
                      <div
                        v-if="showReasoningPanel[index]"
                        class="bg-blue-50/60 border border-blue-100 rounded-lg mt-3 p-5"
                      >
                        <div v-if="getReasoningContent(index)" class="mb-4">
                          <h5 class="font-semibold text-blue-800 mb-2">Reasoning</h5>
                          <div
                            class="markdown-content"
                            v-html="renderMarkdown(getReasoningContent(index))"
                          ></div>
                        </div>
                        <div v-if="getAdditionalContent(index)?.usage" class="mb-2">
                          <h5 class="font-semibold text-blue-800 mb-1">Token Usage</h5>
                          <ul class="text-xs text-blue-900 ml-2">
                            <li v-for="(v, k) in getAdditionalContent(index).usage" :key="k">
                              <span class="font-medium">{{ k.replace(/_/g, ' ') }}:</span> {{ v }}
                            </li>
                          </ul>
                        </div>
                        <div v-if="getAdditionalContent(index)?.finish_reason">
                          <h5 class="font-semibold text-blue-800 mb-1">Finish Reason</h5>
                          <span class="text-xs text-blue-900">{{
                            getAdditionalContent(index).finish_reason
                          }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Row actions -->
                    <div class="mt-6 flex flex-wrap gap-3 justify-end">
                      <button
                        class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                        @click="toggleViewMode(index)"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M4 6h16M4 12h16m-7 6h7"
                          />
                        </svg>
                        {{ viewMode[index] === 'vertical' ? 'Side by Side View' : 'Vertical View' }}
                      </button>
                      <button
                        v-if="documentMeta[index]?.previewable"
                        class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center gap-1.5 transition-colors duration-150 shadow-sm"
                        @click="toggleDocumentPanel(index)"
                      >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path
                            v-if="showDocumentPanel[index]"
                            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268-2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                          />
                          <path v-else d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268-2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          />
                        </svg>
                        {{
                          showDocumentPanel[index]
                            ? 'Hide Original Document'
                            : 'View Original Document'
                        }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <div v-else class="flex flex-col items-center justify-center py-16">
              <svg
                class="h-14 w-14 text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="1.5"
                  d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span class="text-gray-500 mt-3">Trial not found</span>
              <button
                class="mt-6 inline-block px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors duration-150 shadow"
                @click="$emit('close')"
              >
                Return to trials
              </button>
            </div>
          </div>
        </div>

        <!-- Schema / Prompt snapshots (frozen at trial run) -->
        <TrialSchemaModal
          :open="showSchemaModal"
          :schema="schemaForModal"
          :is-snapshot="schemaIsSnapshot"
          @close="showSchemaModal = false"
        />
        <TrialPromptModal
          :open="showPromptModal"
          :prompt="promptForModal"
          :is-snapshot="promptIsSnapshot"
          @close="showPromptModal = false"
        />
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api.js'
import { formatDate } from '@/utils/formatters.js'
import { useToast } from 'vue-toastification'
import JsonViewer from '@/components/common/JsonViewer.vue'
import TrialSchemaModal from './TrialSchemaModal.vue'
import TrialPromptModal from './TrialPromptModal.vue'
import { marked } from 'marked'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
  trialId: { type: [String, Number], required: true },
  isModal: { type: Boolean, default: false },
})
defineEmits(['close'])

const route = useRoute()
const router = useRouter()
const toast = useToast()

const trialId = computed(() => props.trialId || parseInt(route.params.trialId))
const isLoading = ref(true)
const error = ref(null)
const trial = ref(null)

const expandedResults = ref({})
const documentContents = ref({})
const documentLabels = ref({})
const viewMode = ref({})
const documentPdfUrls = ref({})
const documentPdfLoading = ref({})
const showDocumentPanel = ref({})
// per-result: { previewable, fileId } — drives whether the "View Original
// Document" button is shown at all (hidden when there's nothing to render)
const documentMeta = ref({})
const showReasoningPanel = ref({}) // reasoning accordion

// Schema / Prompt snapshot display (frozen at trial run; fallback to live for
// trials created before snapshots existed)
const showSchemaModal = ref(false)
const showPromptModal = ref(false)
const schemaFallback = ref(null) // live schema fetched for legacy trials
const schemaForModal = computed(() => trial.value?.schema_snapshot || schemaFallback.value || null)
const promptForModal = computed(() => trial.value?.prompt_snapshot || trial.value?.prompt || null)
const schemaIsSnapshot = computed(() => !!trial.value?.schema_snapshot)
const promptIsSnapshot = computed(() => !!trial.value?.prompt_snapshot)

async function openSchemaModal() {
  // Legacy trials have no snapshot — fetch the live schema as a best-effort fallback.
  if (!trial.value?.schema_snapshot && trial.value?.schema_id && !schemaFallback.value) {
    try {
      const res = await api.get(`/project/${props.projectId}/schema/${trial.value.schema_id}`)
      schemaFallback.value = res.data
    } catch (err) {
      console.error('Failed to load schema for trial:', err)
    }
  }
  showSchemaModal.value = true
}
function openPromptModal() {
  showPromptModal.value = true
}

const renderMarkdown = (text) => {
  try {
    return marked(text)
  } catch {
    return text
  }
}
const isMarkdown = (text) => {
  if (!text) return false
  try {
    return (
      text.includes('#') ||
      text.includes('**') ||
      text.includes('*') ||
      text.includes('[') ||
      text.includes('```') ||
      /\n\s*-\s/.test(text) ||
      /\n\s*\d+\.\s/.test(text)
    )
  } catch {
    return false
  }
}

// Helpers to parse/inspect additional_content
const parseAdditional = (ac) => {
  if (!ac) return null
  if (typeof ac === 'string') {
    try {
      return JSON.parse(ac)
    } catch {
      return null
    }
  }
  return ac
}
const getAdditionalContent = (i) => {
  const r = trial.value?.results?.[i]
  return r ? parseAdditional(r.additional_content) : null
}
const getReasoningContent = (i) => getAdditionalContent(i)?.reasoning_content || null

const docIdForIndex = (i) => {
  const r = trial.value?.results?.[i]
  // Prefer the document_id embedded in the result; fall back to legacy array if present
  return r?.document_id ?? trial.value?.document_ids?.[i] ?? null
}

const totalUsage = computed(() => {
  const totals = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
  if (!trial.value?.results?.length) return totals
  for (const r of trial.value.results) {
    const ac = parseAdditional(r?.additional_content)
    if (!ac?.usage) continue
    totals.prompt_tokens += Number(ac.usage.prompt_tokens ?? 0) || 0
    totals.completion_tokens += Number(ac.usage.completion_tokens ?? 0) || 0
    totals.total_tokens += Number(ac.usage.total_tokens ?? 0) || 0
  }
  return totals
})

// Fetch the full trial (with results)
const fetchData = async () => {
  isLoading.value = true
  error.value = null
  try {
    const res = await api.get(`/project/${props.projectId}/trial/${trialId.value}`)
    trial.value = res.data
    if (trial.value?.results?.length) loadDocumentNames()
  } catch (err) {
    console.error('Error loading trial:', err)
    error.value = err?.message || 'Failed to load trial data'
  } finally {
    isLoading.value = false
  }
}

// Load per-document display labels + original-file previewability
const loadDocumentNames = async () => {
  if (!trial.value?.results?.length) return
  for (let i = 0; i < trial.value.results.length; i++) {
    try {
      const docId = docIdForIndex(i)
      if (!docId) {
        documentMeta.value[i] = { previewable: false, fileId: null }
        continue
      }
      const r = await api.get(`/project/${props.projectId}/document/${docId}`)
      const d = r.data
      documentLabels.value[i] = {
        name: d.document_name || d.original_file?.file_name || `Document ${docId}`,
        original: d.original_file?.file_name || '',
      }
      // Only PDFs/images can be shown inline; the "View Original Document"
      // button is hidden for everything else (txt, csv, xlsx, …) so no split
      // screen is offered when there's nothing to render.
      const { previewable } = analyzeOriginalFile(d)
      const fileId =
        d.preprocessed_file_id && d.preprocessed_file?.file_type === 'application/pdf'
          ? d.preprocessed_file_id
          : d.original_file_id
      documentMeta.value[i] = { previewable, fileId: previewable ? fileId : null }
    } catch (err) {
      console.error(`Label load failed index ${i}:`, err)
      const fallbackId = docIdForIndex(i)
      documentLabels.value[i] = { name: `Document (ID: ${fallbackId ?? 'unknown'})`, original: '' }
      documentMeta.value[i] = { previewable: false, fileId: null }
    }
  }
}

// Toggles
const toggleResultExpansion = async (i) => {
  expandedResults.value[i] = !expandedResults.value[i]
  if (viewMode.value[i] === undefined) viewMode.value[i] = 'horizontal'
  if (expandedResults.value[i] && !documentContents.value[i]) {
    try {
      const docId = docIdForIndex(i)
      if (!docId) throw new Error('Missing document_id for this result')
      const r = await api.get(`/project/${props.projectId}/document/${docId}`)
      documentContents.value[i] = r.data.text || 'No text content available'
    } catch (err) {
      documentContents.value[i] = 'Error loading document content'
      console.error(err)
    }
  }
}

const toggleViewMode = (i) => {
  viewMode.value[i] = viewMode.value[i] === 'vertical' ? 'horizontal' : 'vertical'
}
// Decide whether the original file can be rendered as an inline preview.
// Mirrors DocumentViewer.vue's detection (hasDisplayableOriginalFile +
// originalFileType): only PDFs and images are previewable. TXT files and
// row-by-row CSV/XLSX have no separate original (the extracted text IS the
// content); other types (CSV/XLSX full-document, DOCX, …) can't be shown
// inline. The caller hides the "View Original Document" button for these.
const analyzeOriginalFile = (d) => {
  const fileType = d?.original_file?.file_type
  if (!fileType) return { previewable: false }
  if (fileType === 'application/pdf' || fileType.startsWith('image/')) return { previewable: true }
  return { previewable: false }
}

const toggleDocumentPanel = async (i) => {
  showDocumentPanel.value[i] = !showDocumentPanel.value[i]
  if (!showDocumentPanel.value[i]) return
  // Already resolved — just show the existing preview
  if (documentPdfUrls.value[i] || documentPdfLoading.value[i]) return
  const meta = documentMeta.value[i]
  // No inline-previewable original (txt/csv/xlsx/…) → button is hidden, so this
  // should not be reachable; bail out defensively.
  if (!meta?.previewable || !meta?.fileId) return
  documentPdfLoading.value[i] = true
  try {
    const fr = await api.get(
      `/project/${props.projectId}/file/${meta.fileId}/content?preview=true`,
      { responseType: 'blob' },
    )
    const blob = new Blob([fr.data], { type: fr.headers['content-type'] })
    documentPdfUrls.value[i] = URL.createObjectURL(blob)
  } catch (err) {
    console.error(err)
    toast.error('Failed to load document')
  } finally {
    documentPdfLoading.value[i] = false
  }
}

watch(
  () => props.isModal,
  (v) => {
    document.body.style.overflow = v ? 'hidden' : ''
  },
)
onMounted(() => {
  fetchData()
  if (props.isModal) document.body.style.overflow = 'hidden'
})
onUnmounted(() => {
  try {
    Object.values(documentPdfUrls.value || {}).forEach((url) => {
      if (url) URL.revokeObjectURL(url)
    })
  } catch {
    // ignore cleanup errors
  }
  document.body.style.overflow = ''
})
</script>

<style>
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
.markdown-content h1 {
  font-size: 1.5em;
}
.markdown-content h2 {
  font-size: 1.25em;
}
.markdown-content h3 {
  font-size: 1.125em;
}
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
  font-family: SFMono-Regular, Consolas, Menlo, monospace;
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
</style>
