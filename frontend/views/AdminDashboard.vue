<template>
  <div class="max-w-4xl mx-auto py-10 px-4">
    <h1 class="text-3xl font-bold mb-7 flex items-center gap-3">
      <svg class="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="10" stroke="currentColor" />
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z" />
      </svg>
      Admin Dashboard
    </h1>
    <BaseTabGroup :model-value="route.path" :tabs="tabs" class="mb-6" />
    <router-view />
    <!-- Shows the active tab content -->
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'

const route = useRoute()

const tabs = computed(() => [
  { label: 'Settings', value: '/admin/settings', to: '/admin/settings' },
  { label: 'Celery & Queues', value: '/admin/celery', to: '/admin/celery' },
])
</script>
