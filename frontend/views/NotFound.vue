<!-- views/NotFound.vue -->
<template>
  <div class="min-h-screen flex flex-col items-center justify-center text-center px-4">
    <h1 class="text-6xl font-bold text-gray-800">404</h1>
    <p class="text-xl text-gray-600 mt-4">Page Not Found</p>
    <p class="text-gray-500 mt-2 mb-8">The page you are looking for doesn't exist or has been moved.</p>
    <router-link to="/" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
      Go Home
    </router-link>
  </div>
</template>
