<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-slate-900 dark:text-white">
      What you can do here
    </h2>

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

<script setup lang="ts">
import type { Component } from 'vue'
import { Lock, Code, ClipboardList, BarChart3, LayoutDashboard, Terminal } from '@lucide/vue'
import FeatureCard from '@/components/landing/FeatureCard.vue'

interface Feature {
  title: string
  description: string
  icon: Component
  borderHover: string
  shadowHover: string
  gradientFrom: string
  iconBg: string
  iconText: string
  iconHoverBg: string
}

const features: Feature[] = [
  {
    title: 'Privacy-First Design',
    description:
      'Run fully local or with self-hosted LLM and OCR providers. No forced external calls — your data stays in your environment.',
    icon: Lock,
    borderHover: 'hover:border-blue-400 dark:hover:border-blue-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-blue-500/10',
    gradientFrom: 'from-blue-500/5',
    iconBg: 'bg-blue-100 dark:bg-blue-500/10',
    iconText: 'text-blue-600 dark:text-blue-400',
    iconHoverBg: 'group-hover:bg-blue-200 dark:group-hover:bg-blue-500/20',
  },
  {
    title: 'Visual Schema Editor',
    description:
      'Build nested JSON schemas with a tree-based editor — objects, arrays, and all JSON types. No hand-writing JSON.',
    icon: Code,
    borderHover: 'hover:border-blue-400 dark:hover:border-blue-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-blue-500/10',
    gradientFrom: 'from-blue-500/5',
    iconBg: 'bg-blue-100 dark:bg-blue-500/10',
    iconText: 'text-blue-600 dark:text-blue-400',
    iconHoverBg: 'group-hover:bg-blue-200 dark:group-hover:bg-blue-500/20',
  },
  {
    title: 'Four OCR Engines',
    description:
      'Extract text from PDFs, images, or spreadsheets with Docling/Tesseract, Mistral OCR, vision LLMs, or local Docling fallback.',
    icon: ClipboardList,
    borderHover: 'hover:border-purple-400 dark:hover:border-purple-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-purple-500/10',
    gradientFrom: 'from-purple-500/5',
    iconBg: 'bg-purple-100 dark:bg-purple-500/10',
    iconText: 'text-purple-600 dark:text-purple-400',
    iconHoverBg: 'group-hover:bg-purple-200 dark:group-hover:bg-purple-500/20',
  },
  {
    title: 'Accuracy Evaluation',
    description:
      'Compare extracted values to a ground-truth file field by field, with per-field and per-document metrics and confusion matrices.',
    icon: BarChart3,
    borderHover: 'hover:border-emerald-400 dark:hover:border-emerald-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-emerald-500/10',
    gradientFrom: 'from-emerald-500/5',
    iconBg: 'bg-emerald-100 dark:bg-emerald-500/10',
    iconText: 'text-emerald-600 dark:text-emerald-400',
    iconHoverBg: 'group-hover:bg-emerald-200 dark:group-hover:bg-emerald-500/20',
  },
  {
    title: 'Reproducible Trials',
    description:
      'Run extraction across document sets with configurable prompts, schemas, models, temperature, and token limits. Compare runs side by side.',
    icon: LayoutDashboard,
    borderHover: 'hover:border-pink-400 dark:hover:border-pink-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-pink-500/10',
    gradientFrom: 'from-pink-500/5',
    iconBg: 'bg-pink-100 dark:bg-pink-500/10',
    iconText: 'text-pink-600 dark:text-pink-400',
    iconHoverBg: 'group-hover:bg-pink-200 dark:group-hover:bg-pink-500/20',
  },
  {
    title: 'OpenAI-Compatible APIs',
    description:
      'Point trials at any OpenAI-compatible endpoint — OpenAI, Mistral, vLLM, Ollama, or llama.cpp. Mix and match per trial.',
    icon: Terminal,
    borderHover: 'hover:border-teal-400 dark:hover:border-teal-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-teal-500/10',
    gradientFrom: 'from-teal-500/5',
    iconBg: 'bg-teal-100 dark:bg-teal-500/10',
    iconText: 'text-teal-600 dark:text-teal-400',
    iconHoverBg: 'group-hover:bg-teal-200 dark:group-hover:bg-teal-500/20',
  },
]
</script>
