<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
    <!-- Section eyebrow only — each child view renders its own PageHeader (the
         page's single <h1>), so a full "Admin" PageHeader here would stack a
         second, competing heading. -->
    <p class="text-xs font-semibold uppercase tracking-wide text-content-subtle mb-2">Admin</p>
    <BaseTabGroup :model-value="route.path" :tabs="tabs" class="mb-6" />
    <router-view />
    <!-- Shows the active tab content -->
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'

const route = useRoute()

const tabs = computed(() => [
  { label: 'User Management', value: '/admin/user-management', to: '/admin/user-management' },
  { label: 'Settings', value: '/admin/settings', to: '/admin/settings' },
  { label: 'SSO', value: '/admin/sso', to: '/admin/sso' },
  { label: 'Audit Log', value: '/admin/audit', to: '/admin/audit' },
  { label: 'Celery & Queues', value: '/admin/celery', to: '/admin/celery' },
])
</script>
