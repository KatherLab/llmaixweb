<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-slate-900 dark:text-white">
      See It In Action
    </h2>

    <div class="grid lg:grid-cols-2 gap-8 items-start">
      <!-- Input Document Preview -->
      <div class="space-y-4">
        <h3
          class="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2 dark:text-white"
        >
          <FileText class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          Medical Document
        </h3>
        <div
          class="rounded-lg border border-slate-200 bg-white/80 backdrop-blur-sm p-6 font-mono text-sm text-slate-600 leading-relaxed overflow-hidden relative dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300"
        >
          <!-- Animated highlight effect -->
          <div
            class="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/10 to-transparent -skew-x-12 animate-shimmer"
          ></div>

          <div class="relative z-10">
            <div class="mb-4 text-blue-600 dark:text-blue-400">## Clinical Letter</div>
            <div class="mb-2">
              <span class="text-slate-400 dark:text-slate-500">Patient:</span>
              <span class="highlight-patient">Sarah Lee</span>, DOB:
              <span class="highlight-dob">03/04/1961</span>
            </div>
            <div class="mb-2">
              <span class="text-slate-400 dark:text-slate-500">MRN:</span>
              <span class="highlight-mrn">2123242</span>
            </div>
            <div class="mb-4">
              <span class="text-slate-400 dark:text-slate-500">Date:</span> August 7, 2025
            </div>

            <div class="mb-2 text-slate-500 dark:text-slate-400">
              Dear Dr. General Practitioner,
            </div>

            <div class="mb-4">
              I am writing regarding our patient who was recently diagnosed with a
              <span
                class="highlight-diagnosis bg-yellow-100 text-yellow-800 px-1 rounded dark:bg-yellow-500/20 dark:text-yellow-300"
                >lung embolism</span
              >.
            </div>

            <div class="mb-2 font-semibold">Presenting Symptoms:</div>
            <div class="mb-4 ml-4">
              •
              <span
                class="highlight-symptom bg-blue-100 text-blue-800 px-1 rounded dark:bg-blue-500/20 dark:text-blue-300"
                >Shortness of breath</span
              ><br />
              •
              <span
                class="highlight-symptom bg-blue-100 text-blue-800 px-1 rounded dark:bg-blue-500/20 dark:text-blue-300"
                >Chest pain</span
              ><br />
              • No leg swelling observed
            </div>

            <div class="mb-2 font-semibold">Diagnosis:</div>
            <div class="ml-4">
              <span
                class="highlight-location bg-emerald-100 text-emerald-800 px-1 rounded dark:bg-green-500/20 dark:text-green-300"
                >Pulmonary embolism - bilateral</span
              >
            </div>
          </div>
        </div>
      </div>

      <!-- Extracted JSON Output -->
      <div class="space-y-4">
        <h3
          class="text-xl font-semibold text-slate-900 mb-4 flex items-center gap-2 dark:text-white"
        >
          <span class="text-2xl font-mono text-emerald-600 dark:text-emerald-400">{}</span>
          Extracted Structured Data
        </h3>

        <!-- LLM Extracted Data -->
        <div
          class="rounded-lg border border-slate-200 bg-white/80 backdrop-blur-sm overflow-hidden dark:border-slate-700 dark:bg-slate-900/50"
        >
          <div
            class="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-800/50"
          >
            <div class="flex items-center space-x-2">
              <div class="h-3 w-3 rounded-full bg-red-500"></div>
              <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
              <div class="h-3 w-3 rounded-full bg-green-500"></div>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-emerald-600 font-medium dark:text-emerald-400"
                >LLM Output</span
              >
              <div class="text-sm text-slate-500 dark:text-slate-400">output.json</div>
            </div>
            <button
              class="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded hover:bg-emerald-200 transition-colors dark:bg-emerald-500/20 dark:text-emerald-400 dark:hover:bg-emerald-500/30"
            >
              Copy
            </button>
          </div>
          <div class="p-4 overflow-auto max-h-64">
            <!--
              NOTE: This inline JSON <pre> is intentionally kept instead of using <JsonViewer>.
              The interactive hover-highlight behavior pairs source spans (.highlight-* in the
              document preview) with target spans (.highlight-target-* below) via DOM queries.
              JsonViewer renders a collapsible tree and cannot attach per-value highlight classes
              or reproduce the dark syntax-highlighted flat layout without a risky extension.
              See deviation note in the refactor report.
            -->
            <pre class="font-mono text-xs text-slate-600 dark:text-slate-300"><code>{
  <span class="text-emerald-600 dark:text-emerald-400">"patient"</span>: {
    <span class="text-emerald-600 dark:text-emerald-400">"name"</span>: <span class="text-yellow-700 dark:text-yellow-300 highlight-target-patient">"Sarah Lee"</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"date_of_birth"</span>: <span class="text-yellow-700 dark:text-yellow-300 highlight-target-dob">"1961-04-03"</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"mrn"</span>: <span class="text-yellow-700 dark:text-yellow-300 highlight-target-mrn">"2123242"</span>
  },
  <span class="text-emerald-600 dark:text-emerald-400">"diagnosis"</span>: {
    <span class="text-emerald-600 dark:text-emerald-400">"primary"</span>: <span class="text-yellow-700 dark:text-yellow-300 highlight-target-diagnosis">"Pulmonary embolism"</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"location"</span>: <span class="text-yellow-700 dark:text-yellow-300 highlight-target-location">"bilateral"</span>
  },
  <span class="text-emerald-600 dark:text-emerald-400">"symptoms"</span>: {
    <span class="text-emerald-600 dark:text-emerald-400">"shortness_of_breath"</span>: <span class="text-blue-600 dark:text-blue-300">true</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"chest_pain"</span>: <span class="text-blue-600 dark:text-blue-300">true</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"leg_pain_or_swelling"</span>: <span class="text-blue-600 dark:text-blue-300">false</span>
  }
}</code></pre>
          </div>
        </div>

        <!-- Extraction Metadata -->
        <div class="mt-4 grid grid-cols-2 gap-4">
          <!-- Processing Info Card -->
          <div
            class="rounded-lg bg-slate-50 border border-slate-200 p-4 dark:bg-slate-800/50 dark:border-slate-700"
          >
            <div class="flex items-center gap-2 mb-2">
              <Zap class="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <h4 class="text-sm font-semibold text-slate-900 dark:text-white">
                Processing Details
              </h4>
            </div>
            <div class="space-y-1">
              <div class="flex justify-between items-center">
                <span class="text-xs text-slate-500 dark:text-slate-400">Model</span>
                <span class="text-xs text-blue-600 font-mono dark:text-blue-300">gpt-4o</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-xs text-slate-500 dark:text-slate-400">Processing Time</span>
                <span class="text-xs text-blue-600 font-mono dark:text-blue-300">1.2s</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-xs text-slate-500 dark:text-slate-400">Tokens Used</span>
                <span class="text-xs text-blue-600 font-mono dark:text-blue-300">2,769</span>
              </div>
            </div>
          </div>

          <!-- Accuracy Card -->
          <div
            class="rounded-lg bg-slate-50 border border-slate-200 p-4 dark:bg-slate-800/50 dark:border-slate-700"
          >
            <div class="flex items-center gap-2 mb-2">
              <BarChart3 class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h4 class="text-sm font-semibold text-slate-900 dark:text-white">Accuracy Metrics</h4>
            </div>
            <div class="space-y-2">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-xs text-slate-500 dark:text-slate-400">Overall Accuracy</span>
                  <span class="text-sm font-bold text-emerald-600 dark:text-emerald-400"
                    >92.2%</span
                  >
                </div>
                <div class="w-full bg-slate-200 rounded-full h-1.5 dark:bg-slate-700">
                  <div
                    class="bg-gradient-to-r from-emerald-500 to-teal-500 h-1.5 rounded-full transition-all duration-1000"
                    style="width: 92.2%"
                  ></div>
                </div>
              </div>
              <div class="text-xs text-slate-400 italic dark:text-slate-500">
                Based on 8 documents evaluated
              </div>
            </div>
          </div>
        </div>

        <!-- Visual Flow Indicator -->
        <div
          class="mt-4 flex items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400"
        >
          <FileText class="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span>Document</span>
          <ChevronRight class="w-4 h-4" />
          <Zap class="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span>LLM Processing</span>
          <ChevronRight class="w-4 h-4" />
          <CircleCheckBig class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>Validated Output</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileText, Zap, BarChart3, ChevronRight, CircleCheckBig } from '@lucide/vue'
import { onMounted } from 'vue'

onMounted(() => {
  // Interactive hover effects for demo section
  const highlightPairs: { source: string; target: string }[] = [
    { source: '.highlight-patient', target: '.highlight-target-patient' },
    { source: '.highlight-dob', target: '.highlight-target-dob' },
    { source: '.highlight-mrn', target: '.highlight-target-mrn' },
    { source: '.highlight-diagnosis', target: '.highlight-target-diagnosis' },
    { source: '.highlight-location', target: '.highlight-target-location' },
  ]

  highlightPairs.forEach((pair) => {
    const sourceEl = document.querySelector(pair.source)
    const targetEl = document.querySelector(pair.target)

    if (sourceEl && targetEl) {
      sourceEl.addEventListener('mouseenter', () => {
        sourceEl.classList.add('bg-yellow-200', 'dark:bg-yellow-500/40', 'scale-105')
        targetEl.classList.add('bg-yellow-200', 'dark:bg-yellow-500/40', 'scale-105')
      })

      sourceEl.addEventListener('mouseleave', () => {
        sourceEl.classList.remove('bg-yellow-200', 'dark:bg-yellow-500/40', 'scale-105')
        targetEl.classList.remove('bg-yellow-200', 'dark:bg-yellow-500/40', 'scale-105')
      })
    }
  })
})
</script>

<style scoped>
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
</style>
