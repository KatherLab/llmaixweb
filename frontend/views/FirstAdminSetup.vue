<template>
  <div class="w-full max-w-md mx-auto py-10">
    <div class="mb-8 text-center">
      <div class="flex justify-center mb-2">
        <svg class="w-14 h-14 text-blue-700" fill="none" stroke="currentColor" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="22" stroke="currentColor" stroke-width="4" fill="#e6f0ff" />
          <path
            d="M18 30c0-3.3137 2.6863-6 6-6s6 2.6863 6 6"
            stroke="currentColor"
            stroke-width="3"
            stroke-linecap="round"
          />
          <circle cx="24" cy="19" r="4" fill="currentColor" />
        </svg>
      </div>
      <h1 class="text-3xl font-extrabold text-blue-700 mb-1">Welcome to LLMAIx-v2</h1>
      <p class="text-base text-gray-500">First-time setup: Create your admin account</p>
    </div>
    <form
      class="bg-white border border-gray-100 rounded-xl p-8 shadow-lg flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">Full Name</label>
        <input
          v-model="fullName"
          type="text"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Full name"
        />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">Email address</label>
        <input
          v-model="email"
          type="email"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="admin@yourcompany.com"
        />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">Password</label>
        <input
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Password"
        />
      </div>
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">Confirm Password</label>
        <input
          v-model="confirmPassword"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Confirm password"
        />
      </div>
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading || !isFormValid"
        class="w-full py-2.5"
      >
        {{ isLoading ? 'Creating admin...' : 'Create Admin Account' }}
      </BaseButton>
      <transition name="fade">
        <div
          v-if="error"
          class="mt-2 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md text-center"
        >
          {{ error }}
        </div>
      </transition>
    </form>
    <div class="text-center text-gray-400 text-xs mt-8">Powered by LLMAIx (v2)</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'vue-toastification'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)

const isFormValid = computed(
  () =>
    fullName.value.length >= 2 &&
    email.value.includes('@') &&
    password.value.length >= 8 &&
    password.value === confirmPassword.value,
)

async function handleSubmit() {
  if (!isFormValid.value || isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    await usersApi.createFirstAdmin({
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'admin',
    })
    // Auto-login
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)
    const resp = await authApi.login(formData.toString())
    await authStore.setToken(resp.data.access_token)
    await authStore.fetchUser()
    // --- Re-check first-admin state (to update Pinia) ---
    const firstAdminStore = useFirstAdminStore()
    await firstAdminStore.checkFirstAdmin()

    // --- Only then, route away
    toast.success('Admin account created! Welcome 👋')
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to create admin. Try again.'
    toast.error(error.value)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
