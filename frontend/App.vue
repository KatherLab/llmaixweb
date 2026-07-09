<template>
  <AppBanner />
  <router-view />
  <ToastContainer />
</template>

<script setup lang="ts">
import AppBanner from '@/components/common/AppBanner.vue'
import ToastContainer from '@/components/common/ToastContainer.vue'
</script>
