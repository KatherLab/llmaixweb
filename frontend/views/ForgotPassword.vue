<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">{{ $t('auth.forgot.header_subtitle') }}</p>
    </div>

    <!-- Step 1: Email input -->
    <div v-if="step === 1" class="bg-surface border border-default rounded-modal p-8 shadow-sm">
      <h2 class="text-lg font-bold text-content mb-2">{{ $t('auth.forgot.title') }}</h2>
      <p class="text-sm text-content-muted mb-6">
        {{ $t('auth.forgot.description') }}
      </p>
      <form @submit.prevent="handleForgotPassword">
        <div class="mb-5">
          <FormField
            v-model="email"
            :label="$t('auth.form.email')"
            type="email"
            required
            maxlength="254"
            :placeholder="$t('auth.form.email_placeholder')"
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
          <span>{{ isLoading ? $t('auth.forgot.sending') : $t('auth.forgot.send_link') }}</span>
        </BaseButton>
      </form>
      <router-link to="/login" class="block mt-5 text-center text-primary hover:underline text-sm">
        {{ $t('auth.actions.back_to_login') }}
      </router-link>
    </div>

    <!-- Step 2: Success message -->
    <div v-else class="bg-surface border border-default rounded-modal p-8 shadow-sm text-center">
      <div
        class="mx-auto mb-4 w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center"
      >
        <Check class="w-6 h-6 text-green-600 dark:text-green-400" aria-hidden="true" />
      </div>
      <h2 class="text-lg font-bold text-content mb-2">{{ $t('auth.forgot.check_email_title') }}</h2>
      <p class="text-sm text-content-muted mb-6">
        {{ $t('auth.forgot.check_email_description') }}
      </p>
      <div v-if="emailWarning" :class="['mb-4 p-3 text-sm rounded-card', getBannerClass('yellow')]">
        {{ emailWarning }}
      </div>
      <router-link to="/login" class="text-primary hover:underline text-sm font-medium">
        {{ $t('auth.actions.back_to_login') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mail, Check } from '@lucide/vue'
import { usersApi } from '@/services/usersApi'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { getBannerClass } from '@/utils/statusStyles'
import { extractErrorMessage } from '@/utils/errors'

const { t } = useI18n({ useScope: 'global' })
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
      error.value = t('auth.errors.too_many_requests')
    } else {
      error.value = extractErrorMessage(err, t('auth.errors.unexpected'))
    }
    console.error('Forgot password error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
