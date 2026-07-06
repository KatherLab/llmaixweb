<!-- Landing.vue -->
<template>
  <div class="landing-root relative min-h-screen overflow-hidden bg-surface-muted text-content">
    <!-- Animated background elements -->
    <LandingBackground />

    <!-- Main content -->
    <div class="relative z-10 mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <!-- Hero Section -->
      <LandingHero />

      <!-- Interactive Pipeline Visualization -->
      <PipelineVisualization />

      <!-- Interactive Demo Section -->
      <InteractiveDemo />

      <!-- Key Features Grid -->
      <FeatureGrid />

      <!-- CTA Section -->
      <LandingCta />
    </div>
  </div>
</template>

<script setup lang="ts">
import LandingBackground from '@/components/landing/LandingBackground.vue'
import LandingHero from '@/components/landing/LandingHero.vue'
import PipelineVisualization from '@/components/landing/PipelineVisualization.vue'
import InteractiveDemo from '@/components/landing/InteractiveDemo.vue'
import FeatureGrid from '@/components/landing/FeatureGrid.vue'
import LandingCta from '@/components/landing/LandingCta.vue'
</script>

<style scoped>
/* Universal smooth transitions — applied to all descendants to match original behavior */
.landing-root,
.landing-root :deep(*) {
  transition-property: transform, opacity, background-color, border-color, box-shadow;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}
</style>
