<template>
  <div class="max-w-4xl mx-auto py-10 px-4">
    <h1 class="text-3xl font-bold mb-7 flex items-center gap-3">
      <svg class="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke="currentColor" />
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z"/>
      </svg>
      Admin Dashboard
    </h1>
    <div class="flex gap-2 mb-6 border-b border-gray-100 dark:border-slate-800">
      <router-link
        to="/admin/settings"
        class="px-4 py-2 text-base rounded-t-lg bg-gray-50 dark:bg-slate-900 border border-b-0 border-gray-100 dark:border-slate-800 font-medium hover:bg-blue-50 dark:hover:bg-blue-950 transition-all"
        :class="{
          'bg-white dark:bg-slate-900 border-blue-400 dark:border-blue-500 text-blue-700 dark:text-blue-300':
            $route.path === '/admin/settings'
        }"
      >
        Settings
      </router-link>
      <router-link
        to="/admin/celery"
        class="px-4 py-2 text-base rounded-t-lg bg-gray-50 dark:bg-slate-900 border border-b-0 border-gray-100 dark:border-slate-800 font-medium hover:bg-blue-50 dark:hover:bg-blue-950 transition-all"
        :class="{
          'bg-white dark:bg-slate-900 border-blue-400 dark:border-blue-500 text-blue-700 dark:text-blue-300':
            $route.path === '/admin/celery'
        }"
      >
        Celery & Queues
      </router-link>
      <!-- Add more tabs here! -->
    </div>
    <router-view /> <!-- Shows the active tab content -->
  </div>
</template>
