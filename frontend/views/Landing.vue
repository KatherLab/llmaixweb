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
          <LanguageSwitcher />
          <router-link
            v-if="!isAuthenticated && registrationOpen"
            to="/login"
            class="text-sm font-medium text-content-muted hover:text-content transition-colors"
          >
            {{ $t('landing.nav.sign_in') }}
          </router-link>
          <BaseButton
            v-if="!isAuthenticated"
            :to="registrationOpen ? '/register' : '/login'"
            size="sm"
          >
            {{ registrationOpen ? $t('landing.nav.get_started') : $t('landing.nav.sign_in') }}
          </BaseButton>
          <BaseButton v-else to="/projects" size="sm">{{ $t('landing.nav.go_to_app') }}</BaseButton>
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
      <LandingCta :registration-open="registrationOpen" />
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
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import { useAuthStore } from '@/stores/auth'
import { usePublicSettingsStore } from '@/stores/publicSettings'

const authStore = useAuthStore()
const publicSettingsStore = usePublicSettingsStore()
const authReady = ref(false)
onMounted(async () => {
  await Promise.all([authStore.initialize(), publicSettingsStore.fetch()])
  authReady.value = true
})
const isAuthenticated = computed(() => authReady.value && authStore.isAuthenticated)
// Default deployments are invitation-only — only advertise "Get started"
// (→ /register) once the backend confirms open registration; otherwise the
// CTAs point to sign-in so visitors never dead-end on a closed register page.
const registrationOpen = computed(() => publicSettingsStore.settings?.require_invitation === false)
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
