<template>
  <div class="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-900">
    <!-- Navigation -->
    <nav
      class="w-full bg-white dark:bg-slate-900 shadow-sm border-b border-slate-100 dark:border-slate-800"
    >
      <div
        v-if="isBackendDown"
        class="bg-red-600 text-white text-center py-1.5 text-xs font-medium animate-pulse"
      >
        Backend connection failed. Please check if the backend server is running.
      </div>
      <div class="w-full px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-14 items-center">
          <div class="flex items-center">
            <div class="flex-shrink-0 flex items-center mr-8">
              <router-link to="/">
                <span class="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white"
                  >LLMAIx-v2</span
                >
              </router-link>
            </div>
            <div v-if="authReady && isAuthenticated" class="flex space-x-1">
              <router-link
                :class="[
                  $route.path.startsWith('/projects')
                    ? 'text-blue-600 border-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300 dark:text-slate-400 dark:hover:text-white',
                ]"
                class="inline-flex items-center px-4 h-14 text-sm font-medium border-b-2 transition-all"
                to="/projects"
              >
                Projects
              </router-link>

              <router-link
                v-if="isAdmin"
                :class="[
                  $route.path.includes('/admin/user-management')
                    ? 'text-blue-600 border-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'text-slate-500 border-transparent hover:text-slate-700 hover:border-slate-300 dark:text-slate-400 dark:hover:text-white',
                ]"
                class="inline-flex items-center px-4 h-14 text-sm font-medium border-b-2 transition-all"
                to="/admin/user-management"
              >
                User Management
                <span
                  class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-700"
                >
                  Admin
                </span>
              </router-link>
            </div>
          </div>

          <div class="flex items-center gap-1">
            <!-- Admin Settings (visible to admins only) -->
            <div v-if="isAdmin" class="relative">
              <button
                aria-label="Admin menu"
                class="rounded-full p-2 hover:bg-blue-50 dark:hover:bg-slate-800 transition"
                @click="showAdminMenu = !showAdminMenu"
              >
                <Settings class="w-5 h-5 text-blue-600 dark:text-blue-300" />
              </button>
              <transition name="fade-slide">
                <div
                  v-if="showAdminMenu"
                  class="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 border border-blue-100 dark:border-slate-800 rounded-xl shadow-xl z-50"
                  @click.outside="showAdminMenu = false"
                >
                  <router-link
                    to="/admin/settings"
                    class="block px-5 py-3 text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950"
                    >Settings</router-link
                  >
                  <router-link
                    to="/admin/celery"
                    class="block px-5 py-3 text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950"
                    >Celery & Queues</router-link
                  >
                  <!-- Add more as needed -->
                </div>
              </transition>
            </div>

            <!-- Activity Bell (visible to all authenticated users) -->
            <div v-if="isAuthenticated">
              <ActivityBell />
            </div>

            <!-- Dark mode toggle -->
            <button
              :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
              class="mr-3 p-2 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors focus:outline-none"
              @click="toggleDarkMode"
            >
              <Sun v-if="!isDark" class="w-5 h-5 text-slate-500" />
              <Moon v-else class="w-5 h-5 text-slate-400" />
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
                  <span
                    class="font-semibold text-lg text-blue-800 dark:text-blue-200 select-none"
                    >{{ userInitials }}</span
                  >
                  <span v-if="isAdmin" class="absolute -bottom-1 -right-1" title="Admin">
                    <ShieldCheck class="w-4 h-4 text-amber-400 drop-shadow" />
                  </span>
                </div>
                <ChevronDown
                  :class="{ 'rotate-180': showUserMenu }"
                  class="ml-2 w-4 h-4 text-blue-400 group-hover:text-blue-600 transition-transform duration-200"
                />
              </button>
              <transition name="fade-slide">
                <div
                  v-if="showUserMenu"
                  class="absolute right-0 mt-3 w-64 rounded-xl shadow-xl bg-white dark:bg-slate-900 ring-1 ring-blue-100 dark:ring-blue-900 z-50 animate-dropdown"
                  @click.outside="showUserMenu = false"
                >
                  <div class="px-5 py-3 border-b border-slate-100 dark:border-slate-800">
                    <div class="flex items-center gap-2">
                      <ShieldCheck v-if="isAdmin" class="w-5 h-5 text-amber-400" />
                      <span class="font-semibold text-slate-900 dark:text-white">{{
                        userName
                      }}</span>
                      <span
                        v-if="isAdmin"
                        class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-700"
                      >
                        Admin
                      </span>
                    </div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                      {{ userEmail }}
                    </div>
                  </div>
                  <a
                    class="block px-5 py-3 text-base text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors"
                    href="#"
                    @click.prevent="openChangePasswordModal"
                  >
                    <Lock class="inline-block w-5 h-5 mr-2 text-blue-500" />
                    Change Password
                  </a>
                  <a
                    class="block px-5 py-3 text-base text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950 hover:text-blue-700 dark:hover:text-blue-300 font-medium rounded-b-xl transition-colors"
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
                to="/login"
              >
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
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <footer
      class="w-full bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 py-4 text-center text-sm text-slate-500 dark:text-slate-400"
    >
      <div>
        &copy; {{ currentYear }} KatherLab. Licensed under
        <a
          class="underline hover:text-blue-600 dark:hover:text-blue-300"
          href="https://www.gnu.org/licenses/agpl-3.0.de.html"
          rel="noopener noreferrer"
          target="_blank"
        >
          AGPL-3.0
        </a>
      </div>
      <div class="space-x-4">
        <span :title="`Commit: ${frontendGitCommit}`" class="cursor-help">
          Frontend Version: {{ frontendVersion }}
        </span>
        <span :title="`Commit: ${backendGitCommit}`" class="cursor-help">
          Backend Version: {{ backendVersion }}
        </span>
      </div>
    </footer>
    <!-- Change Password Modal -->
    <BaseModal
      :open="showChangePasswordModal"
      title="Change Password"
      size="sm"
      panel-class="dark:bg-slate-900 dark:border-slate-800"
      header-class="dark:bg-slate-900"
      @close="closeChangePasswordModal"
    >
      <form class="flex flex-col gap-5" @submit.prevent="handleChangePassword">
        <FormField
          v-model="currentPassword"
          label="Current Password"
          type="password"
          required
          placeholder="Enter current password"
          autocomplete="current-password"
        />
        <FormField
          v-model="newPassword"
          label="New Password"
          type="password"
          required
          :minlength="8"
          :maxlength="128"
          placeholder="New password (8–128 chars)"
          autocomplete="new-password"
        />
        <FormField
          v-model="confirmPassword"
          label="Confirm New Password"
          type="password"
          required
          :minlength="8"
          :maxlength="128"
          placeholder="Repeat new password"
          autocomplete="new-password"
        />
        <ErrorBanner v-if="passwordError" :message="passwordError" />
        <div v-if="passwordSuccess" :class="['text-sm rounded px-3 py-2', getBannerClass('green')]">
          {{ passwordSuccess }}
        </div>
        <BaseButton
          type="submit"
          :loading="isChangingPassword"
          :disabled="isChangingPassword"
          class="mt-2 w-full"
        >
          {{ isChangingPassword ? 'Updating...' : 'Update Password' }}
        </BaseButton>
      </form>
    </BaseModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Settings, Sun, Moon, ShieldCheck, ChevronDown, Lock } from '@lucide/vue'
import { frontendVersion, frontendGitCommit } from '@/version.js'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { versionApi } from '@/services/versionApi'
import { usersApi } from '@/services/usersApi'
import { useToast } from 'vue-toastification'
import ActivityBell from '@/components/admin/ActivityBell.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { getBannerClass } from '@/utils/statusStyles'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref(false)
const backendVersion = ref('')
const backendGitCommit = ref('')
const isBackendDown = ref(false)
const currentYear = new Date().getFullYear()
const authReady = ref(false)
const toast = useToast()

const showAdminMenu = ref(false)

// Initialize dark mode state from localStorage or system preference
const getInitialDarkMode = () => {
  const saved = localStorage.getItem('darkMode')
  if (saved !== null) {
    return saved === '1'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const isDark = ref(getInitialDarkMode())

// Apply dark mode class on mount
const applyDarkMode = (val) => {
  if (val) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// Apply initial dark mode immediately
applyDarkMode(isDark.value)

function setDarkClass(val) {
  applyDarkMode(val)
  isDark.value = val
  localStorage.setItem('darkMode', val ? '1' : '0')
}

function toggleDarkMode() {
  setDarkClass(!isDark.value)
}

// Watch for system theme changes (only if user hasn't set explicit preference)
if (typeof window !== 'undefined' && window.matchMedia) {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handleChange = (e) => {
    const saved = localStorage.getItem('darkMode')
    if (saved === null) {
      // User hasn't set explicit preference, follow system
      setDarkClass(e.matches)
    }
  }
  mediaQuery.addEventListener('change', handleChange)
}

onMounted(async () => {
  // Fetch backend version and git commit
  try {
    const response = await versionApi.get()
    backendVersion.value = response.data.backend_version || response.data.version
    backendGitCommit.value = response.data.backend_git_commit || 'unknown'
    isBackendDown.value = false
  } catch (error) {
    console.error('Error fetching backend version:', error)
    isBackendDown.value = true
  }
  // Wait for authStore initialization
  await authStore.initialize()
  authReady.value = true
})

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isAdmin = computed(() => authStore.isAdmin)
const userName = computed(() => authStore.user?.full_name || '')
const userInitials = computed(() => {
  if (!authStore.user?.full_name) return ''
  return authStore.user.full_name
    .split(' ')
    .map((n) => n[0])
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
watch(
  () => router.currentRoute.value.fullPath,
  () => {
    showUserMenu.value = false
  },
)

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

const isPasswordValid = computed(
  () => newPassword.value.length >= 8 && newPassword.value.length <= 128,
)
const doPasswordsMatch = computed(() => newPassword.value === confirmPassword.value)

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
    await usersApi.changePassword({
      old_password: currentPassword.value,
      new_password: newPassword.value,
    })
    passwordSuccess.value = 'Password updated successfully!'
    toast.success('Your password has been updated.')
    setTimeout(() => {
      closeChangePasswordModal()
    }, 1100)
  } catch (err) {
    passwordError.value = extractErrorMessage(err, 'Password change failed.')
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

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity 0.18s,
    transform 0.15s;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}

.animate-dropdown {
  animation: dropdown-pop 0.22s cubic-bezier(0.21, 0.6, 0.43, 1.07);
}

@keyframes dropdown-pop {
  0% {
    opacity: 0;
    transform: translateY(-12px) scale(0.97);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
