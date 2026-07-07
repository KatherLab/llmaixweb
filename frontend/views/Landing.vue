<!-- Landing.vue -->
<template>
  <div class="landing-root relative min-h-screen overflow-hidden bg-surface-muted text-content">
    <!-- Animated background elements -->
    <LandingBackground />

    <!-- Minimal top bar (landing has its own clean header, no app navbar) -->
    <header
      class="relative z-20 sticky top-0 bg-surface/80 backdrop-blur-md border-b border-default"
    >
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex h-14 items-center justify-between">
        <AppBrand />
        <div class="flex items-center gap-3">
          <router-link
            v-if="!isAuthenticated"
            to="/login"
            class="text-sm font-medium text-content-muted hover:text-content transition-colors"
          >
            Sign in
          </router-link>
          <BaseButton v-if="!isAuthenticated" to="/register" size="sm">Get started</BaseButton>
          <BaseButton v-else to="/projects" size="sm">Go to app</BaseButton>
        </div>
      </div>
    </header>

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
import { computed, onMounted, ref } from 'vue'
import LandingBackground from '@/components/landing/LandingBackground.vue'
import LandingHero from '@/components/landing/LandingHero.vue'
import PipelineVisualization from '@/components/landing/PipelineVisualization.vue'
import InteractiveDemo from '@/components/landing/InteractiveDemo.vue'
import FeatureGrid from '@/components/landing/FeatureGrid.vue'
import LandingCta from '@/components/landing/LandingCta.vue'
import AppBrand from '@/components/common/AppBrand.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const authReady = ref(false)
onMounted(async () => {
  await authStore.initialize()
  authReady.value = true
})
const isAuthenticated = computed(() => authReady.value && authStore.isAuthenticated)
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
