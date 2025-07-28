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
                    $route.path.startsWith('/projects')
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
                <span
                    class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-700">
                  Admin
                </span>
              </router-link>
            </div>
          </div>

          <div v-if="isAdmin" class="ml-4 relative">
            <button
              aria-label="Admin menu"
              @click="showAdminMenu = !showAdminMenu"
              class="rounded-full p-2 hover:bg-blue-50 dark:hover:bg-slate-800 transition"
            >
              <svg class="w-6 h-6 text-blue-600 dark:text-blue-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7zm7-3.5c0-.8.7-1.4 1.5-1.4s1.5.6 1.5 1.4-.7 1.4-1.5 1.4-1.5-.6-1.5-1.4zm-14 0c0-.8.7-1.4 1.5-1.4S8 11.2 8 12s-.7 1.4-1.5 1.4S5 12.8 5 12z" />
                <circle cx="12" cy="12" r="10" stroke="currentColor"/>
              </svg>
            </button>
            <transition name="fade-slide">
              <div v-if="showAdminMenu"
                class="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 border border-blue-100 dark:border-slate-800 rounded-xl shadow-xl z-50"
                @click.away="showAdminMenu = false"
              >
                <router-link to="/admin/settings" class="block px-5 py-3 text-gray-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950">Settings</router-link>
                <router-link to="/admin/celery" class="block px-5 py-3 text-gray-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950">Celery & Queues</router-link>
                <!-- Add more as needed -->
              </div>
            </transition>
          </div>

          <div class="flex items-center">
            <!-- Dark mode toggle -->
            <button
                :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
                class="mr-3 p-2 rounded-full hover:bg-gray-200 dark:hover:bg-slate-800 transition-colors focus:outline-none"
                @click="toggleDarkMode"
            >
              <svg v-if="!isDark" class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" stroke-width="2"
                   viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="5"/>
                <path
                    d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
              </svg>
              <svg v-else class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" stroke-width="2"
                   viewBox="0 0 24 24">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
              </svg>
            </button>
            <div v-if="authReady && isAuthenticated" class="relative">
              <button
                  aria-label="Open user menu"
                  class="group flex items-center rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  @click="toggleUserMenu"
              >
                <div
                    class="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-950 flex items-center justify-center shadow-sm border border-blue-200 dark:border-blue-700 group-hover:scale-105 group-hover:shadow-lg group-hover:border-blue-400 dark:group-hover:border-blue-300 transition-all duration-150 relative"
                >
                  <span class="font-semibold text-lg text-blue-800 dark:text-blue-200 select-none">{{
                      userInitials
                    }}</span>
                  <span
                      v-if="isAdmin"
                      class="absolute -bottom-1 -right-1"
                      title="Admin"
                  >
                    <svg class="w-4 h-4 text-amber-400 drop-shadow" fill="currentColor" viewBox="0 0 20 20">
                      <path
                          d="M10 2a1 1 0 01.894.553l7 14A1 1 0 0117 18H3a1 1 0 01-.894-1.447l7-14A1 1 0 0110 2zm0 4.618L5.618 16h8.764L10 6.618z"/>
                    </svg>
                  </span>
                </div>
                <svg
                    :class="{ 'rotate-180': showUserMenu }"
                    class="ml-2 w-4 h-4 text-blue-400 group-hover:text-blue-600 transition-transform duration-200"
                    fill="none" viewBox="0 0 20 20"
                >
                  <path d="M7 8l3 3 3-3" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
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
                        <path
                            d="M10 2a1 1 0 01.894.553l7 14A1 1 0 0117 18H3a1 1 0 01-.894-1.447l7-14A1 1 0 0110 2zm0 4.618L5.618 16h8.764L10 6.618z"/>
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
                      class="block px-5 py-3 text-base text-gray-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors"
                      href="#"
                      @click.prevent="openChangePasswordModal"
                  >
                    <svg class="inline-block w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor"
                         stroke-width="2" viewBox="0 0 24 24">
                      <path
                          d="M12 17v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9 9h6a2 2 0 012 2v3a2 2 0 01-2 2H9a2 2 0 01-2-2v-3a2 2 0 012-2v-1a3 3 0 116 0v1"></path>
                    </svg>
                    Change Password
                  </a>
                  <a
                      class="block px-5 py-3 text-base text-gray-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 font-medium rounded-b-xl transition-colors"
                      href="#"
                      @click.prevent="logout"
                  >
                    Logout
                  </a>
                </div>
              </transition>
            </div>
            <div v-else-if="authReady">
              <router-link
                  class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-5 rounded-lg shadow-sm transition"
                  to="/login">
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
    <footer
        class="w-full bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 py-4 text-center text-sm text-gray-500 dark:text-slate-400">
      <div>
        &copy; {{ currentYear }} KatherLab. Licensed under
        <a class="underline hover:text-blue-600 dark:hover:text-blue-300" href="https://www.gnu.org/licenses/agpl-3.0.de.html" rel="noopener noreferrer"
           target="_blank">
          AGPL-3.0
        </a>
      </div>
      <div>
        Frontend Version: {{ frontendVersion }} | Backend Version: {{ backendVersion }}
      </div>
    </footer>
    <!-- Change Password Modal -->
    <transition name="fade-slide">
      <div
          v-if="showChangePasswordModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/60 backdrop-blur-sm"
          @keydown.esc="closeChangePasswordModal"
      >
        <div
            class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-md mx-auto p-8 border border-gray-100 dark:border-slate-800 relative animate-dropdown"
            @click.stop
        >
          <button aria-label="Close"
                  class="absolute top-4 right-4 text-gray-400 hover:text-gray-700 dark:hover:text-gray-100 transition-colors focus:outline-none"
                  @click="closeChangePasswordModal">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <h2 class="text-xl font-bold mb-4 text-gray-900 dark:text-white">Change Password</h2>
          <form class="flex flex-col gap-5" @submit.prevent="handleChangePassword">
            <div>
              <label class="block text-sm font-semibold mb-1 text-gray-700 dark:text-slate-200">Current Password</label>
              <input
                  v-model="currentPassword"
                  autocomplete="current-password"
                  class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
                  placeholder="Enter current password"
                  required
                  type="password"
              />
            </div>
            <div>
              <label class="block text-sm font-semibold mb-1 text-gray-700 dark:text-slate-200">New Password</label>
              <input
                  v-model="newPassword"
                  autocomplete="new-password"
                  class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
                  maxlength="128"
                  minlength="8"
                  placeholder="New password (8–128 chars)"
                  required
                  type="password"
              />
            </div>
            <div>
              <label class="block text-sm font-semibold mb-1 text-gray-700 dark:text-slate-200">Confirm New
                Password</label>
              <input
                  v-model="confirmPassword"
                  autocomplete="new-password"
                  class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800 text-gray-900 dark:text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
                  maxlength="128"
                  minlength="8"
                  placeholder="Repeat new password"
                  required
                  type="password"
              />
            </div>
            <div v-if="passwordError"
                 class="text-red-600 dark:text-red-400 text-sm rounded bg-red-50 dark:bg-red-900/30 px-3 py-2">
              {{ passwordError }}
            </div>
            <div v-if="passwordSuccess"
                 class="text-green-600 dark:text-green-400 text-sm rounded bg-green-50 dark:bg-green-900/30 px-3 py-2">
              {{ passwordSuccess }}
            </div>
            <button
                :disabled="isChangingPassword"
                class="mt-2 w-full py-2.5 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                type="submit"
            >
              <svg v-if="isChangingPassword" class="animate-spin h-5 w-5 mr-2" fill="none"
                   viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      fill="currentColor"/>
              </svg>
              <span>{{ isChangingPassword ? 'Updating...' : 'Update Password' }}</span>
            </button>
          </form>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {frontendVersion} from '@/version.js'
import {useRouter} from 'vue-router'
import {useAuthStore} from '@/stores/auth'
import {api} from "@/services/api.js"
import {useToast} from 'vue-toastification'

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const backendVersion = ref('')
const currentYear = new Date().getFullYear()
const authReady = ref(false)
const toast = useToast()

const showAdminMenu = ref(false)
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

// -----------------------
// Change Password Modal
// -----------------------
const showChangePasswordModal = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
const isChangingPassword = ref(false)

const isPasswordValid = computed(() =>
    newPassword.value.length >= 8 && newPassword.value.length <= 128
)
const doPasswordsMatch = computed(() =>
    newPassword.value === confirmPassword.value
)

function openChangePasswordModal() {
  passwordError.value = ''
  passwordSuccess.value = ''
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showChangePasswordModal.value = true
}

function closeChangePasswordModal() {
  showChangePasswordModal.value = false
}

async function handleChangePassword() {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (!currentPassword.value || !newPassword.value) {
    passwordError.value = 'Please fill in all fields.'
    return
  }
  if (!isPasswordValid.value) {
    passwordError.value = 'Password must be 8–128 characters.'
    return
  }
  if (!doPasswordsMatch.value) {
    passwordError.value = "Passwords don't match."
    return
  }
  isChangingPassword.value = true
  try {
    await api.post('/user/change-password', {
      old_password: currentPassword.value,
      new_password: newPassword.value
    })
    passwordSuccess.value = 'Password updated successfully!'
    toast.success('Your password has been updated.')
    setTimeout(() => {
      closeChangePasswordModal()
    }, 1100)
  } catch (err) {
    passwordError.value = err?.response?.data?.detail || 'Password change failed.'
    toast.error(passwordError.value)
  } finally {
    isChangingPassword.value = false
  }
}
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
  animation: dropdown-pop 0.22s cubic-bezier(.21, .6, .43, 1.07);
}

@keyframes dropdown-pop {
  0% {
    opacity: 0;
    transform: translateY(-12px) scale(.97);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
