<!-- src/App.vue -->
<template>
  <div class="min-h-screen flex flex-col bg-gray-50">
    <!-- Navigation -->
    <nav class="w-full bg-white shadow-sm">
      <div class="w-full px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <!-- Logo/Home -->
            <div class="flex-shrink-0 flex items-center mr-8">
              <router-link to="/">
                <span class="text-xl font-bold text-gray-900">LLMAIx-v2</span>
              </router-link>
            </div>
            <!-- Navigation Links - Only shown when authenticated -->
            <div v-if="authStore.isAuthenticated" class="hidden sm:flex sm:space-x-0">
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
          <!-- User Menu or Login Button -->
          <div class="flex items-center">
            <div v-if="authStore.isAuthenticated" class="relative">
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
            <div v-else>
              <router-link to="/login" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                Login
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </nav>
    <!-- Main Content -->
    <div class="flex-1">
      <main class="w-full">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <!-- Footer -->
    <footer class="w-full bg-white border-t border-gray-200 py-4 text-center text-sm text-gray-500">
      <div>
        &copy; {{ new Date().getFullYear() }} KatherLab. Licensed under
        <a href="https://www.gnu.org/licenses/agpl-3.0.de.html" target="_blank" rel="noopener noreferrer">
          AGPL-3.0
        </a>
      </div>
      <div>
        Frontend Version: {{ frontendVersion }} | Backend Version: {{ backendVersion }}
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { frontendVersion} from '@/version.js'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from "@/services/api.js";

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const isLoading = ref(false)
const backendVersion = ref('');

onMounted(async () => {
  try {
    const response = await api.get('/version');
    backendVersion.value = response.data.version;
  } catch (error) {
    console.error('Error fetching backend version:', error);
  }
});

onMounted(async () => {
  console.log("App.vue mounted");
  try {
    await authStore.initialize();
    const currentPath = router.currentRoute.value.path;

    if (authStore.isAuthenticated && ['/', '/login'].includes(currentPath)) {
      await router.push(authStore.isAdmin ? '/' : '/');
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