<template>
  <div
    class="h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 flex flex-col"
  >
    <!-- Floating Glassy Header -->
    <header class="sticky top-0 z-30 bg-white dark:bg-slate-900 shadow-lg flex-shrink-0">
      <div class="max-w-7xl mx-auto flex justify-between items-center py-2 px-4 sm:px-6">
        <div class="flex items-center gap-2">
          <div
            class="bg-blue-100 dark:bg-slate-800 text-blue-500 dark:text-blue-400 rounded-full p-1.5 shadow"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="11" stroke="currentColor" stroke-width="2" fill="white" />
              <path
                d="M9 12l2 2 4-4"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <h1 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
            Project Overview
          </h1>
        </div>
        <CreateProjectButton />
      </div>
    </header>
    <main class="flex-1 max-w-7xl mx-auto w-full px-2 py-2 sm:px-6 min-h-0">
      <div class="h-full flex flex-col gap-4">
        <section
          class="flex-1 min-h-0 relative bg-white/70 dark:bg-slate-800/70 rounded-xl shadow-lg p-4 sm:p-5 transition-all border border-blue-100 dark:border-slate-700"
          style="backdrop-filter: blur(8px)"
        >
          <div class="h-full flex flex-col min-h-0">
            <ProjectGrid />
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import ProjectGrid from '@/components/ProjectGrid.vue'
import CreateProjectButton from '@/components/CreateProjectButton.vue'
// Optionally import a SearchBar or FilterControls here in the future
</script>
