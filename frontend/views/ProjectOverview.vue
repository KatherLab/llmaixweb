<template>
  <div class="bg-surface flex flex-col">
    <PageHeader
      title="Projects"
      subtitle="Create and manage your extraction projects."
      class="mb-6"
    >
      <template #icon>
        <CircleCheckBig class="w-5 h-5" aria-hidden="true" />
      </template>
      <template #actions>
        <CreateProjectButton />
      </template>
    </PageHeader>
    <main class="flex-1 max-w-7xl mx-auto w-full px-4 py-4 sm:px-6 min-h-0">
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

<script setup lang="ts">
import { CircleCheckBig } from '@lucide/vue'
import ProjectGrid from '@/components/projects/ProjectGrid.vue'
import CreateProjectButton from '@/components/projects/CreateProjectButton.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import GlassCard from '@/components/common/GlassCard.vue'
// Optionally import a SearchBar or FilterControls here in the future
</script>
