<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-content tracking-tight">
        <AppBrand :as-link="false" size="md" />
      </h1>
      <p class="text-base text-content-muted mt-2">
        {{ $t('auth.tagline') }}
      </p>
    </div>
    <form
      class="bg-surface border border-default rounded-modal p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <!-- SSO providers -->
      <div v-if="ssoProviders.length" class="flex flex-col gap-2">
        <a
          v-for="provider in ssoProviders"
          :key="provider.slug"
          :href="ssoLoginUrl(provider.slug, redirectTarget)"
          class="w-full py-2.5 px-4 rounded-card border border-strong text-sm font-medium text-content-muted bg-surface hover:bg-surface-muted transition flex items-center justify-center gap-2"
        >
          <LogIn class="h-4 w-4" aria-hidden="true" />
          {{ $t('auth.login.continue_with', { name: provider.name }) }}
        </a>
        <div class="flex items-center gap-3 my-1">
          <div class="h-px flex-1 bg-default-border" />
          <span class="text-xs text-content-subtle">{{ $t('auth.login.or') }}</span>
          <div class="h-px flex-1 bg-default-border" />
        </div>
      </div>

      <FormField
        v-model="email"
        :label="$t('auth.form.email')"
        type="email"
        required
        maxlength="254"
        :placeholder="$t('auth.form.email_placeholder')"
        autocomplete="email"
        :spellcheck="false"
        data-testid="login-email"
      />
      <FormField
        v-model="password"
        :label="$t('auth.form.password')"
        type="password"
        required
        :placeholder="$t('auth.form.password_placeholder')"
        autocomplete="current-password"
        data-testid="login-password"
      >
        <template #trailing>
          <router-link to="/forgot-password" class="text-xs text-primary hover:underline">
            {{ $t('auth.login.forgot_password') }}
          </router-link>
        </template>
      </FormField>
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading"
        data-testid="login-submit"
        class="w-full py-2.5"
      >
        <Lock v-if="!isLoading" class="h-5 w-5" aria-hidden="true" />
        <span>{{ isLoading ? $t('auth.login.signing_in') : $t('auth.login.sign_in') }}</span>
      </BaseButton>
      <transition name="fade">
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
      <router-link
        to="/register"
        class="block mt-3 text-center text-primary hover:underline text-sm transition"
      >
        {{ $t('auth.login.no_account') }}
        <span class="font-semibold">{{ $t('auth.login.register_here') }}</span>
      </router-link>
    </form>
  </div>
</template>

<script setup lang="ts">
import AppBrand from '@/components/common/AppBrand.vue'
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import { Lock, LogIn } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/authApi'
import { ssoLoginUrl } from '@/services/ssoApi'
import { useToast } from '@/composables/useToast'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { extractErrorMessage } from '@/utils/errors'
import type { SsoProviderPublic } from '@/types'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const toast = useToast()
const firstAdminStore = useFirstAdminStore()

const email = ref<string>('')
const password = ref<string>('')
const isLoading = ref<boolean>(false)
const error = ref<string | null>(null)
const ssoProviders = ref<SsoProviderPublic[]>([])
const redirectTarget = ref<string>('/projects')

onMounted(async () => {
  // If first-admin flow is needed, redirect to it (extra safe)
  if (!firstAdminStore.checked) {
    await firstAdminStore.checkFirstAdmin()
  }
  if (firstAdminStore.needsFirstAdmin) {
    router.replace('/first-admin')
    return
  }
  // Preserve the intended destination for post-login redirect (and SSO).
  if (route.query.redirect) {
    redirectTarget.value = String(route.query.redirect)
  }
  // Load SSO providers advertised by the backend.
  try {
    const res = await authApi.getSettings()
    ssoProviders.value = res.data.sso_providers || []
  } catch {
    ssoProviders.value = []
  }
})

async function handleSubmit(): Promise<void> {
  if (isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const response = await authApi.login(formData.toString())

    await authStore.setSession(response.data.access_token, response.data.refresh_token)
    router.push(redirectTarget.value || '/projects')
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    let message: string
    if (status === 401) {
      // Deliberately generic to avoid account enumeration.
      message = t('auth.errors.invalid_credentials')
    } else if (status) {
      // Lockout (423), rate limit (429), etc. — surface the backend's message.
      message = extractErrorMessage(err, t('auth.errors.sign_in_failed'))
    } else {
      message = t('auth.errors.server_unreachable')
    }
    error.value = message
    toast.error(message, {
      timeout: 3500,
    })
    console.error('Login error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
