<template>
  <div class="w-full max-w-md mx-auto">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">
        {{ $t('auth.tagline') }}
      </p>
    </div>
    <!-- Registration Closed Message -->
    <div
      v-if="!allowRegister && !isLoadingSettings"
      class="p-8 bg-surface border border-default rounded-modal text-center text-content-muted"
    >
      {{ $t('auth.register.closed') }}
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
        :label="$t('auth.form.full_name')"
        type="text"
        required
        :placeholder="$t('auth.register.full_name_placeholder')"
      />
      <FormField
        v-model="email"
        :label="$t('auth.form.email')"
        type="email"
        required
        maxlength="254"
        :disabled="isEmailFromInvitation"
        :placeholder="$t('auth.register.email_placeholder')"
      >
        <template v-if="isEmailFromInvitation" #hint>
          {{ $t('auth.register.email_from_invitation') }}
        </template>
      </FormField>
      <PasswordInput
        v-model="password"
        :label="$t('auth.form.password')"
        required
        :placeholder="$t('auth.register.password_placeholder')"
      />
      <FormField
        v-model="confirmPassword"
        :label="$t('auth.form.confirm_password')"
        type="password"
        required
        :placeholder="$t('auth.register.confirm_password_placeholder')"
        :invalid="!!confirmPassword && confirmPassword !== password"
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
        class="w-full py-2.5"
      >
        {{ isLoading ? $t('auth.register.creating') : $t('auth.register.create_account') }}
      </BaseButton>
      <transition name="fade">
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
      <router-link
        to="/login"
        class="block mt-3 text-center text-primary hover:underline text-sm transition"
      >
        {{ $t('auth.register.have_account') }}
        <span class="font-semibold">{{ $t('auth.register.sign_in_here') }}</span>
      </router-link>
    </form>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n({ useScope: 'global' })
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
        error.value = t('auth.errors.invitation_invalid_or_used')
      }
    } catch {
      error.value = t('auth.errors.invitation_validate_failed')
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

    toast.success(t('auth.register.success_toast'))
    router.push('/projects')
  } catch (err) {
    error.value = extractErrorMessage(err, t('auth.errors.registration_failed'))
    toast.error(error.value)
  } finally {
    isLoading.value = false
  }
}
</script>
