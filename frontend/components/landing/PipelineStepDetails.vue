<template>
  <div class="rounded-xl border border-slate-700 bg-slate-900/50 backdrop-blur-sm p-8">
    <!-- Step 1 Details -->
    <div v-if="step === 1" class="space-y-4">
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
              <div class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <span class="text-xs font-bold text-blue-400">DOC</span>
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
            <li v-for="feature in uploadFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Step 2 Details -->
    <div v-if="step === 2" class="space-y-4">
      <h3 class="text-2xl font-bold text-white mb-4">Advanced Text Extraction</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-blue-400 mb-3">OCR Methods</h4>
          <div class="space-y-3">
            <div
              v-for="method in ocrMethods"
              :key="method.name"
              class="p-3 rounded-lg bg-slate-800/50 border border-slate-700"
            >
              <h5 class="font-semibold text-white mb-1">{{ method.name }}</h5>
              <p class="text-sm text-slate-400">{{ method.description }}</p>
            </div>
          </div>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-blue-400 mb-3">Document Parsers</h4>
          <div class="space-y-3">
            <div
              v-for="parser in documentParsers"
              :key="parser.name"
              class="p-3 rounded-lg bg-slate-800/50 border border-slate-700"
            >
              <h5 class="font-semibold text-white mb-1">{{ parser.name }}</h5>
              <p class="text-sm text-slate-400">{{ parser.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3 Details -->
    <div v-if="step === 3" class="space-y-4">
      <h3 class="text-2xl font-bold text-white mb-4">Document Management</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-purple-400 mb-3">Organization Features</h4>
          <ul class="space-y-2 text-slate-300">
            <li v-for="feature in documentFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-purple-400 mb-3">Flexible Selection</h4>
          <p class="text-slate-300 mb-3">Choose documents for trials in two ways:</p>
          <div class="space-y-3">
            <div
              v-for="option in selectionOptions"
              :key="option.name"
              class="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30"
            >
              <h5 class="font-semibold text-white mb-1">{{ option.name }}</h5>
              <p class="text-sm text-slate-400">{{ option.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 4 Details -->
    <div v-if="step === 4" class="space-y-4">
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
                <div
                  v-for="field in schemaTreeFields"
                  :key="field.name"
                  class="flex items-center gap-2"
                >
                  <span class="text-emerald-400">{{ field.name }}</span>
                  <span class="text-slate-500">:</span>
                  <span :class="field.typeClass">{{ field.type }}</span>
                </div>
              </div>
            </div>
          </div>
          <p class="text-sm text-slate-400 mt-3">Create complex nested structures</p>
        </div>
        <div>
          <h4 class="text-lg font-semibold text-pink-400 mb-3">Schema Features</h4>
          <ul class="space-y-2 text-slate-300">
            <li v-for="feature in schemaFeatures" :key="feature" class="flex items-start gap-2">
              <CheckIcon />
              {{ feature }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Step 5 Details -->
    <div v-if="step === 5" class="space-y-4">
      <h3 class="text-2xl font-bold text-white mb-4">LLM-Powered Extraction</h3>
      <div class="space-y-6">
        <!-- Visual Flow -->
        <div class="p-6 rounded-lg bg-slate-800/30 border border-slate-700">
          <div class="flex items-center justify-between gap-4">
            <template v-for="(item, index) in extractionFlow" :key="item.label">
              <div class="text-center">
                <div
                  class="w-16 h-16 mx-auto mb-2 rounded-lg flex items-center justify-center"
                  :class="item.bg"
                >
                  <component
                    :is="item.icon"
                    v-if="item.icon"
                    class="w-8 h-8"
                    :class="item.iconClass"
                  />
                  <span v-else class="text-2xl font-mono" :class="item.iconClass">{}</span>
                </div>
                <p class="text-sm text-slate-400">{{ item.label }}</p>
              </div>
              <div v-if="index < extractionFlow.length - 1" class="flex-1 flex items-center">
                <div class="w-full h-0.5" :class="flowArrows[index].line"></div>
                <ChevronRight class="w-6 h-6 -ml-1" :class="flowArrows[index].arrowClass" />
              </div>
            </template>
          </div>
        </div>

        <div class="grid md:grid-cols-2 gap-6">
          <div>
            <h4 class="text-lg font-semibold text-emerald-400 mb-3">Compatible LLM Providers</h4>
            <div class="space-y-2">
              <div
                v-for="provider in llmProviders"
                :key="provider.name"
                class="p-3 rounded-lg bg-slate-800/50 border border-slate-700"
              >
                <h5 class="font-semibold text-white mb-1">{{ provider.name }}</h5>
                <p class="text-sm text-slate-400">{{ provider.description }}</p>
              </div>
            </div>
          </div>
          <div>
            <h4 class="text-lg font-semibold text-emerald-400 mb-3">Trial Configuration</h4>
            <ul class="space-y-2 text-slate-300">
              <li v-for="feature in trialConfig" :key="feature" class="flex items-start gap-2">
                <CheckIcon />
                {{ feature }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 6 Details -->
    <div v-if="step === 6" class="space-y-4">
      <h3 class="text-2xl font-bold text-white mb-4">Accuracy Evaluation</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-lg font-semibold text-teal-400 mb-3">Evaluation Process</h4>
          <div class="space-y-3">
            <div v-for="item in evaluationProcess" :key="item.step" class="flex items-start gap-3">
              <div
                class="w-8 h-8 rounded-full bg-teal-500/20 flex items-center justify-center flex-shrink-0 mt-0.5"
              >
                <span class="text-sm font-bold text-teal-400">{{ item.step }}</span>
              </div>
              <div>
                <h5 class="font-semibold text-white">{{ item.title }}</h5>
                <p class="text-sm text-slate-400">{{ item.description }}</p>
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
                <div
                  class="bg-gradient-to-r from-teal-500 to-emerald-500 h-2 rounded-full"
                  style="width: 92.2%"
                ></div>
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
      class="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
      @click="$emit('close')"
    >
      <X class="w-6 h-6" />
    </button>
  </div>
</template>

<script setup>
import { FileText, MessageSquare, Database, Zap, ChevronRight, X } from '@lucide/vue'
import CheckIcon from '@/components/landing/CheckIcon.vue'

defineProps({
  step: {
    type: Number,
    default: null,
  },
})

defineEmits(['close'])

// Step 1 data
const uploadFeatures = [
  'Batch upload multiple files',
  'Automatic format detection',
  'Secure local processing',
]

// Step 2 data
const ocrMethods = [
  { name: 'Tesseract OCR', description: 'Industry-standard OCR for printed text' },
  { name: 'Mistral OCR API', description: 'Best for complex layouts and handwritten text' },
  { name: 'Vision LLM-based OCR', description: 'AI-powered extraction via vision language models' },
]

const documentParsers = [{ name: 'Docling', description: "IBM's document understanding library" }]

// Step 3 data
const documentFeatures = [
  'Create document groups for batch processing',
  'Tag and categorize documents',
  'Search and filter by metadata',
  'View extracted text preview',
]

const selectionOptions = [
  { name: 'Document Groups', description: 'Process entire groups at once' },
  { name: 'Individual Selection', description: 'Hand-pick specific documents' },
]

// Step 4 data
const schemaTreeFields = [
  { name: 'patient_id', type: 'string', typeClass: 'text-yellow-400' },
  { name: 'first_name', type: 'string', typeClass: 'text-yellow-400' },
  { name: 'diagnosis', type: 'array', typeClass: 'text-purple-400' },
]

const schemaFeatures = [
  'Support for nested objects and arrays',
  'All JSON data types supported',
  'Import/export JSON schemas',
  'Schema validation and templates',
]

// Step 5 data
const extractionFlow = [
  {
    label: 'Document',
    bg: 'bg-blue-500/20',
    icon: FileText,
    iconClass: 'text-blue-400',
  },
  {
    label: 'Prompt',
    bg: 'bg-blue-500/20',
    icon: MessageSquare,
    iconClass: 'text-blue-400',
  },
  {
    label: 'Schema',
    bg: 'bg-purple-500/20',
    icon: Database,
    iconClass: 'text-purple-400',
  },
  {
    label: 'LLM API',
    bg: 'bg-emerald-500/20',
    icon: Zap,
    iconClass: 'text-emerald-400',
  },
  {
    label: 'JSON Output',
    bg: 'bg-teal-500/20',
    icon: null,
    iconClass: 'text-teal-400',
  },
]

const flowArrows = [
  { line: 'bg-gradient-to-r from-blue-500 to-blue-500', arrowClass: 'text-blue-500' },
  { line: 'bg-gradient-to-r from-blue-500 to-purple-500', arrowClass: 'text-purple-500' },
  { line: 'bg-gradient-to-r from-purple-500 to-emerald-500', arrowClass: 'text-emerald-500' },
  { line: 'bg-gradient-to-r from-emerald-500 to-teal-500', arrowClass: 'text-teal-500' },
]

const llmProviders = [
  { name: 'OpenAI API', description: 'GPT-4, GPT-3.5-turbo' },
  { name: 'Local Models', description: 'Ollama, llama.cpp, vLLM' },
  { name: 'Custom Endpoints', description: 'Any OpenAI-compatible API' },
]

const trialConfig = [
  'Configure temperature for consistency',
  'Run multiple iterations per trial',
  'Compare different prompts & models',
  'Track token usage and costs',
]

// Step 6 data
const evaluationProcess = [
  { step: 1, title: 'Upload Ground Truth', description: 'Provide validated JSON data' },
  { step: 2, title: 'Compare Extractions', description: 'Field-by-field comparison' },
  { step: 3, title: 'Calculate Metrics', description: 'Overall and per-field accuracy' },
]
</script>

<style scoped>
/* Code syntax highlighting colors for schema tree preview */
.text-emerald-400 {
  color: #34d399;
}
.text-yellow-400 {
  color: #fcd34d;
}
.text-blue-400 {
  color: #60a5fa;
}
.text-purple-400 {
  color: #c084fc;
}
.text-orange-400 {
  color: #fb923c;
}
.text-slate-500 {
  color: #64748b;
}
</style>
