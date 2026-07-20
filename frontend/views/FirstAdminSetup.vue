<template>
  <div class="w-full max-w-md mx-auto py-10">
    <div class="mb-8 text-center">
      <div class="flex justify-center mb-2">
        <CircleUser class="w-12 h-12 text-content-subtle" aria-hidden="true" />
      </div>
      <h1 class="text-4xl font-extrabold text-content tracking-tight mb-1">
        {{ $t('auth.first_admin.welcome_to') }} <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted">{{ $t('auth.first_admin.subtitle') }}</p>
    </div>
    <form
      class="bg-surface border border-default rounded-modal p-8 shadow-lg flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <FormField
        v-model="fullName"
        :label="$t('auth.form.full_name')"
        type="text"
        required
        :placeholder="$t('auth.first_admin.full_name_placeholder')"
        data-testid="first-admin-name"
      />
      <FormField
        v-model="email"
        :label="$t('auth.form.email')"
        type="email"
        required
        maxlength="254"
        :placeholder="$t('auth.form.email_admin_placeholder')"
        data-testid="first-admin-email"
      />
      <PasswordInput
        v-model="password"
        :label="$t('auth.form.password')"
        required
        :placeholder="$t('auth.form.password_placeholder')"
        data-testid="first-admin-password"
      />
      <FormField
        v-model="confirmPassword"
        :label="$t('auth.form.confirm_password')"
        type="password"
        required
        :placeholder="$t('auth.first_admin.confirm_password_placeholder')"
        :invalid="!!confirmPassword && confirmPassword !== password"
        data-testid="first-admin-confirm"
      >
        <template v-if="!!confirmPassword && confirmPassword !== password" #error>
          {{ $t('auth.errors.passwords_mismatch') }}
        </template>
      </FormField>
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading || !isFormValid"
        data-testid="first-admin-submit"
        class="w-full py-2.5"
      >
        {{ isLoading ? $t('auth.first_admin.creating') : $t('auth.first_admin.create_account') }}
      </BaseButton>
      <transition name="fade">
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
    </form>
    <div class="text-center text-content-subtle text-xs mt-8">
      {{ $t('auth.first_admin.powered_by') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { CircleUser } from '@lucide/vue'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { extractErrorMessage } from '@/utils/errors'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const fullName = ref<string>('')
const email = ref<string>('')
const password = ref<string>('')
const confirmPassword = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)

const isFormValid = computed<boolean>(
  () =>
    fullName.value.length >= 2 &&
    email.value.includes('@') &&
    password.value.length >= 8 &&
    password.value === confirmPassword.value,
)

async function handleSubmit(): Promise<void> {
  if (!isFormValid.value || isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    // `role` is accepted by the backend's first-admin endpoint but not
    // declared on UserCreate — build as a plain record to avoid excess-
    // property checking at the call site.
    const payload = {
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'admin',
    }
    await usersApi.createFirstAdmin(payload)
    // Auto-login
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)
    const resp = await authApi.login(formData.toString())
    await authStore.setSession(resp.data.access_token, resp.data.refresh_token)
    // --- Re-check first-admin state (to update Pinia) ---
    const firstAdminStore = useFirstAdminStore()
    await firstAdminStore.checkFirstAdmin()

    // --- Only then, route away
    toast.success(t('auth.first_admin.success_toast'))
    router.push('/')
  } catch (err) {
    error.value = extractErrorMessage(err, t('auth.errors.create_admin_failed'))
    toast.error(error.value)
  } finally {
    isLoading.value = false
  }
}
</script>
