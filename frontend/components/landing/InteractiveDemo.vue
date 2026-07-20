<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-content">
      {{ $t('landing.demo.heading') }}
    </h2>

    <div class="grid lg:grid-cols-2 gap-8 items-start">
      <!-- Input Document Preview -->
      <div class="space-y-4">
        <h3 class="text-xl font-semibold text-content mb-4 flex items-center gap-2">
          <FileText class="w-6 h-6 text-primary" />
          {{ $t('landing.demo.medical_document') }}
        </h3>
        <div
          class="rounded-card border border-default bg-surface/80 backdrop-blur-sm p-6 font-mono text-sm text-content-muted leading-relaxed overflow-hidden relative"
        >
          <!-- Animated highlight effect -->
          <div
            class="absolute inset-0 bg-gradient-to-r from-transparent via-primary/10 to-transparent -skew-x-12 animate-shimmer"
          ></div>

          <div class="relative z-10">
            <div class="mb-4 text-primary">## Clinical Letter</div>
            <div class="mb-2">
              <span class="text-content-subtle">Patient:</span>
              <span class="highlight-patient">Sarah Lee</span>, DOB:
              <span class="highlight-dob">03/04/1961</span>
            </div>
            <div class="mb-2">
              <span class="text-content-subtle">MRN:</span>
              <span class="highlight-mrn">2123242</span>
            </div>
            <div class="mb-4"><span class="text-content-subtle">Date:</span> August 7, 2025</div>

            <div class="mb-2 text-content-muted">Dear Dr. General Practitioner,</div>

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
              <span class="highlight-symptom bg-primary-soft text-primary px-1 rounded"
                >Shortness of breath</span
              ><br />
              •
              <span class="highlight-symptom bg-primary-soft text-primary px-1 rounded"
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
        <h3 class="text-xl font-semibold text-content mb-4 flex items-center gap-2">
          <span class="text-2xl font-mono text-emerald-600 dark:text-emerald-400">{}</span>
          {{ $t('landing.demo.extracted_data') }}
        </h3>

        <!-- LLM Extracted Data -->
        <div
          class="rounded-card border border-default bg-surface/80 backdrop-blur-sm overflow-hidden"
        >
          <div
            class="flex items-center justify-between border-b border-default bg-surface-muted px-4 py-2"
          >
            <div class="flex items-center space-x-2">
              <div class="h-3 w-3 rounded-full bg-red-500"></div>
              <div class="h-3 w-3 rounded-full bg-yellow-500"></div>
              <div class="h-3 w-3 rounded-full bg-green-500"></div>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-emerald-600 font-medium dark:text-emerald-400">{{
                $t('landing.demo.llm_output')
              }}</span>
              <div class="text-sm text-content-muted">output.json</div>
            </div>
            <button
              type="button"
              :aria-label="$t('landing.demo.copy_aria')"
              class="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded hover:bg-emerald-200 transition-colors dark:bg-emerald-500/20 dark:text-emerald-400 dark:hover:bg-emerald-500/30"
              @click="copyJson"
            >
              {{ copied ? $t('landing.demo.copied') : $t('landing.demo.copy') }}
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
            <pre class="font-mono text-xs text-content-muted"><code ref="jsonCode">{
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
    <span class="text-emerald-600 dark:text-emerald-400">"shortness_of_breath"</span>: <span class="text-primary">true</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"chest_pain"</span>: <span class="text-primary">true</span>,
    <span class="text-emerald-600 dark:text-emerald-400">"leg_pain_or_swelling"</span>: <span class="text-primary">false</span>
  }
}</code></pre>
          </div>
        </div>

        <!-- Extraction Metadata -->
        <div class="mt-4 grid grid-cols-2 gap-4">
          <!-- Processing Info Card -->
          <div class="rounded-card bg-surface-muted border border-default p-4">
            <div class="flex items-center gap-2 mb-2">
              <Zap class="w-5 h-5 text-primary" />
              <h4 class="text-sm font-semibold text-content">
                {{ $t('landing.demo.processing_details') }}
              </h4>
            </div>
            <div class="space-y-1">
              <div class="flex justify-between items-center">
                <span class="text-xs text-content-muted">{{ $t('landing.demo.model') }}</span>
                <span class="text-xs text-primary font-mono">gpt-4o</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-xs text-content-muted">{{
                  $t('landing.demo.processing_time')
                }}</span>
                <span class="text-xs text-primary font-mono">1.2s</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-xs text-content-muted">{{ $t('landing.demo.tokens_used') }}</span>
                <span class="text-xs text-primary font-mono">2,769</span>
              </div>
            </div>
          </div>

          <!-- Accuracy Card -->
          <div class="rounded-card bg-surface-muted border border-default p-4">
            <div class="flex items-center gap-2 mb-2">
              <BarChart3 class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h4 class="text-sm font-semibold text-content">
                {{ $t('landing.demo.accuracy_metrics') }}
              </h4>
            </div>
            <div class="space-y-2">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <span class="text-xs text-content-muted">{{
                    $t('landing.demo.overall_accuracy')
                  }}</span>
                  <span class="text-sm font-bold text-emerald-600 dark:text-emerald-400"
                    >92.2%</span
                  >
                </div>
                <div class="w-full bg-surface-sunken rounded-full h-1.5">
                  <div
                    class="bg-gradient-to-r from-emerald-500 to-teal-500 h-1.5 rounded-full transition-all duration-1000"
                    style="width: 92.2%"
                  ></div>
                </div>
              </div>
              <div class="text-xs text-content-subtle italic">
                {{ $t('landing.demo.based_on_documents') }}
              </div>
            </div>
          </div>
        </div>

        <!-- Disclaimer: the metrics above are demo values, not real results -->
        <p class="mt-2 text-center text-xs text-content-subtle italic">
          {{ $t('landing.demo.disclaimer') }}
        </p>

        <!-- Visual Flow Indicator -->
        <div class="mt-4 flex items-center justify-center gap-2 text-xs text-content-muted">
          <FileText class="w-4 h-4 text-primary" />
          <span>{{ $t('landing.demo.flow_document') }}</span>
          <ChevronRight class="w-4 h-4" />
          <Zap class="w-4 h-4 text-primary" />
          <span>{{ $t('landing.demo.flow_llm_processing') }}</span>
          <ChevronRight class="w-4 h-4" />
          <CircleCheckBig class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>{{ $t('landing.demo.flow_validated_output') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FileText, Zap, BarChart3, ChevronRight, CircleCheckBig } from '@lucide/vue'
import { onMounted, onUnmounted, ref } from 'vue'

const jsonCode = ref<HTMLElement | null>(null)
const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | null = null

async function copyJson(): Promise<void> {
  const text = jsonCode.value?.textContent
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    if (copiedTimer) clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    // Clipboard unavailable (permissions / non-secure context) — ignore.
  }
}

onUnmounted(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})

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
