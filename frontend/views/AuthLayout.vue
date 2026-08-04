<template>
  <div class="relative min-h-screen flex items-center justify-center bg-surface">
    <!-- Language switcher: top-right corner, outside the centered card -->
    <div class="absolute top-4 right-4">
      <LanguageSwitcher />
    </div>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
</script>
