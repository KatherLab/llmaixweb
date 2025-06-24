<!-- src/App.vue -->
<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation - Only shown when authenticated -->
    <nav v-if="authStore.isAuthenticated" class="w-full bg-white shadow-sm">
      <div class="w-full px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <!-- Logo/Home -->
            <div class="flex-shrink-0 flex items-center mr-8">
              <span class="text-xl font-bold text-gray-900">LLMAIx-v2</span>
            </div>

            <!-- Navigation Links -->
            <div class="hidden sm:flex sm:space-x-0">
              <!-- Admin Navigation -->
              <template v-if="authStore.isAdmin">
                <router-link
                  to="/admin/user-management"
                  class="inline-flex items-center px-4 h-16 text-sm font-medium border-b-2"
                  :class="[$route.path.includes('/admin/user-management')
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300']"
                >
                  User Management
                </router-link>
              </template>

              <!-- All User Navigation -->
              <template>
                <router-link
                  to="/landing"
                  class="inline-flex items-center px-4 h-16 text-sm font-medium border-b-2"
                  :class="[$route.path === '/landing'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300']"
                >
                  LLMAIx-v2
                </router-link>
                <router-link
                  to="/preprocessing"
                  class="inline-flex items-center px-4 h-16 text-sm font-medium border-b-2"
                  :class="[$route.path === '/preprocessing'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300']"
                >
                  Preprocessing
                </router-link>
                <router-link
                  to="/information-extraction"
                  class="inline-flex items-center px-4 h-16 text-sm font-medium border-b-2"
                  :class="[$route.path === '/information-extraction'
                    ? 'text-blue-600 border-blue-600'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300']"
                >
                  Information Extraction
                </router-link>
              </template>
            </div>
          </div>

          <!-- User Menu -->
          <div class="flex items-center">
            <div class="relative">
              <button
                @click="showUserMenu = !showUserMenu"
                class="flex items-center space-x-3 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <span class="sr-only">Open user menu</span>
                <div class="h-9 w-9 rounded-full bg-blue-100 flex items-center justify-center">
                  <span class="font-medium text-blue-800">{{ userInitials }}</span>
                </div>
              </button>

              <!-- Dropdown -->
              <div
                v-if="showUserMenu"
                class="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 z-50"
              >
                <div class="px-4 py-2 text-sm text-gray-900 border-b">
                  {{ authStore.user?.full_name }}
                </div>
                <a
                  href="#"
                  @click.prevent="logout"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Logout
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="w-full">
      <div v-if="isLoading" class="fixed inset-0 bg-white bg-opacity-75 z-50 flex items-center justify-center">
        <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      </div>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const isLoading = ref(false)

onMounted(async () => {
  console.log("App.vue mounted");
  try {
    await authStore.initialize();
    const currentPath = router.currentRoute.value.path;

    if (authStore.isAuthenticated && ['/', '/login'].includes(currentPath)) {
      await router.push(authStore.isAdmin ? '/landing' : '/landing');
    }
  } catch (error) {
    console.error("Mount error:", error);
    await authStore.logout();
    router.push('/login');
  }
});

const userInitials = computed(() => {
  if (!authStore.user?.full_name) return ''
  return authStore.user.full_name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
})

async function logout() {
  await authStore.logout()
  showUserMenu.value = false
  router.push('/login')
}

watch(() => authStore.token, (newToken, oldToken) => {
  // console.log("Token changed from:", oldToken, "to:", newToken);
  if (newToken) {
    // console.log("Attempting to fetch user due to token change");
    authStore.fetchUser().catch(error => {
      console.error("Error fetching user on token change:", error);
    });
  }
});
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>