<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100">
    <!-- Floating Glassy Header -->
    <header class="sticky top-0 z-20 bg-white/70 backdrop-blur-lg shadow-lg">
      <div class="max-w-7xl mx-auto flex justify-between items-center py-6 px-4 sm:px-8">
        <h1 class="text-3xl sm:text-4xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2">
          <svg class="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="11" stroke="currentColor" stroke-width="2" fill="white"/>
            <path d="M8 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Project Overview
        </h1>
        <CreateProjectButton />
      </div>
    </header>
    <main class="max-w-7xl mx-auto px-4 py-10 sm:px-8">
      <div class="w-full mx-auto">
        <div class="mb-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 class="text-2xl font-semibold text-gray-900 tracking-tight">Your Projects</h2>
          <!-- (Optional) Room for filter/search etc -->
          <!-- <div>
            <SearchBar />
          </div> -->
        </div>
        <section
          class="relative bg-white/70 rounded-3xl shadow-2xl p-8 sm:p-10 mb-12 transition-all border border-blue-100"
          style="backdrop-filter: blur(8px);"
        >
          <ProjectGrid />
          <!-- If you want a fade-in animation, you can wrap ProjectGrid with <transition> here -->
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import ProjectGrid from '@/components/ProjectGrid.vue';
import CreateProjectButton from '@/components/CreateProjectButton.vue';
// Optionally import a SearchBar or FilterControls here in the future
</script>
