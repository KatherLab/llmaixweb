<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">{{ $t('auth.reset.header_subtitle') }}</p>
    </div>

    <!-- Loading: validating token -->
    <div
      v-if="state === 'loading'"
      class="bg-surface border border-default rounded-modal p-8 shadow-sm text-center"
    >
      <div class="mx-auto mb-4 w-12 h-12">
        <LoadingSpinner size="medium" />
      </div>
      <p class="text-sm text-content-muted">{{ $t('auth.reset.validating') }}</p>
    </div>

    <!-- Invalid / Expired token -->
    <div
      v-else-if="state === 'invalid'"
      class="bg-surface border border-default rounded-modal p-8 shadow-sm text-center"
    >
      <div
        class="mx-auto mb-4 w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center"
      >
        <TriangleAlert class="w-6 h-6 text-red-600 dark:text-red-400" aria-hidden="true" />
      </div>
      <h2 class="text-lg font-bold text-content mb-2">{{ $t('auth.reset.invalid_title') }}</h2>
      <p class="text-sm text-content-muted mb-6">
        {{ $t('auth.reset.invalid_description') }}
      </p>
      <BaseButton to="/forgot-password">{{ $t('auth.reset.request_new') }}</BaseButton>
      <br />
      <router-link to="/login" class="inline-block mt-3 text-primary hover:underline text-sm">
        {{ $t('auth.actions.back_to_login') }}
      </router-link>
    </div>

    <!-- Password form -->
    <div v-else class="bg-surface border border-default rounded-modal p-8 shadow-sm">
      <h2 class="text-lg font-bold text-content mb-2">{{ $t('auth.reset.form_title') }}</h2>
      <p class="text-sm text-content-muted mb-6">{{ $t('auth.reset.form_description') }}</p>
      <form @submit.prevent="handleResetPassword">
        <div class="mb-4">
          <PasswordInput
            v-model="newPassword"
            :label="$t('auth.form.new_password')"
            required
            :minlength="8"
            :placeholder="$t('auth.reset.new_password_placeholder')"
            autocomplete="new-password"
          />
        </div>
        <div class="mb-5">
          <FormField
            v-model="confirmPassword"
            :label="$t('auth.form.confirm_password')"
            type="password"
            required
            :minlength="8"
            :invalid="passwordsMismatch"
            :placeholder="$t('auth.reset.confirm_password_placeholder')"
            autocomplete="new-password"
          >
            <template v-if="passwordsMismatch" #error>{{
              $t('auth.errors.passwords_mismatch_period')
            }}</template>
          </FormField>
        </div>
        <ErrorBanner v-if="error" :message="error" class="mb-4" />
        <BaseButton
          type="submit"
          size="lg"
          :loading="isLoading"
          :disabled="isLoading || passwordsMismatch || !newPassword || !confirmPassword"
          class="w-full py-2.5"
        >
          <Lock v-if="!isLoading" class="h-5 w-5" aria-hidden="true" />
          <span>{{
            isLoading ? $t('auth.reset.resetting') : $t('auth.reset.reset_password')
          }}</span>
        </BaseButton>
      </form>
      <router-link to="/login" class="block mt-5 text-center text-primary hover:underline text-sm">
        {{ $t('auth.actions.back_to_login') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { TriangleAlert, Lock } from '@lucide/vue'
import { useRouter, useRoute } from 'vue-router'
import { usersApi } from '@/services/usersApi'
import { useToast } from '@/composables/useToast'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { extractErrorMessage } from '@/utils/errors'

type ResetState = 'loading' | 'invalid' | 'form' | 'success'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const route = useRoute()
const toast = useToast()

const state = ref<ResetState>('loading')
const newPassword = ref<string>('')
const confirmPassword = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)

const passwordsMismatch = computed<boolean>(() => {
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
    await usersApi.validateResetToken(String(token))
    state.value = 'form'
  } catch {
    state.value = 'invalid'
  }
})

async function handleResetPassword(): Promise<void> {
  if (isLoading.value || passwordsMismatch.value) return
  isLoading.value = true
  error.value = null

  const token = route.params.token

  try {
    // The backend's reset endpoint accepts `token` in the body as well as the
    // URL path; the typed payload omits it, so build the body loosely.
    const body = {
      token: String(token),
      new_password: newPassword.value,
    }
    await usersApi.resetPassword(String(token), body)
    toast.success(t('auth.reset.success_toast'), {
      timeout: 3000,
    })
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { status?: number } }
    if (axiosErr.response?.status === 404) {
      state.value = 'invalid'
    } else {
      error.value = extractErrorMessage(err, t('auth.errors.unexpected'))
    }
    console.error('Reset password error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
