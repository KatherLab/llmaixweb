<!-- Landing.vue -->
<template>
  <div class="relative min-h-screen overflow-hidden bg-slate-900 text-white">
    <!-- Background elements -->
    <div class="absolute inset-0 z-0">
      <div class="absolute top-0 left-0 h-64 w-64 rounded-full bg-blue-500 opacity-10 blur-3xl"></div>
      <div class="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-purple-500 opacity-10 blur-3xl"></div>
      <div class="absolute top-1/4 right-1/4 h-64 w-64 rounded-full bg-emerald-500 opacity-5 blur-3xl"></div>

      <!-- Subtle grid pattern -->
      <div class="absolute inset-0 opacity-5"
           style="background-image: linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 24px 24px;">
      </div>

      <!-- Floating code snippets -->
      <div class="absolute top-20 left-10 font-mono text-xs text-blue-300 opacity-20">{"diagnosis": "pulmonary_embolism"}</div>
      <div class="absolute top-60 right-20 font-mono text-xs text-blue-300 opacity-20">[extract_successful]</div>
      <div class="absolute bottom-40 left-40 font-mono text-xs text-blue-300 opacity-20">results.json</div>
      <div class="absolute bottom-20 right-60 font-mono text-xs text-blue-300 opacity-20">{"confidence": 0.98}</div>
    </div>

    <!-- Main content -->
    <div class="relative z-10 mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="mb-16 text-center">
        <div class="mb-4 inline-block rounded-lg bg-blue-600 bg-opacity-30 p-2 backdrop-blur-sm">
          <span class="text-sm font-semibold tracking-wider">MEDICAL INFORMATION EXTRACTION</span>
        </div>
        <h1 class="mb-6 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-5xl font-extrabold text-transparent sm:text-6xl">
          LLMAIx-v2
        </h1>
        <p class="mx-auto max-w-2xl text-xl text-blue-100">
          An open source pipeline for information extraction from unstructured
          medical text using privacy-preserving Large Language Models
        </p>
      </div>

      <!-- Workflow Section -->
      <div class="mb-16">
        <!-- Workflow steps container -->
        <div class="relative">
          <!-- Connecting line -->
          <div class="absolute left-1/2 top-0 h-full w-1 -translate-x-1/2 bg-gradient-to-b from-blue-500 via-indigo-500 to-emerald-500 lg:left-0 lg:h-1 lg:w-full lg:translate-x-0 lg:translate-y-32 lg:bg-gradient-to-r"></div>

          <!-- Steps -->
          <div class="flex flex-col items-center space-y-24 lg:flex-row lg:items-start lg:space-y-0 lg:space-x-8">
            <!-- Step 1: Preprocessing -->
            <div class="relative w-full max-w-md transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-blue-500/20 lg:w-1/3">
              <div class="absolute -top-8 left-1/2 flex h-16 w-16 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/30 lg:left-32">
                <span class="text-xl font-bold">1</span>
              </div>
              <div class="mt-8 text-center">
                <h2 class="mb-4 text-2xl font-bold text-white">Preprocessing</h2>
                <ul class="space-y-3 text-left text-slate-300">
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Extract text from PDFs with docling, pymupdf4llm and markitdown
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Multiple OCR methods: tesseract, surya-ocr and vision LLM
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Support for multiple formats: PDF, DOCX, images (PNG, JPEG), CSV, XLSX
                  </li>
                </ul>
              </div>
              <div class="mt-6 text-center">
                <div class="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-sm">
                  <span class="mr-2 h-2 w-2 rounded-full bg-blue-400"></span>
                  Data preparation
                </div>
              </div>
            </div>

            <!-- Step 2: LLM Analysis -->
            <div class="relative w-full max-w-md transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-indigo-500/20 lg:w-1/3">
              <div class="absolute -top-8 left-1/2 flex h-16 w-16 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/30 lg:left-32">
                <span class="text-xl font-bold">2</span>
              </div>
              <div class="mt-8 text-center">
                <h2 class="mb-4 text-2xl font-bold text-white">LLM Analysis</h2>
                <ul class="space-y-3 text-left text-slate-300">
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Compatible with any OpenAI-compatible LLM
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Zero-shot entity extraction with prompt engineering
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Privacy-preserving local processing
                  </li>
                </ul>
              </div>
              <div class="mt-6 text-center">
                <div class="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-sm">
                  <span class="mr-2 h-2 w-2 rounded-full bg-indigo-400"></span>
                  Information extraction
                </div>
              </div>
            </div>

            <!-- Step 3: Structured Output -->
            <div class="relative w-full max-w-md transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-emerald-500/20 lg:w-1/3">
              <div class="absolute -top-8 left-1/2 flex h-16 w-16 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/30 lg:left-32">
                <span class="text-xl font-bold">3</span>
              </div>
              <div class="mt-8 text-center">
                <h2 class="mb-4 text-2xl font-bold text-white">Structured Output</h2>
                <ul class="space-y-3 text-left text-slate-300">
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Generate standardized JSON output
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Consistent schema across documents
                  </li>
                  <li class="flex items-start">
                    <svg class="mr-2 mt-1 h-4 w-4 shrink-0 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                    Ready for downstream applications
                  </li>
                </ul>
              </div>
              <div class="mt-6 text-center">
                <div class="inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-sm">
                  <span class="mr-2 h-2 w-2 rounded-full bg-emerald-400"></span>
                  Structured data
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- JSON Preview -->
      <div class="mx-auto mb-16 max-w-3xl overflow-hidden rounded-lg border border-slate-700 bg-slate-900 shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-4 py-2">
          <div class="flex items-center space-x-2">
            <div class="h-3 w-3 rounded-full bg-red-500"></div>
            <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
            <div class="h-3 w-3 rounded-full bg-green-500"></div>
          </div>
          <div class="text-sm text-slate-400">output.json</div>
          <div class="text-sm text-slate-400">42 KB</div>
        </div>
        <div class="overflow-auto p-4">
          <pre class="font-mono text-xs text-slate-300"><span class="text-blue-400">{</span>
  <span class="text-emerald-400">"document"</span><span class="text-slate-500">:</span> <span class="text-blue-400">{</span>
    <span class="text-emerald-400">"id"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"MED-2023-11"</span><span class="text-slate-500">,</span>
    <span class="text-emerald-400">"type"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"clinical_letter"</span><span class="text-slate-500">,</span>
    <span class="text-emerald-400">"extracted_data"</span><span class="text-slate-500">:</span> <span class="text-blue-400">{</span>
      <span class="text-emerald-400">"diagnosis"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"Pulmonary embolism"</span><span class="text-slate-500">,</span>
      <span class="text-emerald-400">"symptoms"</span><span class="text-slate-500">:</span> <span class="text-purple-400">[</span>
        <span class="text-blue-400">{</span> <span class="text-emerald-400">"type"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"shortness_of_breath"</span><span class="text-slate-500">,</span> <span class="text-emerald-400">"present"</span><span class="text-slate-500">:</span> <span class="text-red-400">true</span> <span class="text-blue-400">}</span><span class="text-slate-500">,</span>
        <span class="text-blue-400">{</span> <span class="text-emerald-400">"type"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"chest_pain"</span><span class="text-slate-500">,</span> <span class="text-emerald-400">"present"</span><span class="text-slate-500">:</span> <span class="text-red-400">true</span> <span class="text-blue-400">}</span><span class="text-slate-500">,</span>
        <span class="text-blue-400">{</span> <span class="text-emerald-400">"type"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"leg_pain"</span><span class="text-slate-500">,</span> <span class="text-emerald-400">"present"</span><span class="text-slate-500">:</span> <span class="text-red-400">false</span> <span class="text-blue-400">}</span>
      <span class="text-purple-400">]</span><span class="text-slate-500">,</span>
      <span class="text-emerald-400">"embolism_side"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"bilateral"</span><span class="text-slate-500">,</span>
      <span class="text-emerald-400">"tnm_stage"</span><span class="text-slate-500">:</span> <span class="text-blue-400">{</span>
        <span class="text-emerald-400">"t"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"T3"</span><span class="text-slate-500">,</span>
        <span class="text-emerald-400">"n"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"N1"</span><span class="text-slate-500">,</span>
        <span class="text-emerald-400">"m"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"M0"</span>
      <span class="text-blue-400">}</span>
    <span class="text-blue-400">}</span><span class="text-slate-500">,</span>
    <span class="text-emerald-400">"confidence_score"</span><span class="text-slate-500">:</span> <span class="text-orange-400">0.97</span><span class="text-slate-500">,</span>
    <span class="text-emerald-400">"processing_time"</span><span class="text-slate-500">:</span> <span class="text-yellow-400">"1.2s"</span>
  <span class="text-blue-400">}</span>
<span class="text-blue-400">}</span></pre>
        </div>
      </div>

      <!-- Features Section -->
      <div class="mx-auto grid max-w-4xl gap-8 md:grid-cols-2">
        <div class="transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-blue-500/10">
          <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500 bg-opacity-20 text-blue-400">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
          </div>
          <h3 class="mb-2 text-lg font-bold text-white">Privacy Preserving</h3>
          <p class="text-slate-300">Process medical documents locally without transferring sensitive patient data to external servers.</p>
        </div>

        <div class="transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-indigo-500/10">
          <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-500 bg-opacity-20 text-indigo-400">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
            </svg>
          </div>
          <h3 class="mb-2 text-lg font-bold text-white">Model Flexibility</h3>
          <p class="text-slate-300">Use any OpenAI-compatible LLM according to your specific needs, whether open-source or commercial.</p>
        </div>

        <div class="transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-purple-500/10">
          <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-purple-500 bg-opacity-20 text-purple-400">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
            </svg>
          </div>
          <h3 class="mb-2 text-lg font-bold text-white">No Coding Required</h3>
          <p class="text-slate-300">Intuitive graphical interface allows medical researchers to extract information without programming knowledge.</p>
        </div>

        <div class="transform rounded-xl border border-slate-700 bg-slate-800 bg-opacity-75 p-6 shadow-xl backdrop-blur-sm transition duration-300 hover:-translate-y-1 hover:shadow-emerald-500/10">
          <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500 bg-opacity-20 text-emerald-400">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path>
            </svg>
          </div>
          <h3 class="mb-2 text-lg font-bold text-white">Structured Data Output</h3>
          <p class="text-slate-300">Convert unstructured clinical text into standardized JSON format for quantitative analysis.</p>
        </div>
      </div>

      <div class="mt-16 text-center">
        <div v-if="authStore.isAuthenticated">
          <router-link
            to="/projects"
            class="transform rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 px-8 py-3 font-medium text-white shadow-lg transition duration-300 hover:-translate-y-1 hover:shadow-xl"
          >
            Go to Projects
          </router-link>
        </div>
        <div v-else class="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <router-link
            to="/login"
            class="rounded-full bg-blue-600 px-8 py-3 font-medium text-white shadow-lg transition hover:bg-blue-700 text-lg"
          >
            Login
          </router-link>
          <router-link
            to="/register"
            class="rounded-full bg-white text-blue-600 px-8 py-3 font-medium shadow-lg border border-blue-600 transition hover:bg-blue-50 text-lg"
          >
            Register
          </router-link>
        </div>
        <p class="mt-4 text-slate-400">Experience the future of medical data extraction</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
const authStore = useAuthStore()
</script>

<style scoped>
/* Any additional styles that can't be handled by Tailwind */
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.json-animate-fade {
  animation: fadeIn 2s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
