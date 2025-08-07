<!-- Landing.vue -->
<template>
  <div class="relative min-h-screen overflow-hidden bg-slate-950 text-white">
    <!-- Animated background elements -->
    <div class="absolute inset-0 z-0">
      <!-- Gradient orbs with medical theme colors -->
      <div class="absolute top-0 left-0 h-96 w-96 rounded-full bg-blue-500 opacity-10 blur-3xl animate-pulse"></div>
      <div class="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-indigo-500 opacity-10 blur-3xl animate-pulse" style="animation-delay: 2s"></div>
      <div class="absolute top-1/3 left-1/2 h-64 w-64 rounded-full bg-emerald-500 opacity-5 blur-3xl animate-pulse" style="animation-delay: 1s"></div>

      <!-- Grid pattern -->
      <div class="absolute inset-0 opacity-5"
           style="background-image: linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 24px 24px;">
      </div>

      <!-- Floating elements -->
      <div class="floating-element absolute top-20 left-10 font-mono text-xs text-blue-300 opacity-20">{"patient_id": "MED-2023-11"}</div>
      <div class="floating-element absolute top-60 right-20 font-mono text-xs text-emerald-300 opacity-20">[extraction_complete]</div>
      <div class="floating-element absolute bottom-40 left-40 font-mono text-xs text-indigo-300 opacity-20">schema.json</div>
      <div class="floating-element absolute bottom-20 right-60 font-mono text-xs text-purple-300 opacity-20">{"accuracy": 0.92}</div>
    </div>

    <!-- Main content -->
    <div class="relative z-10 mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <!-- Hero Section -->
      <div class="mb-20 text-center">
        <div class="mb-6 inline-block rounded-lg bg-gradient-to-r from-blue-600/20 to-indigo-600/20 border border-blue-500/30 p-3 backdrop-blur-sm">
          <span class="text-sm font-semibold tracking-wider uppercase bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            Medical Document Intelligence Platform
          </span>
        </div>
        <h1 class="mb-6 text-5xl font-extrabold sm:text-7xl">
          <span class="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
            LLMAIx-v2
          </span>
        </h1>
        <p class="mx-auto max-w-3xl text-xl text-slate-300 leading-relaxed">
          Transform unstructured medical documents into structured data using state-of-the-art
          Large Language Models with complete privacy and control over your extraction pipeline
        </p>
      </div>

      <!-- Interactive Pipeline Visualization -->
      <div class="mb-24">
        <h2 class="text-center text-3xl font-bold mb-12 text-white">How It Works</h2>

        <!-- Pipeline Container -->
        <div class="relative">
          <!-- Connection Lines (visible on desktop) -->
          <div class="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 -translate-y-1/2"></div>

          <!-- Pipeline Steps -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-8 lg:gap-4">

            <!-- Step 1: Upload -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Upload Files</h3>
                <p class="text-sm text-slate-400">PDF, Word, Images, CSV, Excel</p>
              </div>
            </div>

            <!-- Step 2: Preprocess -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-lg shadow-indigo-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Extract Text</h3>
                <p class="text-sm text-slate-400">OCR & Document Parsing</p>
              </div>
            </div>

            <!-- Step 3: Schema -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg shadow-purple-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Define Schema</h3>
                <p class="text-sm text-slate-400">Visual JSON Editor</p>
              </div>
            </div>

            <!-- Step 4: Prompt -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-pink-500 to-pink-600 shadow-lg shadow-pink-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Configure Prompt</h3>
                <p class="text-sm text-slate-400">Extraction Instructions</p>
              </div>
            </div>

            <!-- Step 5: Extract -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-lg shadow-emerald-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">LLM Extraction</h3>
                <p class="text-sm text-slate-400">OpenAI-Compatible API</p>
              </div>
            </div>

            <!-- Step 6: Results -->
            <div class="pipeline-step group relative">
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-teal-600 shadow-lg shadow-teal-500/30 group-hover:scale-110 transition-transform">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h8l4 4v12a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Structured Data</h3>
                <p class="text-sm text-slate-400">JSON Output & Metrics</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Interactive Demo Section -->
      <div class="mb-24">
        <h2 class="text-center text-3xl font-bold mb-12 text-white">See It In Action</h2>

        <div class="grid lg:grid-cols-2 gap-8 items-start">
          <!-- Input Document Preview -->
          <div class="space-y-4">
            <h3 class="text-xl font-semibold text-white mb-4">Medical Document</h3>
            <div class="rounded-lg border border-slate-700 bg-slate-900/50 backdrop-blur-sm p-6 font-mono text-sm text-slate-300 leading-relaxed">
              <div class="mb-4 text-blue-400">## Clinical Letter</div>
              <div class="mb-2"><span class="text-slate-500">Patient:</span> Sarah Lee, DOB: 03/04/1961</div>
              <div class="mb-2"><span class="text-slate-500">MRN:</span> 2123242</div>
              <div class="mb-4"><span class="text-slate-500">Date:</span> August 7, 2025</div>

              <div class="mb-2 text-slate-400">Dear Dr. General Practitioner,</div>

              <div class="mb-4">
                I am writing regarding our patient who was recently diagnosed with a
                <span class="bg-yellow-500/20 text-yellow-300 px-1 rounded">lung embolism</span>.
              </div>

              <div class="mb-2 font-semibold">Presenting Symptoms:</div>
              <div class="mb-4 ml-4">
                • <span class="bg-blue-500/20 text-blue-300 px-1 rounded">Shortness of breath</span><br/>
                • <span class="bg-blue-500/20 text-blue-300 px-1 rounded">Chest pain</span><br/>
                • No leg swelling observed
              </div>

              <div class="mb-2 font-semibold">Diagnosis:</div>
              <div class="ml-4">
                <span class="bg-green-500/20 text-green-300 px-1 rounded">Pulmonary embolism - bilateral</span>
              </div>
            </div>
          </div>

          <!-- Extracted JSON Output -->
          <div class="space-y-4">
            <h3 class="text-xl font-semibold text-white mb-4">Extracted Structured Data</h3>
            <div class="rounded-lg border border-slate-700 bg-slate-900/50 backdrop-blur-sm overflow-hidden">
              <div class="flex items-center justify-between border-b border-slate-700 bg-slate-800/50 px-4 py-2">
                <div class="flex items-center space-x-2">
                  <div class="h-3 w-3 rounded-full bg-red-500"></div>
                  <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
                  <div class="h-3 w-3 rounded-full bg-green-500"></div>
                </div>
                <div class="text-sm text-slate-400">output.json</div>
              </div>
              <div class="p-4 overflow-auto">
                <pre class="font-mono text-xs text-slate-300"><code>{
  <span class="text-emerald-400">"patient"</span>: {
    <span class="text-emerald-400">"name"</span>: <span class="text-yellow-300">"Sarah Lee"</span>,
    <span class="text-emerald-400">"date_of_birth"</span>: <span class="text-yellow-300">"1961-04-03"</span>,
    <span class="text-emerald-400">"mrn"</span>: <span class="text-yellow-300">"2123242"</span>
  },
  <span class="text-emerald-400">"diagnosis"</span>: {
    <span class="text-emerald-400">"primary"</span>: <span class="text-yellow-300">"Pulmonary embolism"</span>,
    <span class="text-emerald-400">"location"</span>: <span class="text-yellow-300">"bilateral"</span>
  },
  <span class="text-emerald-400">"symptoms"</span>: {
    <span class="text-emerald-400">"shortness_of_breath"</span>: <span class="text-blue-300">true</span>,
    <span class="text-emerald-400">"chest_pain"</span>: <span class="text-blue-300">true</span>,
    <span class="text-emerald-400">"leg_pain_or_swelling"</span>: <span class="text-blue-300">false</span>
  },
  <span class="text-emerald-400">"extraction_metadata"</span>: {
    <span class="text-emerald-400">"model"</span>: <span class="text-yellow-300">"gpt-4"</span>,
    <span class="text-emerald-400">"confidence"</span>: <span class="text-orange-400">0.92</span>,
    <span class="text-emerald-400">"processing_time"</span>: <span class="text-yellow-300">"1.2s"</span>
  }
}</code></pre>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Key Features Grid -->
      <div class="mb-24">
        <h2 class="text-center text-3xl font-bold mb-12 text-white">Built for Medical Research</h2>

        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <!-- Feature 1 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">Privacy-First Design</h3>
              <p class="text-sm text-slate-300">Process sensitive medical data locally or with your own hosted LLMs. Full control over your data pipeline.</p>
            </div>
          </div>

          <!-- Feature 2 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">Visual Schema Editor</h3>
              <p class="text-sm text-slate-300">Create complex nested JSON schemas with our intuitive tree-based editor. No coding required.</p>
            </div>
          </div>

          <!-- Feature 3 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-purple-500/50 hover:shadow-lg hover:shadow-purple-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400 group-hover:bg-purple-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">Multiple OCR Methods</h3>
              <p class="text-sm text-slate-300">Extract text from any document format using Tesseract, Surya-OCR, PaddleOCR, or vision LLMs.</p>
            </div>
          </div>

          <!-- Feature 4 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-emerald-500/50 hover:shadow-lg hover:shadow-emerald-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">Accuracy Evaluation</h3>
              <p class="text-sm text-slate-300">Compare extracted data against ground truth and calculate accuracy metrics for validation.</p>
            </div>
          </div>

          <!-- Feature 5 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-pink-500/50 hover:shadow-lg hover:shadow-pink-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-pink-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-pink-500/10 text-pink-400 group-hover:bg-pink-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">Flexible Trials</h3>
              <p class="text-sm text-slate-300">Run multiple extraction trials with different prompts, schemas, and temperature settings.</p>
            </div>
          </div>

          <!-- Feature 6 -->
          <div class="feature-card group relative overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 p-6 transition-all hover:border-teal-500/50 hover:shadow-lg hover:shadow-teal-500/10">
            <div class="absolute inset-0 bg-gradient-to-br from-teal-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="relative z-10">
              <div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-teal-500/10 text-teal-400 group-hover:bg-teal-500/20 transition-colors">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
              </div>
              <h3 class="mb-2 text-lg font-bold text-white">OpenAI-Compatible APIs</h3>
              <p class="text-sm text-slate-300">Use any LLM that supports the OpenAI API format, including local models via Ollama, vLLM, or llama.cpp.</p>
            </div>
          </div>
        </div>
      </div>

            <!-- CTA Section -->
      <div class="text-center">
        <div class="mb-8">
          <h2 class="text-3xl font-bold text-white mb-4">Ready to Transform Your Medical Data?</h2>
          <p class="text-xl text-slate-300">Join researchers extracting structured insights from medical documents</p>
        </div>

        <div v-if="authStore.isAuthenticated" class="mb-8">
          <router-link
            to="/projects"
            class="inline-flex items-center gap-2 transform rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 px-8 py-4 text-lg font-medium text-white shadow-lg transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:from-blue-600 hover:to-indigo-700"
          >
            Go to Projects
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
            </svg>
          </router-link>
        </div>

        <div v-else class="flex flex-col items-center gap-4 sm:flex-row sm:justify-center mb-8">
          <router-link
            to="/register"
            class="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 px-8 py-4 text-lg font-medium text-white shadow-lg transition hover:from-blue-600 hover:to-indigo-700 hover:shadow-xl"
          >
            Get Started
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
            </svg>
          </router-link>
          <router-link
            to="/login"
            class="inline-flex items-center gap-2 rounded-full bg-white/10 backdrop-blur-sm text-white px-8 py-4 text-lg font-medium border border-white/20 transition hover:bg-white/20 hover:border-white/30"
          >
            Login
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
            </svg>
          </router-link>
        </div>

        <!-- GitHub Link -->
        <div class="mt-8">
          <a
            href="https://github.com/KatherLab/llmaixweb"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
          >
            <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            View on KatherLab GitHub
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { onMounted, onUnmounted } from 'vue'

const authStore = useAuthStore()

// Add smooth animations on mount
onMounted(() => {
  // Animate floating elements
  const floatingElements = document.querySelectorAll('.floating-element')
  floatingElements.forEach((el, index) => {
    el.style.animation = `float ${15 + index * 2}s ease-in-out infinite`
    el.style.animationDelay = `${index * 0.5}s`
  })

  // Animate pipeline steps on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-fade-in-up')
      }
    })
  }, { threshold: 0.1 })

  document.querySelectorAll('.pipeline-step').forEach((el) => {
    observer.observe(el)
  })

  // Animate feature cards
  document.querySelectorAll('.feature-card').forEach((el, index) => {
    el.style.animationDelay = `${index * 0.1}s`
    observer.observe(el)
  })
})
</script>

<style scoped>
/* Floating animation */
@keyframes float {
  0%, 100% {
    transform: translateY(0) translateX(0) rotate(0deg);
    opacity: 0.2;
  }
  25% {
    transform: translateY(-20px) translateX(10px) rotate(1deg);
    opacity: 0.3;
  }
  50% {
    transform: translateY(10px) translateX(-10px) rotate(-1deg);
    opacity: 0.2;
  }
  75% {
    transform: translateY(-15px) translateX(5px) rotate(0.5deg);
    opacity: 0.25;
  }
}

/* Fade in up animation */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
}

/* Pipeline step animation */
.pipeline-step {
  opacity: 0;
  transform: translateY(20px);
}

.pipeline-step.animate-fade-in-up {
  opacity: 1;
  transform: translateY(0);
}

/* Feature card hover effects */
.feature-card {
  opacity: 0;
  transform: translateY(20px);
}

.feature-card.animate-fade-in-up {
  opacity: 1;
  transform: translateY(0);
}

/* Gradient text animation */
@keyframes gradient-shift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.bg-gradient-to-r {
  background-size: 200% 200%;
}

h1 .bg-gradient-to-r {
  animation: gradient-shift 6s ease infinite;
}

/* Code syntax highlighting for JSON preview */
.text-emerald-400 { color: #34d399; }
.text-yellow-300 { color: #fcd34d; }
.text-blue-300 { color: #93c5fd; }
.text-purple-400 { color: #c084fc; }
.text-orange-400 { color: #fb923c; }
.text-slate-500 { color: #64748b; }

/* Pulse animation for orbs */
@keyframes pulse {
  0%, 100% {
    opacity: 0.1;
    transform: scale(1);
  }
  50% {
    opacity: 0.15;
    transform: scale(1.1);
  }
}

.animate-pulse {
  animation: pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Interactive hover states */
.group:hover .group-hover\:scale-110 {
  transform: scale(1.1);
}

.group:hover .group-hover\:bg-blue-500\/20 {
  background-color: rgb(59 130 246 / 0.2);
}

/* Smooth transitions */
* {
  transition-property: transform, opacity, background-color, border-color, box-shadow;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .floating-element {
    display: none;
  }

  h1 {
    font-size: 3rem;
  }

  .pipeline-step {
    margin-bottom: 2rem;
  }
}
</style>
