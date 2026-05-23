<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-gray-900 tracking-tight">LLMAIx-v2</h1>
      <p class="text-base text-gray-500 mt-2">Set a new password</p>
    </div>

    <!-- Loading: validating token -->
    <div
      v-if="state === 'loading'"
      class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-center"
    >
      <div class="mx-auto mb-4 w-12 h-12">
        <svg
          class="animate-spin h-10 w-10 text-blue-600 mx-auto"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>
      <p class="text-sm text-gray-500">Validating your reset link...</p>
    </div>

    <!-- Invalid / Expired token -->
    <div
      v-else-if="state === 'invalid'"
      class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-center"
    >
      <div class="mx-auto mb-4 w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
        <svg class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <h2 class="text-lg font-bold text-gray-900 mb-2">Invalid or Expired Link</h2>
      <p class="text-sm text-gray-500 mb-6">
        This password reset link is no longer valid. It may have expired (links are valid for 24
        hours) or already been used.
      </p>
      <router-link
        to="/forgot-password"
        class="inline-block px-5 py-2.5 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors"
      >
        Request New Reset Link
      </router-link>
      <br />
      <router-link to="/login" class="inline-block mt-3 text-blue-600 hover:underline text-sm">
        Back to login
      </router-link>
    </div>

    <!-- Password form -->
    <div v-else class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
      <h2 class="text-lg font-bold text-gray-900 mb-2">Set new password</h2>
      <p class="text-sm text-gray-500 mb-6">Enter your new password below.</p>
      <form @submit.prevent="handleResetPassword">
        <div class="mb-4">
          <label for="new-password" class="block text-sm font-semibold text-gray-700 mb-2"
            >New Password</label
          >
          <input
            id="new-password"
            v-model="newPassword"
            type="password"
            required
            minlength="8"
            class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
            placeholder="At least 8 characters"
            autocomplete="new-password"
          />
          <p v-if="passwordHint" class="mt-1 text-xs text-gray-400">{{ passwordHint }}</p>
        </div>
        <div class="mb-5">
          <label for="confirm-password" class="block text-sm font-semibold text-gray-700 mb-2"
            >Confirm Password</label
          >
          <input
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            required
            minlength="8"
            class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
            :class="{ 'border-red-300 bg-red-50': passwordsMismatch }"
            placeholder="Repeat your password"
            autocomplete="new-password"
          />
          <p v-if="passwordsMismatch" class="mt-1 text-xs text-red-500">Passwords do not match.</p>
        </div>
        <div
          v-if="error"
          class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md"
        >
          {{ error }}
        </div>
        <button
          type="submit"
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 disabled:opacity-70 disabled:cursor-not-allowed"
          :disabled="isLoading || passwordsMismatch || !newPassword || !confirmPassword"
        >
          <svg
            v-if="isLoading"
            class="animate-spin h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
          <span>{{ isLoading ? 'Resetting...' : 'Reset Password' }}</span>
        </button>
      </form>
      <router-link to="/login" class="block mt-5 text-center text-blue-600 hover:underline text-sm">
        Back to login
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/services/api.js'
import { useToast } from 'vue-toastification'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const state = ref('loading') // loading | invalid | form | success
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)

const passwordHint = computed(() => {
  if (!newPassword.value) return ''
  if (newPassword.value.length < 8) return 'Minimum 8 characters'
  return 'Password strength: okay'
})

const passwordsMismatch = computed(() => {
  if (!confirmPassword.value) return false
  return newPassword.value !== confirmPassword.value
})

onMounted(async () => {
  const token = route.params.token
  if (!token) {
    state.value = 'invalid'
    return
  }

  try {
    await api.get(`/user/validate-reset-token/${token}`)
    state.value = 'form'
  } catch (err) {
    state.value = 'invalid'
  }
})

async function handleResetPassword() {
  if (isLoading.value || passwordsMismatch.value) return
  isLoading.value = true
  error.value = null

  const token = route.params.token

  try {
    await api.post(`/user/reset-password/${token}`, {
      token: token,
      new_password: newPassword.value,
    })
    toast.success('Password reset successfully!', {
      timeout: 3000,
      position: 'top-right',
      closeButton: true,
    })
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (err) {
    if (err.response?.status === 404) {
      state.value = 'invalid'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'An unexpected error occurred. Please try again.'
    }
    console.error('Reset password error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
