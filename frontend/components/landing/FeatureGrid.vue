<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-content">
      {{ $t('landing.features.heading') }}
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
import { useI18n } from 'vue-i18n'
import { Lock, Code, ClipboardList, BarChart3, LayoutDashboard, Terminal } from '@lucide/vue'
import FeatureCard from '@/components/landing/FeatureCard.vue'

const { t } = useI18n({ useScope: 'global' })

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
    title: t('landing.features.privacy.title'),
    description: t('landing.features.privacy.description'),
    icon: Lock,
    borderHover: 'hover:border-primary',
    shadowHover: 'hover:shadow-lg hover:shadow-primary/10',
    gradientFrom: 'from-primary/5',
    iconBg: 'bg-primary-soft',
    iconText: 'text-primary',
    iconHoverBg: 'group-hover:bg-primary-soft',
  },
  {
    title: t('landing.features.schema.title'),
    description: t('landing.features.schema.description'),
    icon: Code,
    borderHover: 'hover:border-primary',
    shadowHover: 'hover:shadow-lg hover:shadow-primary/10',
    gradientFrom: 'from-primary/5',
    iconBg: 'bg-primary-soft',
    iconText: 'text-primary',
    iconHoverBg: 'group-hover:bg-primary-soft',
  },
  {
    title: t('landing.features.ocr.title'),
    description: t('landing.features.ocr.description'),
    icon: ClipboardList,
    borderHover: 'hover:border-purple-400 dark:hover:border-purple-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-purple-500/10',
    gradientFrom: 'from-purple-500/5',
    iconBg: 'bg-purple-100 dark:bg-purple-500/10',
    iconText: 'text-purple-600 dark:text-purple-400',
    iconHoverBg: 'group-hover:bg-purple-200 dark:group-hover:bg-purple-500/20',
  },
  {
    title: t('landing.features.evaluation.title'),
    description: t('landing.features.evaluation.description'),
    icon: BarChart3,
    borderHover: 'hover:border-emerald-400 dark:hover:border-emerald-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-emerald-500/10',
    gradientFrom: 'from-emerald-500/5',
    iconBg: 'bg-emerald-100 dark:bg-emerald-500/10',
    iconText: 'text-emerald-600 dark:text-emerald-400',
    iconHoverBg: 'group-hover:bg-emerald-200 dark:group-hover:bg-emerald-500/20',
  },
  {
    title: t('landing.features.trials.title'),
    description: t('landing.features.trials.description'),
    icon: LayoutDashboard,
    borderHover: 'hover:border-pink-400 dark:hover:border-pink-500/50',
    shadowHover: 'hover:shadow-lg hover:shadow-pink-500/10',
    gradientFrom: 'from-pink-500/5',
    iconBg: 'bg-pink-100 dark:bg-pink-500/10',
    iconText: 'text-pink-600 dark:text-pink-400',
    iconHoverBg: 'group-hover:bg-pink-200 dark:group-hover:bg-pink-500/20',
  },
  {
    title: t('landing.features.api.title'),
    description: t('landing.features.api.description'),
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
