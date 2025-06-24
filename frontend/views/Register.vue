<!-- src/views/Register.vue -->
<template>
  <div class="max-w-lg mx-auto px-4 py-10">
    <h1 class="text-4xl font-bold text-gray-900 text-center mb-1">LLMAIx-v2</h1>
    <p class="text-lg text-gray-600 text-center mb-10">Extract information from Documents using LLMs.</p>

    <div v-if="!isValidInvitation && !validating && config.requireInvitation" class="bg-white rounded-lg shadow-md p-6 text-center">
      <svg class="w-12 h-12 text-red-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <h2 class="text-xl font-bold text-red-700 mt-2">Invalid Invitation</h2>
      <p class="mt-2 text-gray-600">The invitation link you used is invalid or has expired.</p>
      <router-link to="/login" class="mt-4 inline-block text-blue-600 hover:underline">
        Go to Login Page
      </router-link>
    </div>

    <div v-else-if="validating && config.requireInvitation" class="flex flex-col items-center justify-center h-32">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      <p class="mt-4 text-center text-gray-600">Verifying your invitation...</p>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="bg-white rounded-lg shadow-md p-8">
      <div v-if="isValidInvitation && config.requireInvitation" class="p-3 bg-green-50 border border-green-200 rounded-md mb-6">
        <p class="text-sm text-green-700 flex items-center">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          Valid invitation. Please complete your registration.
        </p>
      </div>

      <div class="mb-6">
        <label for="fullName" class="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
        <input
          id="fullName"
          v-model="fullName"
          type="text"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Your full name"
        />
      </div>

      <div class="mb-6">
        <label for="email" class="block text-sm font-medium text-gray-700 mb-2">Email address</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          placeholder="Your email"
          :disabled="isEmailFromInvitation"
        />
        <p v-if="isEmailFromInvitation" class="mt-1 text-sm text-gray-500">
          This email is linked to your invitation
        </p>
      </div>

      <div class="mb-6">
        <label for="password" class="block text-sm font-medium text-gray-700 mb-2">Password</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Create a password"
        />
      </div>

      <div class="mb-6">
        <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
        <input
          id="confirmPassword"
          v-model="confirmPassword"
          type="password"
          required
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Confirm your password"
        />
      </div>

      <button
        type="submit"
        class="w-full flex items-center justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-70 disabled:cursor-not-allowed disabled:bg-blue-500"
        :disabled="isLoading || !isFormValid"
      >
        <svg v-if="!isLoading" class="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        {{ isLoading ? 'Creating account...' : 'Create Account' }}
      </button>

      <div v-if="error" class="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded-md text-center">
        {{ error }}
      </div>

      <router-link to="/login" class="block mt-6 text-center text-blue-600 hover:underline text-sm">
        Already have an account? Sign in here
      </router-link>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()
const route = useRoute()
const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)
const invitationToken = ref('')
const isValidInvitation = ref(false)
const validating = ref(false)
const isEmailFromInvitation = ref(false)

// App configuration - can be moved to a central config store
const config = ref({
  requireInvitation: true // Set to false to enable normal registration without invitation
})

// Extract token from URL and validate it
onMounted(async () => {
  // Get the token from the query parameters
  const token = route.query.token
  const emailParam = route.query.email

  // If email is provided in the URL, set it and lock the field
  if (emailParam) {
    email.value = emailParam
    isEmailFromInvitation.value = true
  }

  if (!token) {
    if (config.value.requireInvitation) {
      validating.value = false
      return
    } else {
      // Skip invitation validation if not required
      isValidInvitation.value = true
      validating.value = false
      return
    }
  }

  invitationToken.value = token
  validating.value = true

  try {
    // Only validate if invitation is required
    if (config.value.requireInvitation) {
      await validateInvitation(token)
    } else {
      isValidInvitation.value = true
    }
  } catch (err) {
    console.error('Error validating invitation:', err)
  } finally {
    validating.value = false
  }
})

async function validateInvitation(token) {
  try {
    const response = await api.get(`/user/validate-invitation/${token}`)

    // If the backend returns valid=true and an email, set it
    if (response.data.valid && response.data.email) {
      email.value = response.data.email
      isEmailFromInvitation.value = true
    }

    isValidInvitation.value = response.data.valid
  } catch (err) {
    isValidInvitation.value = false
    console.error('Invalid invitation:', err)
  }
}

const isFormValid = computed(() => {
  const basicValidation = fullName.value.length >= 2 &&
         email.value.includes('@') &&
         password.value.length >= 6 &&
         password.value === confirmPassword.value

  // Add invitation validation only if required
  if (config.value.requireInvitation) {
    return basicValidation && isValidInvitation.value
  }

  return basicValidation
})

async function handleSubmit() {
  if (isLoading.value || !isFormValid.value) return

  isLoading.value = true
  error.value = null

  try {
    // Create registration payload
    const payload = {
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'user'
    }

    // Add invitation token if required
    if (config.value.requireInvitation) {
      payload.invitation_token = invitationToken.value
    }

    await api.post('/user', payload)

    // After successful registration, try to login
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })

    router.push('/landing')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Registration failed. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>