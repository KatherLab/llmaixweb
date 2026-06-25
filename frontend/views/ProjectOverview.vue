<template>
  <div
    class="h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 flex flex-col"
  >
    <PageHeader title="Project Overview">
      <template #icon>
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="11" stroke="currentColor" stroke-width="2" fill="white" />
          <path
            d="M9 12l2 2 4-4"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </template>
      <template #actions>
        <CreateProjectButton />
      </template>
    </PageHeader>
    <main class="flex-1 max-w-7xl mx-auto w-full px-2 py-2 sm:px-6 min-h-0">
      <div class="h-full flex flex-col gap-4">
        <GlassCard>
          <div class="h-full flex flex-col min-h-0">
            <ProjectGrid />
          </div>
        </GlassCard>
      </div>
    </main>
  </div>
</template>

<script setup>
import ProjectGrid from '@/components/projects/ProjectGrid.vue'
import CreateProjectButton from '@/components/projects/CreateProjectButton.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import GlassCard from '@/components/common/GlassCard.vue'
// Optionally import a SearchBar or FilterControls here in the future
</script>
