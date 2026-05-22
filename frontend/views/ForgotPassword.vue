<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-gray-900 tracking-tight">LLMAIx-v2</h1>
      <p class="text-base text-gray-500 mt-2">Reset your password</p>
    </div>

    <!-- Step 1: Email input -->
    <div v-if="step === 1" class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
      <h2 class="text-lg font-bold text-gray-900 mb-2">Forgot your password?</h2>
      <p class="text-sm text-gray-500 mb-6">
        Enter your email address and we'll send you a link to reset your password.
      </p>
      <form @submit.prevent="handleForgotPassword">
        <div class="mb-5">
          <label for="email" class="block text-sm font-semibold text-gray-700 mb-2">Email address</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
            placeholder="e.g. your@email.com"
            autocomplete="email"
            spellcheck="false"
          />
        </div>
        <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {{ error }}
        </div>
        <button
          type="submit"
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 disabled:opacity-70 disabled:cursor-not-allowed"
          :disabled="isLoading"
        >
          <svg v-if="isLoading" class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          <span>{{ isLoading ? 'Sending...' : 'Send Reset Link' }}</span>
        </button>
      </form>
      <router-link to="/login" class="block mt-5 text-center text-blue-600 hover:underline text-sm">
        Back to login
      </router-link>
    </div>

    <!-- Step 2: Success message -->
    <div v-else class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-center">
      <div class="mx-auto mb-4 w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
        <svg class="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
      </div>
      <h2 class="text-lg font-bold text-gray-900 mb-2">Check your email</h2>
      <p class="text-sm text-gray-500 mb-6">
        If an account with that email exists, we've sent a password reset link to it.
      </p>
      <div v-if="emailWarning" class="mb-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm rounded-md">
        {{ emailWarning }}
      </div>
      <router-link to="/login" class="text-blue-600 hover:underline text-sm font-medium">
        Back to login
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '@/services/api.js'
import { useToast } from 'vue-toastification'

const toast = useToast()

const step = ref(1)
const email = ref('')
const isLoading = ref(false)
const error = ref(null)
const emailWarning = ref(null)

async function handleForgotPassword() {
  if (isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    const response = await api.post('/user/forgot-password', { email: email.value })
    emailWarning.value = response.data.warning || null
    step.value = 2
  } catch (err) {
    if (err.response?.status === 429) {
      error.value = 'Too many requests. Please try again later.'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'An unexpected error occurred. Please try again.'
    }
    console.error('Forgot password error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
