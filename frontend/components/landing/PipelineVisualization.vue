<template>
  <div class="mb-24">
    <h2 class="text-center text-3xl font-bold mb-12 text-white">How It Works</h2>

    <!-- Pipeline Container -->
    <div class="relative">
      <!-- Connection Lines (visible on desktop) -->
      <div
        class="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 -translate-y-1/2 z-0"
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

<script setup>
import { ref } from 'vue'
import PipelineStep from '@/components/landing/PipelineStep.vue'
import PipelineStepDetails from '@/components/landing/PipelineStepDetails.vue'

const activeStep = ref(null)

const steps = [
  {
    id: 1,
    title: 'Upload Files',
    subtitle: 'Multiple formats supported',
    gradient: 'bg-gradient-to-br from-blue-500 to-blue-600',
    shadow: 'shadow-blue-500/30',
    icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
  },
  {
    id: 2,
    title: 'Preprocess',
    subtitle: 'Extract & OCR text',
    gradient: 'bg-gradient-to-br from-indigo-500 to-indigo-600',
    shadow: 'shadow-indigo-500/30',
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
  {
    id: 3,
    title: 'Documents',
    subtitle: 'Organize & group',
    gradient: 'bg-gradient-to-br from-purple-500 to-purple-600',
    shadow: 'shadow-purple-500/30',
    icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-2 0V5a2 2 0 00-2-2H7a2 2 0 00-2 2v2m14 0H5',
  },
  {
    id: 4,
    title: 'Schemas',
    subtitle: 'Define structure',
    gradient: 'bg-gradient-to-br from-pink-500 to-pink-600',
    shadow: 'shadow-pink-500/30',
    icon: 'M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4',
  },
  {
    id: 5,
    title: 'Run Trials',
    subtitle: 'LLM extraction',
    gradient: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
    shadow: 'shadow-emerald-500/30',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z',
  },
  {
    id: 6,
    title: 'Evaluation',
    subtitle: 'Accuracy metrics',
    gradient: 'bg-gradient-to-br from-teal-500 to-teal-600',
    shadow: 'shadow-teal-500/30',
    icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h8l4 4v12a2 2 0 01-2 2z',
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
