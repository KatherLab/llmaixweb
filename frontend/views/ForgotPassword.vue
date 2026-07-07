<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">Reset your password</p>
    </div>

    <!-- Step 1: Email input -->
    <div v-if="step === 1" class="bg-surface border border-default rounded-modal p-8 shadow-sm">
      <h2 class="text-lg font-bold text-content mb-2">Forgot your password?</h2>
      <p class="text-sm text-content-muted mb-6">
        Enter your email address and we'll send you a link to reset your password.
      </p>
      <form @submit.prevent="handleForgotPassword">
        <div class="mb-5">
          <FormField
            v-model="email"
            label="Email address"
            type="email"
            required
            maxlength="254"
            placeholder="e.g. your@email.com"
            autocomplete="email"
            :spellcheck="false"
          />
        </div>
        <ErrorBanner v-if="error" :message="error" class="mb-4" />
        <BaseButton
          type="submit"
          size="lg"
          :loading="isLoading"
          :disabled="isLoading"
          class="w-full py-2.5"
        >
          <Mail v-if="!isLoading" class="h-5 w-5" aria-hidden="true" />
          <span>{{ isLoading ? 'Sending...' : 'Send Reset Link' }}</span>
        </BaseButton>
      </form>
      <router-link to="/login" class="block mt-5 text-center text-primary hover:underline text-sm">
        Back to login
      </router-link>
    </div>

    <!-- Step 2: Success message -->
    <div v-else class="bg-surface border border-default rounded-modal p-8 shadow-sm text-center">
      <div
        class="mx-auto mb-4 w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center"
      >
        <Check class="w-6 h-6 text-green-600 dark:text-green-400" aria-hidden="true" />
      </div>
      <h2 class="text-lg font-bold text-content mb-2">Check your email</h2>
      <p class="text-sm text-content-muted mb-6">
        If an account with that email exists, we've sent a password reset link to it.
      </p>
      <div v-if="emailWarning" :class="['mb-4 p-3 text-sm rounded-card', getBannerClass('yellow')]">
        {{ emailWarning }}
      </div>
      <router-link to="/login" class="text-primary hover:underline text-sm font-medium">
        Back to login
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref } from 'vue'
import { Mail, Check } from '@lucide/vue'
import { usersApi } from '@/services/usersApi'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { getBannerClass } from '@/utils/statusStyles'
import { extractErrorMessage } from '@/utils/errors'

const step = ref<number>(1)
const email = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)
const emailWarning = ref<string | null>(null)

async function handleForgotPassword(): Promise<void> {
  if (isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    const response = await usersApi.forgotPassword(email.value)
    emailWarning.value = (response.data as { warning?: string | null }).warning || null
    step.value = 2
  } catch (err: unknown) {
    const axiosErr = err as { response?: { status?: number } }
    if (axiosErr.response?.status === 429) {
      error.value = 'Too many requests. Please try again later.'
    } else {
      error.value = extractErrorMessage(err, 'An unexpected error occurred. Please try again.')
    }
    console.error('Forgot password error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
