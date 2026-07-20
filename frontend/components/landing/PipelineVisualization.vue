<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-content">
      {{ $t('landing.pipeline.heading') }}
    </h2>

    <!-- Pipeline Container -->
    <div class="relative">
      <!-- Connection Lines (visible on desktop) -->
      <div
        class="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-primary via-primary to-emerald-500 -translate-y-1/2 z-0"
      ></div>

      <!-- Pipeline Steps -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-8 lg:gap-4 relative z-10">
        <PipelineStep
          v-for="step in steps"
          :key="step.id"
          :step="step"
          :active="activeStep === step.id"
          @toggle="activeStep = activeStep === step.id ? null : step.id"
        />
      </div>
    </div>

    <!-- Step Details (Expandable) -->
    <transition name="fade-slide">
      <div v-if="activeStep" class="mt-12 mx-auto max-w-4xl">
        <PipelineStepDetails :step="activeStep" @close="activeStep = null" />
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { UploadCloud, FileText, FolderOpen, Database, Zap, BarChart3 } from '@lucide/vue'
import PipelineStep from '@/components/landing/PipelineStep.vue'
import PipelineStepDetails from '@/components/landing/PipelineStepDetails.vue'

const { t } = useI18n({ useScope: 'global' })

interface Step {
  id: number
  title: string
  subtitle: string
  gradient: string
  shadow: string
  icon: Component
}

const activeStep = ref<number | null>(null)

const steps: Step[] = [
  {
    id: 1,
    title: t('landing.pipeline.steps.upload.title'),
    subtitle: t('landing.pipeline.steps.upload.subtitle'),
    gradient: 'bg-gradient-to-br from-primary to-primary-hover',
    shadow: 'shadow-primary/30',
    icon: UploadCloud,
  },
  {
    id: 2,
    title: t('landing.pipeline.steps.preprocess.title'),
    subtitle: t('landing.pipeline.steps.preprocess.subtitle'),
    gradient: 'bg-gradient-to-br from-primary to-primary-hover',
    shadow: 'shadow-primary/30',
    icon: FileText,
  },
  {
    id: 3,
    title: t('landing.pipeline.steps.documents.title'),
    subtitle: t('landing.pipeline.steps.documents.subtitle'),
    gradient: 'bg-gradient-to-br from-purple-500 to-purple-600',
    shadow: 'shadow-purple-500/30',
    icon: FolderOpen,
  },
  {
    id: 4,
    title: t('landing.pipeline.steps.schemas.title'),
    subtitle: t('landing.pipeline.steps.schemas.subtitle'),
    gradient: 'bg-gradient-to-br from-pink-500 to-pink-600',
    shadow: 'shadow-pink-500/30',
    icon: Database,
  },
  {
    id: 5,
    title: t('landing.pipeline.steps.trials.title'),
    subtitle: t('landing.pipeline.steps.trials.subtitle'),
    gradient: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
    shadow: 'shadow-emerald-500/30',
    icon: Zap,
  },
  {
    id: 6,
    title: t('landing.pipeline.steps.evaluation.title'),
    subtitle: t('landing.pipeline.steps.evaluation.subtitle'),
    gradient: 'bg-gradient-to-br from-teal-500 to-teal-600',
    shadow: 'shadow-teal-500/30',
    icon: BarChart3,
  },
]
</script>

<style scoped>
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
</style>
