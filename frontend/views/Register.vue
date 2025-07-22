<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-gray-900 tracking-tight">LLMAIx-v2</h1>
      <p class="text-base text-gray-500 mt-2">Extract information from documents using LLMs.</p>
    </div>
    <form
      @submit.prevent="handleSubmit"
      class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
    >
      <div>
        <label for="fullName" class="block text-sm font-semibold text-gray-700 mb-2">Full Name</label>
        <input
          id="fullName"
          v-model="fullName"
          type="text"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Your full name"
        />
      </div>
      <div>
        <label for="email" class="block text-sm font-semibold text-gray-700 mb-2">Email address</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          :disabled="isEmailFromInvitation"
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition disabled:bg-gray-100"
          placeholder="Your email"
        />
        <p v-if="isEmailFromInvitation" class="mt-1 text-sm text-gray-500">
          This email is linked to your invitation
        </p>
      </div>
      <div>
        <label for="password" class="block text-sm font-semibold text-gray-700 mb-2">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Create a password"
        />
      </div>
      <div>
        <label for="confirmPassword" class="block text-sm font-semibold text-gray-700 mb-2">Confirm Password</label>
        <input
          id="confirmPassword"
          v-model="confirmPassword"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Confirm your password"
        />
      </div>
      <button
        type="submit"
        class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 disabled:opacity-70 disabled:cursor-not-allowed"
        :disabled="isLoading || !isFormValid"
      >
        <svg v-if="isLoading" class="animate-spin h-5 w-5 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
        </svg>
        <span>{{ isLoading ? 'Creating account...' : 'Create Account' }}</span>
      </button>
      <transition name="fade">
        <div v-if="error" class="mt-2 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md text-center">
          {{ error }}
        </div>
      </transition>
      <router-link
        to="/login"
        class="block mt-3 text-center text-blue-600 hover:underline text-sm transition"
      >
        Already have an account? <span class="font-semibold">Sign in here</span>
      </router-link>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)
const invitationToken = ref('')
const isEmailFromInvitation = ref(false)

onMounted(() => {
  // Optional: handle pre-filled email from invitation
  const token = route.query.token
  const emailParam = route.query.email
  if (token) invitationToken.value = token
  if (emailParam) {
    email.value = emailParam
    isEmailFromInvitation.value = true
  }
})

const isFormValid = computed(() =>
  fullName.value.length >= 2 &&
  email.value.includes('@') &&
  password.value.length >= 6 &&
  password.value === confirmPassword.value
)

async function handleSubmit() {
  if (isLoading.value || !isFormValid.value) return

  isLoading.value = true
  error.value = null

  try {
    // Registration payload
    const payload = {
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'user'
    }
    if (invitationToken.value) payload.invitation_token = invitationToken.value

    await api.post('/user', payload)

    // Auto-login
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    toast.success('Registration successful! Logging you in...')
    router.push('/')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Registration failed. Please try again.'
    toast.error(error.value)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
