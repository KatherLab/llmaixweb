<template>
  <div class="min-h-screen flex flex-col bg-surface-muted">
    <!-- Navigation -->
    <nav class="w-full bg-surface shadow-sm border-b border-default sticky top-0 z-40">
      <div
        v-if="isBackendDown"
        class="bg-red-600 text-white text-center py-1.5 text-xs font-medium animate-pulse"
      >
        Backend connection failed. Please check if the backend server is running.
      </div>
      <div class="w-full px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-14 items-center">
          <div class="flex items-center">
            <!-- Mobile menu toggle -->
            <button
              v-if="authReady && isAuthenticated"
              type="button"
              aria-label="Open menu"
              :aria-expanded="mobileMenuOpen"
              aria-controls="mobile-menu"
              class="md:hidden mr-2 p-2 rounded-card text-content-muted hover:bg-surface-sunken transition-colors"
              @click="mobileMenuOpen = !mobileMenuOpen"
            >
              <Menu v-if="!mobileMenuOpen" class="w-5 h-5" />
              <X v-else class="w-5 h-5" />
            </button>
            <div class="flex-shrink-0 flex items-center md:mr-8">
              <router-link :to="isAuthenticated ? '/projects' : '/'">
                <span class="text-xl font-extrabold tracking-tight text-content">LLMAIx-v2</span>
              </router-link>
            </div>
            <div v-if="authReady && isAuthenticated" class="hidden md:flex space-x-1">
              <router-link
                :class="[
                  $route.path.startsWith('/projects')
                    ? 'text-primary border-primary'
                    : 'text-content-muted border-transparent hover:text-content hover:border-strong',
                ]"
                class="inline-flex items-center px-4 h-14 text-sm font-medium border-b-2 transition-all"
                to="/projects"
              >
                Projects
              </router-link>

              <router-link
                v-if="isAdmin"
                :class="[
                  $route.path.startsWith('/admin')
                    ? 'text-primary border-primary'
                    : 'text-content-muted border-transparent hover:text-content hover:border-strong',
                ]"
                class="inline-flex items-center px-4 h-14 text-sm font-medium border-b-2 transition-all"
                to="/admin"
              >
                Admin
                <span
                  class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary-soft text-primary border border-primary/30"
                >
                  Admin
                </span>
              </router-link>
            </div>
          </div>

          <div class="flex items-center gap-1">
            <!-- Activity Bell (visible to all authenticated users) -->
            <div v-if="isAuthenticated">
              <ActivityBell />
            </div>

            <!-- Dark mode toggle -->
            <button
              :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
              class="mr-1 sm:mr-3 p-2 rounded-full hover:bg-surface-sunken transition-colors focus:outline-none"
              @click="toggleDarkMode"
            >
              <Sun v-if="!isDark" class="w-5 h-5 text-content-muted" />
              <Moon v-else class="w-5 h-5 text-content-muted" />
            </button>
            <div v-if="authReady && isAuthenticated" class="relative">
              <button
                aria-label="Open user menu"
                :aria-expanded="showUserMenu"
                aria-haspopup="true"
                aria-controls="user-menu"
                class="group flex items-center rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-surface focus:ring-ring"
                @click="toggleUserMenu"
              >
                <div
                  class="h-10 w-10 rounded-full bg-primary-soft flex items-center justify-center shadow-sm border border-primary/30 group-hover:scale-105 group-hover:shadow-lg transition-all duration-150 relative"
                >
                  <span class="font-semibold text-lg text-primary select-none">{{
                    userInitials
                  }}</span>
                  <span v-if="isAdmin" class="absolute -bottom-1 -right-1" title="Admin">
                    <ShieldCheck class="w-4 h-4 text-amber-400 drop-shadow" />
                  </span>
                </div>
                <ChevronDown
                  :class="{ 'rotate-180': showUserMenu }"
                  class="hidden sm:block ml-2 w-4 h-4 text-content-subtle group-hover:text-primary transition-transform duration-200"
                />
              </button>
              <transition name="fade-slide">
                <div
                  v-if="showUserMenu"
                  id="user-menu"
                  class="absolute right-0 mt-3 w-64 rounded-modal shadow-xl bg-surface ring-1 ring-default-border z-50 animate-dropdown"
                  @click.outside="showUserMenu = false"
                >
                  <div class="px-5 py-3 border-b border-default">
                    <div class="flex items-center gap-2">
                      <ShieldCheck v-if="isAdmin" class="w-5 h-5 text-amber-400" />
                      <span class="font-semibold text-content">{{ userName }}</span>
                      <span
                        v-if="isAdmin"
                        class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-700"
                      >
                        Admin
                      </span>
                    </div>
                    <div class="text-xs text-content-muted mt-1 truncate">
                      {{ userEmail }}
                    </div>
                  </div>
                  <router-link
                    class="block px-5 py-3 text-base text-content-muted hover:bg-primary-soft hover:text-primary font-medium transition-colors"
                    to="/account"
                    @click="showUserMenu = false"
                  >
                    <Settings class="inline-block w-5 h-5 mr-2 text-primary" />
                    Account settings
                  </router-link>
                  <a
                    class="block px-5 py-3 text-base text-content-muted hover:bg-primary-soft hover:text-primary font-medium transition-colors"
                    href="#"
                    @click.prevent="openChangePasswordModal"
                  >
                    <Lock class="inline-block w-5 h-5 mr-2 text-primary" />
                    Change Password
                  </a>
                  <a
                    class="block px-5 py-3 text-base text-content-muted hover:bg-primary-soft hover:text-primary font-medium rounded-b-modal transition-colors"
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
                class="bg-primary hover:bg-primary-hover text-white font-bold py-2 px-5 rounded-card shadow-sm transition"
                to="/login"
              >
                Login
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Mobile menu (slide-down) -->
      <transition name="fade-slide">
        <div
          v-if="mobileMenuOpen && authReady && isAuthenticated"
          id="mobile-menu"
          class="md:hidden border-t border-default bg-surface"
        >
          <router-link
            :class="[
              $route.path.startsWith('/projects')
                ? 'text-primary bg-primary-soft'
                : 'text-content-muted hover:bg-surface-sunken',
            ]"
            class="block px-4 py-3 text-sm font-medium"
            to="/projects"
            @click="mobileMenuOpen = false"
          >
            Projects
          </router-link>
          <router-link
            v-if="isAdmin"
            :class="[
              $route.path.startsWith('/admin')
                ? 'text-primary bg-primary-soft'
                : 'text-content-muted hover:bg-surface-sunken',
            ]"
            class="block px-4 py-3 text-sm font-medium"
            to="/admin"
            @click="mobileMenuOpen = false"
          >
            Admin
          </router-link>
          <div class="border-t border-default">
            <div class="px-4 py-2 text-xs text-content-subtle truncate">
              {{ userName }} · {{ userEmail }}
            </div>
            <router-link
              class="block px-4 py-3 text-sm font-medium text-content-muted hover:bg-surface-sunken"
              to="/account"
              @click="mobileMenuOpen = false"
            >
              Account settings
            </router-link>
            <a
              class="block px-4 py-3 text-sm font-medium text-content-muted hover:bg-surface-sunken"
              href="#"
              @click.prevent="openChangePasswordFromMobile"
            >
              Change Password
            </a>
            <a
              class="block px-4 py-3 text-sm font-medium text-content-muted hover:bg-surface-sunken"
              href="#"
              @click.prevent="logout"
            >
              Logout
            </a>
          </div>
        </div>
      </transition>
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
      class="w-full bg-surface border-t border-default py-4 text-center text-sm text-content-muted"
    >
      <div>
        &copy; {{ currentYear }} KatherLab. Licensed under
        <a
          class="underline hover:text-primary"
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
        <PasswordInput
          v-model="newPassword"
          label="New Password"
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

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Settings, Sun, Moon, ShieldCheck, ChevronDown, Lock, Menu, X } from '@lucide/vue'
import { frontendVersion, frontendGitCommit } from '@/version'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { versionApi } from '@/services/versionApi'
import { usersApi } from '@/services/usersApi'
import { useToast } from '@/composables/useToast'
import ActivityBell from '@/components/admin/ActivityBell.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { getBannerClass } from '@/utils/statusStyles'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const authStore = useAuthStore()
const showUserMenu = ref<boolean>(false)
const backendVersion = ref<string>('')
const backendGitCommit = ref<string>('')
const isBackendDown = ref<boolean>(false)
const currentYear: number = new Date().getFullYear()
const authReady = ref<boolean>(false)
const toast = useToast()

const mobileMenuOpen = ref<boolean>(false)

// Initialize dark mode state from localStorage or system preference
const getInitialDarkMode = (): boolean => {
  const saved = localStorage.getItem('darkMode')
  if (saved !== null) {
    return saved === '1'
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const isDark = ref<boolean>(getInitialDarkMode())

// Apply dark mode class on mount
const applyDarkMode = (val: boolean): void => {
  if (val) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// Apply initial dark mode immediately
applyDarkMode(isDark.value)

function setDarkClass(val: boolean): void {
  applyDarkMode(val)
  isDark.value = val
  localStorage.setItem('darkMode', val ? '1' : '0')
}

function toggleDarkMode(): void {
  setDarkClass(!isDark.value)
}

// Watch for system theme changes (only if user hasn't set explicit preference)
if (typeof window !== 'undefined' && window.matchMedia) {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handleChange = (e: MediaQueryListEvent): void => {
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
    backendGitCommit.value =
      (response.data as { backend_git_commit?: string }).backend_git_commit || 'unknown'
    isBackendDown.value = false
  } catch (error) {
    console.error('Error fetching backend version:', error)
    isBackendDown.value = true
  }
  // Wait for authStore initialization
  await authStore.initialize()
  authReady.value = true
})

const isAuthenticated = computed<boolean>(() => authStore.isAuthenticated)
const isAdmin = computed<boolean>(() => authStore.isAdmin)
const userName = computed<string>(() => authStore.user?.full_name || '')
const userInitials = computed<string>(() => {
  if (!authStore.user?.full_name) return ''
  return authStore.user.full_name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
})
const userEmail = computed<string>(() => authStore.user?.email || '')

async function logout(): Promise<void> {
  await authStore.logout()
  showUserMenu.value = false
  router.push('/login')
}

function toggleUserMenu(): void {
  showUserMenu.value = !showUserMenu.value
}

// Hide user menu + mobile menu on route change
watch(
  () => router.currentRoute.value.fullPath,
  () => {
    showUserMenu.value = false
    mobileMenuOpen.value = false
  },
)

// -----------------------
// Change Password Modal
// -----------------------
const showChangePasswordModal = ref<boolean>(false)
const currentPassword = ref<string>('')
const newPassword = ref<string>('')
const confirmPassword = ref<string>('')
const passwordError = ref<string>('')
const passwordSuccess = ref<string>('')
const isChangingPassword = ref<boolean>(false)

const isPasswordValid = computed<boolean>(
  () => newPassword.value.length >= 8 && newPassword.value.length <= 128,
)
const doPasswordsMatch = computed<boolean>(() => newPassword.value === confirmPassword.value)

function openChangePasswordModal(): void {
  passwordError.value = ''
  passwordSuccess.value = ''
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showChangePasswordModal.value = true
}

// Mobile-menu entry: open the change-password modal and close the menu.
function openChangePasswordFromMobile(): void {
  openChangePasswordModal()
  mobileMenuOpen.value = false
}

function closeChangePasswordModal(): void {
  showChangePasswordModal.value = false
}

async function handleChangePassword(): Promise<void> {
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
