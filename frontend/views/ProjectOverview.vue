<!-- src/views/ProjectOverview.vue -->
<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
        <h1 class="text-3xl font-bold text-gray-900">Project Overview</h1>
        <CreateProjectButton />
      </div>
    </header>
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <!-- Project List -->
      <div class="bg-white shadow rounded-lg overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-200">
          <h2 class="text-lg font-medium text-gray-900">Projects</h2>
        </div>
        <div class="p-4">
          <ProjectGrid />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import ProjectGrid from '@/components/ProjectGrid.vue';
import CreateProjectButton from '@/components/CreateProjectButton.vue';
</script>
