<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-white">Built for Medical Research</h2>

    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <FeatureCard
        v-for="(feature, index) in features"
        :key="feature.title"
        :feature="feature"
        :index="index"
      />
    </div>
  </div>
</template>

<script setup>
import { Lock, Code, ClipboardList, BarChart3, LayoutDashboard, Terminal } from '@lucide/vue'
import FeatureCard from '@/components/landing/FeatureCard.vue'

const features = [
  {
    title: 'Privacy-First Design',
    description:
      'Process sensitive medical data locally or with your own hosted LLMs. Full control over your data pipeline.',
    icon: Lock,
    borderHover: 'hover:border-blue-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-blue-500/10',
    gradientFrom: 'from-blue-500/5',
    iconBg: 'bg-blue-500/10',
    iconText: 'text-blue-400',
    iconHoverBg: 'group-hover:bg-blue-500/20',
  },
  {
    title: 'Visual Schema Editor',
    description:
      'Create complex nested JSON schemas with our intuitive tree-based editor. No coding required.',
    icon: Code,
    borderHover: 'hover:border-blue-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-blue-500/10',
    gradientFrom: 'from-blue-500/5',
    iconBg: 'bg-blue-500/10',
    iconText: 'text-blue-400',
    iconHoverBg: 'group-hover:bg-blue-500/20',
  },
  {
    title: 'Advanced OCR Pipeline',
    description:
      'Extract text from any document format using Tesseract, Mistral OCR API, or vision LLM-based OCR.',
    icon: ClipboardList,
    borderHover: 'hover:border-purple-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-purple-500/10',
    gradientFrom: 'from-purple-500/5',
    iconBg: 'bg-purple-500/10',
    iconText: 'text-purple-400',
    iconHoverBg: 'group-hover:bg-purple-500/20',
  },
  {
    title: 'Accuracy Evaluation',
    description:
      'Compare extracted data against ground truth and calculate accuracy metrics for validation.',
    icon: BarChart3,
    borderHover: 'hover:border-emerald-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-emerald-500/10',
    gradientFrom: 'from-emerald-500/5',
    iconBg: 'bg-emerald-500/10',
    iconText: 'text-emerald-400',
    iconHoverBg: 'group-hover:bg-emerald-500/20',
  },
  {
    title: 'Flexible Trials',
    description:
      'Run multiple extraction trials with different prompts, schemas, and temperature settings.',
    icon: LayoutDashboard,
    borderHover: 'hover:border-pink-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-pink-500/10',
    gradientFrom: 'from-pink-500/5',
    iconBg: 'bg-pink-500/10',
    iconText: 'text-pink-400',
    iconHoverBg: 'group-hover:bg-pink-500/20',
  },
  {
    title: 'OpenAI-Compatible APIs',
    description:
      'Use any LLM that supports the OpenAI API format, including local models via Ollama, vLLM, or llama.cpp.',
    icon: Terminal,
    borderHover: 'hover:border-teal-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-teal-500/10',
    gradientFrom: 'from-teal-500/5',
    iconBg: 'bg-teal-500/10',
    iconText: 'text-teal-400',
    iconHoverBg: 'group-hover:bg-teal-500/20',
  },
]
</script>
