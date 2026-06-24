<template>
  <div class="w-full max-w-md mx-auto">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-gray-900 tracking-tight">LLMAIx-v2</h1>
      <p class="text-base text-gray-500 mt-2">Extract information from documents using LLMs.</p>
    </div>
    <!-- Registration Closed Message -->
    <div
      v-if="!allowRegister && !isLoadingSettings"
      class="p-8 bg-white border border-gray-100 rounded-xl text-center text-gray-500"
    >
      Registration is currently closed. Please use an invitation link.
    </div>

    <!-- Registration Form -->
    <form
      v-else
      class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <div>
        <label for="fullName" class="block text-sm font-semibold text-gray-700 mb-2"
          >Full Name</label
        >
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
        <label for="email" class="block text-sm font-semibold text-gray-700 mb-2"
          >Email address</label
        >
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
        <label for="password" class="block text-sm font-semibold text-gray-700 mb-2"
          >Password</label
        >
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
        <label for="confirmPassword" class="block text-sm font-semibold text-gray-700 mb-2"
          >Confirm Password</label
        >
        <input
          id="confirmPassword"
          v-model="confirmPassword"
          type="password"
          required
          class="w-full px-3 py-2 rounded-lg border border-gray-300 bg-gray-50 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition"
          placeholder="Confirm your password"
        />
      </div>
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading || !isFormValid"
        class="w-full py-2.5"
      >
        {{ isLoading ? 'Creating account...' : 'Create Account' }}
      </BaseButton>
      <transition name="fade">
        <div
          v-if="error"
          class="mt-2 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md text-center"
        >
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
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { useToast } from 'vue-toastification'
import { useAuthStore } from '@/stores/auth'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const authStore = useAuthStore()
const firstAdminStore = useFirstAdminStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)
const invitationToken = ref('')
const isEmailFromInvitation = ref(false)

const requireInvitation = ref(true)
const isLoadingSettings = ref(true)
const allowRegister = computed(() => !requireInvitation.value || isEmailFromInvitation.value)

onMounted(async () => {
  // If first-admin flow is needed, redirect to it (extra safe)
  if (!firstAdminStore.checked) {
    await firstAdminStore.checkFirstAdmin()
  }
  if (firstAdminStore.needsFirstAdmin) {
    router.replace('/first-admin')
    return
  }
  // Fetch require_invitation from backend
  try {
    const res = await authApi.getSettings()
    requireInvitation.value = !!res.data.require_invitation
  } catch (e) {
    requireInvitation.value = true
  } finally {
    isLoadingSettings.value = false
  }

  // Handle invitation logic: validate token and fetch email from backend
  const token = route.query.token
  if (token) {
    invitationToken.value = token
    try {
      const response = await usersApi.validateInvitation(token)
      if (response.data && response.data.valid) {
        email.value = response.data.email
        isEmailFromInvitation.value = true
      } else {
        error.value = 'Invitation is invalid or has already been used'
      }
    } catch (err) {
      error.value = 'Failed to validate invitation. It may be expired or invalid.'
    }
  }
})

const isFormValid = computed(
  () =>
    fullName.value.length >= 2 &&
    email.value.includes('@') &&
    password.value.length >= 6 &&
    password.value === confirmPassword.value,
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
      role: 'user',
    }
    if (invitationToken.value) payload.invitation_token = invitationToken.value

    await usersApi.create(payload)

    // Auto-login (save token + fetch user, just like login page)
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const loginResponse = await authApi.login(formData.toString())

    await authStore.setToken(loginResponse.data.access_token)
    await authStore.fetchUser()

    toast.success('Registration successful! Logging you in...')
    router.push(authStore.isAdmin ? '/' : '/')
  } catch (err) {
    error.value = extractErrorMessage(err, 'Registration failed. Please try again.')
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
