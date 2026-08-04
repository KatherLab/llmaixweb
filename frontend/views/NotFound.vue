<!-- views/NotFound.vue -->
<template>
  <div class="min-h-screen flex flex-col items-center justify-center px-4">
    <div
      class="bg-surface border border-default rounded-modal shadow-sm p-10 max-w-md w-full text-center"
    >
      <div class="flex justify-center mb-4">
        <Compass class="w-14 h-14 text-content-subtle" aria-hidden="true" />
      </div>
      <h1 class="text-6xl font-extrabold text-content tracking-tight">404</h1>
      <p class="text-xl text-content mt-4">{{ $t('not_found.title') }}</p>
      <p class="text-content-muted mt-2 mb-8">
        {{ $t('not_found.description') }}
      </p>
      <div class="flex flex-col sm:flex-row gap-3 justify-center">
        <BaseButton variant="primary" size="lg" @click="goProjects">
          <Folder class="h-4 w-4" />
          {{ $t('not_found.go_projects') }}
        </BaseButton>
        <BaseButton variant="secondary" size="lg" @click="goLogin">
          <LogIn class="h-4 w-4" />
          {{ $t('not_found.go_login') }}
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Compass, Folder, LogIn } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'

const router = useRouter()

function goProjects(): void {
  router.push('/projects')
}

function goLogin(): void {
  router.push('/login')
}
</script>
