<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
    <PageHeader
      title="Admin"
      subtitle="Manage users, system settings, SSO providers, and Celery queues."
      class="mb-6"
    />
    <BaseTabGroup :model-value="route.path" :tabs="tabs" class="mb-6" />
    <router-view />
    <!-- Shows the active tab content -->
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const route = useRoute()

const tabs = computed(() => [
  { label: 'User Management', value: '/admin/user-management', to: '/admin/user-management' },
  { label: 'Settings', value: '/admin/settings', to: '/admin/settings' },
  { label: 'SSO', value: '/admin/sso', to: '/admin/sso' },
  { label: 'Celery & Queues', value: '/admin/celery', to: '/admin/celery' },
])
</script>
