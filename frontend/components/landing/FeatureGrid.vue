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
import FeatureCard from '@/components/landing/FeatureCard.vue'

const features = [
  {
    title: 'Privacy-First Design',
    description:
      'Process sensitive medical data locally or with your own hosted LLMs. Full control over your data pipeline.',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
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
    icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
    borderHover: 'hover:border-indigo-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-indigo-500/10',
    gradientFrom: 'from-indigo-500/5',
    iconBg: 'bg-indigo-500/10',
    iconText: 'text-indigo-400',
    iconHoverBg: 'group-hover:bg-indigo-500/20',
  },
  {
    title: 'Advanced OCR Pipeline',
    description:
      'Extract text from any document format using Tesseract, Mistral OCR API, or vision LLM-based OCR.',
    icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
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
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
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
    icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
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
    icon: 'M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    borderHover: 'hover:border-teal-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-teal-500/10',
    gradientFrom: 'from-teal-500/5',
    iconBg: 'bg-teal-500/10',
    iconText: 'text-teal-400',
    iconHoverBg: 'group-hover:bg-teal-500/20',
  },
]
</script>
