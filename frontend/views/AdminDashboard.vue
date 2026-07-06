<template>
  <div class="max-w-4xl mx-auto py-10 px-4">
    <h1 class="text-3xl font-bold mb-7 flex items-center gap-3 text-content">
      <CircleDot class="w-7 h-7 text-blue-600 dark:text-blue-400" aria-hidden="true" />
      Admin Dashboard
    </h1>
    <BaseTabGroup :model-value="route.path" :tabs="tabs" class="mb-6" />
    <router-view />
    <!-- Shows the active tab content -->
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { CircleDot } from '@lucide/vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'

const route = useRoute()

const tabs = computed(() => [
  { label: 'Settings', value: '/admin/settings', to: '/admin/settings' },
  { label: 'SSO', value: '/admin/sso', to: '/admin/sso' },
  { label: 'Celery & Queues', value: '/admin/celery', to: '/admin/celery' },
])
</script>
