<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-slate-900">
    <!-- Navigation -->
    <nav class="w-full bg-white dark:bg-slate-900 shadow-sm border-b border-gray-100 dark:border-slate-800">
      <div class="w-full px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <div class="flex items-center">
            <div class="flex-shrink-0 flex items-center mr-8">
              <router-link to="/">
                <span class="text-xl font-extrabold tracking-tight text-gray-900 dark:text-white">LLMAIx-v2</span>
              </router-link>
            </div>
            <div v-if="authReady && isAuthenticated" class="flex space-x-1">
              <router-link
                :class="[
                  $route.path === '/projects'
                    ? 'text-blue-600 border-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300 dark:text-slate-400 dark:hover:text-white'
                ]"
                class="inline-flex items-center px-4 h-16 text-base font-medium border-b-2 transition-all"
                to="/projects"
              >
                Projects
              </router-link>
              <router-link
                v-if="isAdmin"
                :class="[
                  $route.path.includes('/admin/user-management')
                    ? 'text-blue-600 border-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300 dark:text-slate-400 dark:hover:text-white'
                ]"
                class="inline-flex items-center px-4 h-16 text-base font-medium border-b-2 transition-all"
                to="/admin/user-management"
              >
                User Management
                <span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-700">
                  Admin
                </span>
              </router-link>
            </div>
          </div>
          <div class="flex items-center">
            <!-- Dark mode toggle -->
            <button
              @click="toggleDarkMode"
              class="mr-3 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 transition-colors focus:outline-none"
              :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
            >
              <svg v-if="!isDark" class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="5" />
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
              </svg>
              <svg v-else class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
              </svg>
            </button>
            <div v-if="authReady && isAuthenticated" class="relative">
              <button
                class="group flex items-center rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                @click="toggleUserMenu"
                aria-label="Open user menu"
              >
                <div
                  class="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-950 flex items-center justify-center shadow-sm border border-blue-200 dark:border-blue-700 group-hover:scale-105 group-hover:shadow-lg group-hover:border-blue-400 dark:group-hover:border-blue-300 transition-all duration-150 relative"
                >
                  <span class="font-semibold text-lg text-blue-800 dark:text-blue-200 select-none">{{ userInitials }}</span>
                  <span
                    v-if="isAdmin"
                    class="absolute -bottom-1 -right-1"
                    title="Admin"
                  >
                    <svg class="w-4 h-4 text-amber-400 drop-shadow" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 2a1 1 0 01.894.553l7 14A1 1 0 0117 18H3a1 1 0 01-.894-1.447l7-14A1 1 0 0110 2zm0 4.618L5.618 16h8.764L10 6.618z" />
                    </svg>
                  </span>
                </div>
                <svg
                  class="ml-2 w-4 h-4 text-blue-400 group-hover:text-blue-600 transition-transform duration-200"
                  :class="{ 'rotate-180': showUserMenu }"
                  fill="none" viewBox="0 0 20 20"
                >
                  <path d="M7 8l3 3 3-3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
              <transition name="fade-slide">
                <div
                  v-if="showUserMenu"
                  class="absolute right-0 mt-3 w-64 rounded-xl shadow-xl bg-white dark:bg-slate-900 ring-1 ring-blue-100 dark:ring-blue-900 z-50 animate-dropdown"
                  @click.away="showUserMenu = false"
                >
                  <div class="px-5 py-3 border-b border-gray-100 dark:border-slate-800">
                    <div class="flex items-center gap-2">
                      <svg v-if="isAdmin" class="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 2a1 1 0 01.894.553l7 14A1 1 0 0117 18H3a1 1 0 01-.894-1.447l7-14A1 1 0 0110 2zm0 4.618L5.618 16h8.764L10 6.618z" />
                      </svg>
                      <span class="font-semibold text-gray-900 dark:text-white">{{ userName }}</span>
                      <span v-if="isAdmin"
                        class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-700">
                        Admin
                      </span>
                    </div>
                    <div class="text-xs text-gray-500 dark:text-slate-400 mt-1 truncate">{{ userEmail }}</div>
                  </div>
                  <a
                    href="#"
                    @click.prevent="logout"
                    class="block px-5 py-3 text-base text-gray-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 font-medium rounded-b-xl transition-colors"
                  >
                    Logout
                  </a>
                </div>
              </transition>
            </div>
            <div v-else-if="authReady">
              <router-link class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-5 rounded-lg shadow-sm transition" to="/login">
                Login
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </nav>
    <div class="flex-1">
      <main class="w-full">
        <router-view v-slot="{ Component }">
          <transition mode="out-in" name="fade">
            <component :is="Component"/>
          </transition>
        </router-view>
      </main>
    </div>
    <footer class="w-full bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 py-4 text-center text-sm text-gray-500 dark:text-slate-400">
      <div>
        &copy; {{ currentYear }} KatherLab. Licensed under
        <a href="https://www.gnu.org/licenses/agpl-3.0.de.html" rel="noopener noreferrer" target="_blank" class="underline hover:text-blue-600 dark:hover:text-blue-300">
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
import { computed, ref, onMounted, watch } from 'vue'
import { frontendVersion } from '@/version.js'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from "@/services/api.js"

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const backendVersion = ref('')
const currentYear = new Date().getFullYear()
const authReady = ref(false)

const isDark = ref(false)

function setDarkClass(val) {
  if (val) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  isDark.value = val
  localStorage.setItem('darkMode', val ? '1' : '0')
}

function toggleDarkMode() {
  setDarkClass(!isDark.value)
}

onMounted(async () => {
  // Fetch backend version
  try {
    const response = await api.get('/version')
    backendVersion.value = response.data.version
  } catch (error) {
    console.error('Error fetching backend version:', error)
  }
  // Wait for authStore initialization
  await authStore.initialize()
  authReady.value = true

  // Set dark mode on mount (from localStorage or system preference)
  const saved = localStorage.getItem('darkMode')
  if (saved === '1' || (saved === null && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    setDarkClass(true)
  } else {
    setDarkClass(false)
  }
})

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isAdmin = computed(() => authStore.isAdmin)
const userName = computed(() => authStore.user?.full_name || '')
const userInitials = computed(() => {
  if (!authStore.user?.full_name) return ''
  return authStore.user.full_name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
})
const userEmail = computed(() => authStore.user?.email || '')

async function logout() {
  await authStore.logout()
  showUserMenu.value = false
  router.push('/login')
}

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

// Hide user menu on route change
watch(() => router.currentRoute.value.fullPath, () => {
  showUserMenu.value = false
})
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
.fade-slide-enter-active, .fade-slide-leave-active {
  transition: opacity 0.18s, transform 0.15s;
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}
.animate-dropdown {
  animation: dropdown-pop 0.22s cubic-bezier(.21,.6,.43,1.07);
}
@keyframes dropdown-pop {
  0% { opacity:0; transform: translateY(-12px) scale(.97);}
  100% { opacity:1; transform: translateY(0) scale(1);}
}
</style>
