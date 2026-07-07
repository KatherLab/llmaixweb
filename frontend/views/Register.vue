<template>
  <div class="w-full max-w-md mx-auto">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">
        Extract information from documents using LLMs.
      </p>
    </div>
    <!-- Registration Closed Message -->
    <div
      v-if="!allowRegister && !isLoadingSettings"
      class="p-8 bg-surface border border-default rounded-modal text-center text-content-muted"
    >
      Registration is currently closed. Please use an invitation link.
    </div>

    <!-- Registration Form -->
    <form
      v-else
      class="bg-surface border border-default rounded-modal p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <FormField
        v-model="fullName"
        label="Full Name"
        type="text"
        required
        placeholder="Your full name"
      />
      <FormField
        v-model="email"
        label="Email address"
        type="email"
        required
        maxlength="254"
        :disabled="isEmailFromInvitation"
        placeholder="Your email"
      >
        <template v-if="isEmailFromInvitation" #hint>
          This email is linked to your invitation
        </template>
      </FormField>
      <PasswordInput v-model="password" label="Password" required placeholder="Create a password" />
      <FormField
        v-model="confirmPassword"
        label="Confirm Password"
        type="password"
        required
        placeholder="Confirm your password"
        :invalid="!!confirmPassword && confirmPassword !== password"
      >
        <template v-if="!!confirmPassword && confirmPassword !== password" #error>
          Passwords do not match
        </template>
      </FormField>
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
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
      <router-link
        to="/login"
        class="block mt-3 text-center text-primary hover:underline text-sm transition"
      >
        Already have an account? <span class="font-semibold">Sign in here</span>
      </router-link>
    </form>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const authStore = useAuthStore()
const firstAdminStore = useFirstAdminStore()

const fullName = ref<string>('')
const email = ref<string>('')
const password = ref<string>('')
const confirmPassword = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)
const invitationToken = ref<string>('')
const isEmailFromInvitation = ref<boolean>(false)

const requireInvitation = ref<boolean>(true)
const isLoadingSettings = ref<boolean>(true)
const allowRegister = computed<boolean>(
  () => !requireInvitation.value || isEmailFromInvitation.value,
)

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
  } catch {
    requireInvitation.value = true
  } finally {
    isLoadingSettings.value = false
  }

  // Handle invitation logic: validate token and fetch email from backend
  const token = route.query.token
  if (token) {
    invitationToken.value = String(token)
    try {
      const response = await usersApi.validateInvitation(String(token))
      if (response.data && response.data.valid) {
        email.value = response.data.email ?? ''
        isEmailFromInvitation.value = true
      } else {
        error.value = 'Invitation is invalid or has already been used'
      }
    } catch {
      error.value = 'Failed to validate invitation. It may be expired or invalid.'
    }
  }
})

const isFormValid = computed<boolean>(
  () =>
    fullName.value.length >= 2 &&
    email.value.includes('@') &&
    password.value.length >= 8 &&
    password.value === confirmPassword.value,
)

async function handleSubmit(): Promise<void> {
  if (isLoading.value || !isFormValid.value) return

  isLoading.value = true
  error.value = null

  try {
    // Registration payload (includes `role` which the backend accepts but
    // UserCreate type doesn't declare — cast to satisfy the call signature).
    const payload = {
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'user',
      ...(invitationToken.value ? { invitation_token: invitationToken.value } : {}),
    }

    await usersApi.create(payload)

    // Auto-login (save token + fetch user, just like login page)
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const loginResponse = await authApi.login(formData.toString())

    await authStore.setSession(loginResponse.data.access_token, loginResponse.data.refresh_token)

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
