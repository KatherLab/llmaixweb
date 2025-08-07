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
          <div class="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 -translate-y-1/2 z-0"></div>

          <!-- Pipeline Steps -->
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-8 lg:gap-4 relative z-10">

            <!-- Step 1: Upload -->
            <div
              @click="activeStep = activeStep === 1 ? null : 1"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/30 transition-all duration-300"
                     :class="activeStep === 1 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Upload Files</h3>
                <p class="text-sm text-slate-400">Multiple formats supported</p>
              </div>
            </div>

            <!-- Step 2: Preprocess -->
            <div
              @click="activeStep = activeStep === 2 ? null : 2"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-lg shadow-indigo-500/30 transition-all duration-300"
                     :class="activeStep === 2 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Preprocess</h3>
                <p class="text-sm text-slate-400">Extract & OCR text</p>
              </div>
            </div>

            <!-- Step 3: Documents -->
            <div
              @click="activeStep = activeStep === 3 ? null : 3"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg shadow-purple-500/30 transition-all duration-300"
                     :class="activeStep === 3 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-2 0V5a2 2 0 00-2-2H7a2 2 0 00-2 2v2m14 0H5"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Documents</h3>
                <p class="text-sm text-slate-400">Organize & group</p>
              </div>
            </div>

            <!-- Step 4: Schema -->
            <div
              @click="activeStep = activeStep === 4 ? null : 4"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-pink-500 to-pink-600 shadow-lg shadow-pink-500/30 transition-all duration-300"
                     :class="activeStep === 4 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Schemas</h3>
                <p class="text-sm text-slate-400">Define structure</p>
              </div>
            </div>

            <!-- Step 5: Run Trials -->
            <div
              @click="activeStep = activeStep === 5 ? null : 5"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-lg shadow-emerald-500/30 transition-all duration-300"
                     :class="activeStep === 5 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Run Trials</h3>
                <p class="text-sm text-slate-400">LLM extraction</p>
              </div>
            </div>

            <!-- Step 6: Evaluation -->
            <div
              @click="activeStep = activeStep === 6 ? null : 6"
              class="pipeline-step group relative cursor-pointer transform transition-all hover:scale-105"
            >
              <div class="relative z-10 flex flex-col items-center text-center">
                <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-teal-600 shadow-lg shadow-teal-500/30 transition-all duration-300"
                     :class="activeStep === 6 ? 'scale-110 shadow-xl' : ''">
                  <svg class="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h8l4 4v12a2 2 0 01-2 2z"></path>
                  </svg>
                </div>
                <h3 class="font-bold text-white mb-2">Evaluation</h3>
                <p class="text-sm text-slate-400">Accuracy metrics</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Step Details (Expandable) -->
        <transition name="fade-slide">
          <div v-if="activeStep" class="mt-12 mx-auto max-w-4xl">
            <div class="rounded-xl border border-slate-700 bg-slate-900/50 backdrop-blur-sm p-8">
              <!-- Step 1 Details -->
              <div v-if="activeStep === 1" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">Upload Medical Documents</h3>
                <div class="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 class="text-lg font-semibold text-blue-400 mb-3">Supported Formats</h4>
                    <div class="space-y-2">
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                          <span class="text-xs font-bold text-blue-400">PDF</span>
                        </div>
                        <span class="text-slate-300">PDF documents with text or scanned images</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                          <span class="text-xs font-bold text-indigo-400">DOC</span>
                        </div>
                        <span class="text-slate-300">Word documents (DOCX, DOC)</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                          <span class="text-xs font-bold text-purple-400">IMG</span>
                        </div>
                        <span class="text-slate-300">Images (PNG, JPEG) with OCR support</span>
                      </div>
                      <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                          <span class="text-xs font-bold text-emerald-400">CSV</span>
                        </div>
                        <span class="text-slate-300">Structured data (CSV, XLSX)</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 class="text-lg font-semibold text-blue-400 mb-3">Features</h4>
                    <ul class="space-y-2 text-slate-300">
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Batch upload multiple files
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Automatic format detection
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Secure local processing
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <!-- Step 2 Details -->
              <div v-if="activeStep === 2" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">Advanced Text Extraction</h3>
                <div class="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 class="text-lg font-semibold text-indigo-400 mb-3">OCR Methods</h4>
                    <div class="space-y-3">
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">Tesseract OCR</h5>
                        <p class="text-sm text-slate-400">Industry-standard OCR for printed text</p>
                      </div>
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">Surya-OCR</h5>
                        <p class="text-sm text-slate-400">Advanced neural OCR for complex layouts</p>
                      </div>
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">PaddleOCR</h5>
                        <p class="text-sm text-slate-400">Multi-language support with high accuracy</p>
                      </div>
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">Vision LLMs</h5>
                        <p class="text-sm text-slate-400">AI-powered text extraction from images</p>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 class="text-lg font-semibold text-indigo-400 mb-3">Document Parsers</h4>
                    <div class="space-y-3">
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">Docling</h5>
                        <p class="text-sm text-slate-400">IBM's document understanding library</p>
                      </div>
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">PyMuPDF4LLM</h5>
                        <p class="text-sm text-slate-400">Optimized PDF parsing for LLMs</p>
                      </div>
                      <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                        <h5 class="font-semibold text-white mb-1">MarkItDown</h5>
                        <p class="text-sm text-slate-400">Convert documents to clean markdown</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 3 Details -->
              <div v-if="activeStep === 3" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">Document Management</h3>
                <div class="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 class="text-lg font-semibold text-purple-400 mb-3">Organization Features</h4>
                    <ul class="space-y-2 text-slate-300">
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Create document groups for batch processing
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Tag and categorize documents
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Search and filter by metadata
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        View extracted text preview
                      </li>
                    </ul>
                  </div>
                  <div>
                    <h4 class="text-lg font-semibold text-purple-400 mb-3">Flexible Selection</h4>
                    <p class="text-slate-300 mb-3">Choose documents for trials in two ways:</p>
                    <div class="space-y-3">
                      <div class="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
                        <h5 class="font-semibold text-white mb-1">Document Groups</h5>
                        <p class="text-sm text-slate-400">Process entire groups at once</p>
                      </div>
                      <div class="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
                        <h5 class="font-semibold text-white mb-1">Individual Selection</h5>
                        <p class="text-sm text-slate-400">Hand-pick specific documents</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 4 Details -->
              <div v-if="activeStep === 4" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">Visual Schema Editor</h3>
                <div class="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 class="text-lg font-semibold text-pink-400 mb-3">Tree-Based Editor</h4>
                    <div class="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                      <div class="font-mono text-sm space-y-2">
                        <div class="flex items-center gap-2">
                          <span class="text-slate-500">▼</span>
                          <span class="text-orange-400">patient</span>
                          <span class="text-slate-500">:</span>
                          <span class="text-blue-400">object</span>
                        </div>
                        <div class="ml-6 space-y-2">
                          <div class="flex items-center gap-2">
                            <span class="text-emerald-400">patient_id</span>
                            <span class="text-slate-500">:</span>
                            <span class="text-yellow-400">string</span>
                          </div>
                          <div class="flex items-center gap-2">
                            <span class="text-emerald-400">first_name</span>
                            <span class="text-slate-500">:</span>
                            <span class="text-yellow-400">string</span>
                          </div>
                          <div class="flex items-center gap-2">
                            <span class="text-emerald-400">diagnosis</span>
                            <span class="text-slate-500">:</span>
                            <span class="text-purple-400">array</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <p class="text-sm text-slate-400 mt-3">
                      Create complex nested structures with drag-and-drop
                    </p>
                  </div>
                  <div>
                    <h4 class="text-lg font-semibold text-pink-400 mb-3">Schema Features</h4>
                    <ul class="space-y-2 text-slate-300">
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Support for nested objects and arrays
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        All JSON data types supported
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Import/export JSON schemas
                      </li>
                      <li class="flex items-start gap-2">
                        <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        Schema validation and templates
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

                            <!-- Step 5 Details -->
              <div v-if="activeStep === 5" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">LLM-Powered Extraction</h3>
                <div class="space-y-6">
                  <!-- Visual Flow -->
                  <div class="p-6 rounded-lg bg-slate-800/30 border border-slate-700">
                    <div class="flex items-center justify-between gap-4">
                      <div class="text-center">
                        <div class="w-16 h-16 mx-auto mb-2 rounded-lg bg-blue-500/20 flex items-center justify-center">
                          <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                          </svg>
                        </div>
                        <p class="text-sm text-slate-400">Document</p>
                      </div>
                      <div class="flex-1 flex items-center">
                        <div class="w-full h-0.5 bg-gradient-to-r from-blue-500 to-indigo-500"></div>
                        <svg class="w-6 h-6 text-indigo-500 -ml-1" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                        </svg>
                      </div>
                      <div class="text-center">
                        <div class="w-16 h-16 mx-auto mb-2 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                          <svg class="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-4l-4 4z"></path>
                          </svg>
                        </div>
                        <p class="text-sm text-slate-400">Prompt</p>
                      </div>
                      <div class="flex-1 flex items-center">
                        <div class="w-full h-0.5 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
                        <svg class="w-6 h-6 text-purple-500 -ml-1" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                        </svg>
                      </div>
                      <div class="text-center">
                        <div class="w-16 h-16 mx-auto mb-2 rounded-lg bg-purple-500/20 flex items-center justify-center">
                          <svg class="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4"></path>
                          </svg>
                        </div>
                        <p class="text-sm text-slate-400">Schema</p>
                      </div>
                      <div class="flex-1 flex items-center">
                        <div class="w-full h-0.5 bg-gradient-to-r from-purple-500 to-emerald-500"></div>
                        <svg class="w-6 h-6 text-emerald-500 -ml-1" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                        </svg>
                      </div>
                      <div class="text-center">
                        <div class="w-16 h-16 mx-auto mb-2 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                          <svg class="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                          </svg>
                        </div>
                        <p class="text-sm text-slate-400">LLM API</p>
                      </div>
                      <div class="flex-1 flex items-center">
                        <div class="w-full h-0.5 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
                        <svg class="w-6 h-6 text-teal-500 -ml-1" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                        </svg>
                      </div>
                      <div class="text-center">
                        <div class="w-16 h-16 mx-auto mb-2 rounded-lg bg-teal-500/20 flex items-center justify-center">
                          <span class="text-2xl font-mono text-teal-400">{}</span>
                        </div>
                        <p class="text-sm text-slate-400">JSON Output</p>
                      </div>
                    </div>
                  </div>

                  <div class="grid md:grid-cols-2 gap-6">
                    <div>
                      <h4 class="text-lg font-semibold text-emerald-400 mb-3">Compatible LLM Providers</h4>
                      <div class="space-y-2">
                        <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                          <h5 class="font-semibold text-white mb-1">OpenAI API</h5>
                          <p class="text-sm text-slate-400">GPT-4, GPT-3.5-turbo</p>
                        </div>
                        <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                          <h5 class="font-semibold text-white mb-1">Local Models</h5>
                          <p class="text-sm text-slate-400">Ollama, llama.cpp, vLLM</p>
                        </div>
                        <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                          <h5 class="font-semibold text-white mb-1">Custom Endpoints</h5>
                          <p class="text-sm text-slate-400">Any OpenAI-compatible API</p>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 class="text-lg font-semibold text-emerald-400 mb-3">Trial Configuration</h4>
                      <ul class="space-y-2 text-slate-300">
                        <li class="flex items-start gap-2">
                          <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                          </svg>
                          Configure temperature for consistency
                        </li>
                        <li class="flex items-start gap-2">
                          <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                          </svg>
                          Run multiple iterations per trial
                        </li>
                        <li class="flex items-start gap-2">
                          <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                          </svg>
                          Compare different prompts & models
                        </li>
                        <li class="flex items-start gap-2">
                          <svg class="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                          </svg>
                          Track token usage and costs
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Step 6 Details -->
              <div v-if="activeStep === 6" class="space-y-4">
                <h3 class="text-2xl font-bold text-white mb-4">Accuracy Evaluation</h3>
                <div class="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 class="text-lg font-semibold text-teal-400 mb-3">Evaluation Process</h4>
                    <div class="space-y-3">
                      <div class="flex items-start gap-3">
                        <div class="w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span class="text-sm font-bold text-teal-400">1</span>
                        </div>
                        <div>
                          <h5 class="font-semibold text-white">Upload Ground Truth</h5>
                          <p class="text-sm text-slate-400">Provide validated JSON data</p>
                        </div>
                      </div>
                      <div class="flex items-start gap-3">
                        <div class="w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span class="text-sm font-bold text-teal-400">2</span>
                        </div>
                        <div>
                          <h5 class="font-semibold text-white">Compare Extractions</h5>
                          <p class="text-sm text-slate-400">Field-by-field comparison</p>
                        </div>
                      </div>
                      <div class="flex items-start gap-3">
                        <div class="w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span class="text-sm font-bold text-teal-400">3</span>
                        </div>
                        <div>
                          <h5 class="font-semibold text-white">Calculate Metrics</h5>
                          <p class="text-sm text-slate-400">Overall and per-field accuracy</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 class="text-lg font-semibold text-teal-400 mb-3">Metrics Dashboard</h4>
                    <div class="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                      <div class="space-y-3">
                        <div class="flex justify-between items-center">
                          <span class="text-slate-300">Overall Accuracy</span>
                          <span class="text-2xl font-bold text-teal-400">92.2%</span>
                        </div>
                        <div class="w-full bg-slate-700 rounded-full h-2">
                          <div class="bg-gradient-to-r from-teal-500 to-emerald-500 h-2 rounded-full" style="width: 92.2%"></div>
                        </div>
                        <div class="grid grid-cols-2 gap-2 mt-4">
                          <div class="text-center p-2 rounded bg-slate-800">
                            <p class="text-xs text-slate-400">Documents</p>
                            <p class="text-lg font-bold text-white">8</p>
                          </div>
                          <div class="text-center p-2 rounded bg-slate-800">
                            <p class="text-xs text-slate-400">Field Errors</p>
                            <p class="text-lg font-bold text-white">5</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Close button -->
              <button
                @click="activeStep = null"
                class="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          </div>
        </transition>
      </div>

      <!-- Interactive Demo Section -->
      <div class="mb-24">
        <h2 class="text-center text-3xl font-bold mb-12 text-white">See It In Action</h2>

        <div class="grid lg:grid-cols-2 gap-8 items-start">
          <!-- Input Document Preview -->
          <div class="space-y-4">
            <h3 class="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              Medical Document
            </h3>
            <div class="rounded-lg border border-slate-700 bg-slate-900/50 backdrop-blur-sm p-6 font-mono text-sm text-slate-300 leading-relaxed overflow-hidden relative">
              <!-- Animated highlight effect -->
              <div class="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/10 to-transparent -skew-x-12 animate-shimmer"></div>

              <div class="relative z-10">
                <div class="mb-4 text-blue-400">## Clinical Letter</div>
                <div class="mb-2"><span class="text-slate-500">Patient:</span> <span class="highlight-patient">Sarah Lee</span>, DOB: <span class="highlight-dob">03/04/1961</span></div>
                <div class="mb-2"><span class="text-slate-500">MRN:</span> <span class="highlight-mrn">2123242</span></div>
                <div class="mb-4"><span class="text-slate-500">Date:</span> August 7, 2025</div>

                <div class="mb-2 text-slate-400">Dear Dr. General Practitioner,</div>

                <div class="mb-4">
                  I am writing regarding our patient who was recently diagnosed with a
                  <span class="highlight-diagnosis bg-yellow-500/20 text-yellow-300 px-1 rounded">lung embolism</span>.
                </div>

                <div class="mb-2 font-semibold">Presenting Symptoms:</div>
                <div class="mb-4 ml-4">
                  • <span class="highlight-symptom bg-blue-500/20 text-blue-300 px-1 rounded">Shortness of breath</span><br/>
                  • <span class="highlight-symptom bg-blue-500/20 text-blue-300 px-1 rounded">Chest pain</span><br/>
                  • No leg swelling observed
                </div>

                <div class="mb-2 font-semibold">Diagnosis:</div>
                <div class="ml-4">
                  <span class="highlight-location bg-green-500/20 text-green-300 px-1 rounded">Pulmonary embolism - bilateral</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Extracted JSON Output -->
          <div class="space-y-4">
            <h3 class="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <span class="text-2xl font-mono text-emerald-400">{}</span>
              Extracted Structured Data
            </h3>
            <div class="rounded-lg border border-slate-700 bg-slate-900/50 backdrop-blur-sm overflow-hidden">
              <div class="flex items-center justify-between border-b border-slate-700 bg-slate-800/50 px-4 py-2">
                <div class="flex items-center space-x-2">
                  <div class="h-3 w-3 rounded-full bg-red-500"></div>
                  <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
                  <div class="h-3 w-3 rounded-full bg-green-500"></div>
                </div>
                <div class="text-sm text-slate-400">output.json</div>
                <button class="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded hover:bg-emerald-500/30 transition-colors">
                  Copy
                </button>
              </div>
              <div class="p-4 overflow-auto max-h-96">
                <pre class="font-mono text-xs text-slate-300"><code>{
  <span class="text-emerald-400">"patient"</span>: {
    <span class="text-emerald-400">"name"</span>: <span class="text-yellow-300 highlight-target-patient">"Sarah Lee"</span>,
    <span class="text-emerald-400">"date_of_birth"</span>: <span class="text-yellow-300 highlight-target-dob">"1961-04-03"</span>,
    <span class="text-emerald-400">"mrn"</span>: <span class="text-yellow-300 highlight-target-mrn">"2123242"</span>
  },
  <span class="text-emerald-400">"diagnosis"</span>: {
    <span class="text-emerald-400">"primary"</span>: <span class="text-yellow-300 highlight-target-diagnosis">"Pulmonary embolism"</span>,
    <span class="text-emerald-400">"location"</span>: <span class="text-yellow-300 highlight-target-location">"bilateral"</span>
  },
  <span class="text-emerald-400">"symptoms"</span>: {
    <span class="text-emerald-400">"shortness_of_breath"</span>: <span class="text-blue-300">true</span>,
    <span class="text-emerald-400">"chest_pain"</span>: <span class="text-blue-300">true</span>,
    <span class="text-emerald-400">"leg_pain_or_swelling"</span>: <span class="text-blue-300">false</span>
  },
  <span class="text-emerald-400">"extraction_metadata"</span>: {
    <span class="text-emerald-400">"model"</span>: <span class="text-yellow-300">"gpt-4"</span>,
    <span class="text-emerald-400">"confidence"</span>: <span class="text-orange-400">0.92</span>,
    <span class="text-emerald-400">"processing_time"</span>: <span class="text-yellow-300">"1.2s"</span>,
    <span class="text-emerald-400">"tokens_used"</span>: <span class="text-orange-400">2769</span>
  }
}</code></pre>
              </div>
            </div>

            <!-- Connection lines animation -->
            <div class="mt-4 flex justify-center">
              <div class="flex items-center gap-2 text-sm text-slate-400">
                <svg class="w-4 h-4 animate-pulse text-emerald-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>Extraction complete with 92% accuracy</span>
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
              <h3 class="mb-2 text-lg font-bold text-white">Advanced OCR Pipeline</h3>
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
            href="https://github.com/KatherLab"
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

    <!-- Footer -->
    <div class="relative z-10 mt-24 border-t border-slate-800 py-8">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div class="text-sm text-slate-400">
            © 2025 LLMAIx-v2. Developed by KatherLab for the medical research community.
          </div>
          <div class="flex items-center gap-6 text-sm text-slate-400">
            <span>Privacy-First Medical Data Extraction</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { ref, onMounted, onUnmounted } from 'vue'

const authStore = useAuthStore()
const activeStep = ref(null)

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

  // Interactive hover effects for demo section
  const highlightPairs = [
    { source: '.highlight-patient', target: '.highlight-target-patient' },
    { source: '.highlight-dob', target: '.highlight-target-dob' },
    { source: '.highlight-mrn', target: '.highlight-target-mrn' },
    { source: '.highlight-diagnosis', target: '.highlight-target-diagnosis' },
    { source: '.highlight-location', target: '.highlight-target-location' }
  ]

  highlightPairs.forEach(pair => {
    const sourceEl = document.querySelector(pair.source)
    const targetEl = document.querySelector(pair.target)

    if (sourceEl && targetEl) {
      sourceEl.addEventListener('mouseenter', () => {
        sourceEl.classList.add('bg-yellow-500/40', 'scale-105')
        targetEl.classList.add('bg-yellow-500/40', 'scale-105')
      })

      sourceEl.addEventListener('mouseleave', () => {
        sourceEl.classList.remove('bg-yellow-500/40', 'scale-105')
        targetEl.classList.remove('bg-yellow-500/40', 'scale-105')
      })
    }
  })
})

// Clean up observers
onUnmounted(() => {
  // Cleanup code if needed
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

/* Shimmer effect for demo section */
@keyframes shimmer {
  0% {
    transform: translateX(-100%) skewX(-12deg);
  }
  100% {
    transform: translateX(200%) skewX(-12deg);
  }
}

.animate-shimmer {
  animation: shimmer 8s infinite;
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

/* Highlight transitions for demo */
.highlight-patient,
.highlight-dob,
.highlight-mrn,
.highlight-diagnosis,
.highlight-symptom,
.highlight-location,
.highlight-target-patient,
.highlight-target-dob,
.highlight-target-mrn,
.highlight-target-diagnosis,
.highlight-target-location {
  transition: all 0.3s ease;
  cursor: pointer;
}

/* Step details fade transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  transform: translateY(-20px);
  opacity: 0;
}

.fade-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
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

