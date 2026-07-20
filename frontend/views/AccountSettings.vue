<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-4">
    <PageHeader
      :title="$t('account.title')"
      :subtitle="$t('account.subtitle')"
      max-width="3xl"
      class="mb-6"
    />

    <div class="space-y-6">
      <!-- Profile -->
      <GlassCard>
        <div class="p-6">
          <h2 class="text-base font-semibold text-content mb-4">
            {{ $t('account.profile.title') }}
          </h2>
          <div class="space-y-4">
            <FormField
              v-model="profileForm.full_name"
              :label="$t('account.profile.full_name')"
              type="text"
              :placeholder="$t('account.profile.full_name_placeholder')"
            />
            <FormField
              v-model="profileForm.email"
              :label="$t('account.profile.email')"
              type="email"
              maxlength="254"
              :placeholder="$t('account.profile.email_placeholder')"
            />
            <div class="flex items-center gap-3">
              <BaseButton
                variant="primary"
                :disabled="!profileDirty || savingProfile"
                :loading="savingProfile"
                @click="saveProfile"
              >
                {{ $t('account.profile.save') }}
              </BaseButton>
              <p v-if="profileSaved" class="text-xs text-green-600 dark:text-green-400">
                {{ $t('account.profile.saved') }}
              </p>
            </div>
          </div>
        </div>
      </GlassCard>

      <!-- Change password -->
      <GlassCard>
        <div class="p-6">
          <h2 class="text-base font-semibold text-content mb-1">
            {{ $t('common.change_password') }}
          </h2>
          <p class="text-xs text-content-subtle mb-4">
            {{ $t('account.password.hint') }}
          </p>
          <div class="space-y-4 max-w-md">
            <FormField
              v-model="passwordForm.old_password"
              :label="$t('account.password.current')"
              type="password"
              autocomplete="current-password"
              :placeholder="$t('account.password.current_placeholder')"
            />
            <PasswordInput
              v-model="passwordForm.new_password"
              :label="$t('account.password.new')"
              autocomplete="new-password"
              :placeholder="$t('account.password.new_placeholder')"
            />
            <FormField
              v-model="passwordForm.confirm"
              :label="$t('account.password.confirm')"
              type="password"
              autocomplete="new-password"
              :placeholder="$t('account.password.confirm_placeholder')"
              :invalid="
                !!passwordForm.confirm && passwordForm.confirm !== passwordForm.new_password
              "
            >
              <template
                v-if="!!passwordForm.confirm && passwordForm.confirm !== passwordForm.new_password"
                #error
              >
                {{ $t('account.password.mismatch') }}
              </template>
            </FormField>
            <div class="flex items-center gap-3">
              <BaseButton
                variant="primary"
                :disabled="!canChangePassword || savingPassword"
                :loading="savingPassword"
                @click="changePassword"
              >
                {{ $t('account.password.update') }}
              </BaseButton>
            </div>
            <p v-if="passwordError" class="text-xs text-red-600 dark:text-red-400">
              {{ passwordError }}
            </p>
            <p v-if="passwordSaved" class="text-xs text-green-600 dark:text-green-400">
              {{ $t('account.password.updated_notice') }}
            </p>
          </div>
        </div>
      </GlassCard>

      <!-- Connected accounts (SSO) -->
      <GlassCard v-if="ssoEnabled !== false">
        <div class="p-6">
          <h2 class="text-base font-semibold text-content mb-1">
            {{ $t('account.connected.title') }}
          </h2>
          <p class="text-xs text-content-subtle mb-4">
            {{ $t('account.connected.subtitle') }}
          </p>
          <div v-if="loadingIdentities" class="flex justify-center py-6">
            <LoadingSpinner size="medium" />
          </div>
          <div v-else-if="identities.length === 0" class="text-sm text-content-subtle">
            {{ $t('account.connected.empty') }}
          </div>
          <ul v-else class="divide-y divide-default">
            <li
              v-for="ident in identities"
              :key="ident.id"
              class="flex items-center justify-between py-3"
            >
              <div>
                <p class="text-sm font-medium text-content">
                  {{ ident.provider_name }}
                </p>
                <p class="text-xs text-content-subtle">
                  {{ ident.external_subject }}
                  <span v-if="ident.last_login_at">
                    {{
                      $t('account.connected.last_login', { date: formatDate(ident.last_login_at) })
                    }}</span
                  >
                </p>
              </div>
              <BaseButton
                variant="secondary"
                size="sm"
                tone="red"
                :disabled="disconnectingId === ident.id"
                @click="disconnectIdentity(ident)"
              >
                {{ disconnectingId === ident.id ? '...' : $t('account.connected.disconnect') }}
              </BaseButton>
            </li>
          </ul>
        </div>
      </GlassCard>

      <!-- Sign out -->
      <GlassCard>
        <div class="p-6 flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-content">{{ $t('account.signout.title') }}</h2>
            <p class="text-xs text-content-subtle mt-1">
              {{ $t('account.signout.subtitle') }}
            </p>
          </div>
          <div class="flex gap-2">
            <BaseButton variant="secondary" :loading="signingOut" @click="signOut(false)">
              {{ $t('account.signout.button') }}
            </BaseButton>
            <BaseButton variant="secondary" tone="red" :loading="signingOut" @click="signOut(true)">
              {{ $t('account.signout.everywhere') }}
            </BaseButton>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import { formatDate } from '@/utils/formatters'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import GlassCard from '@/components/common/GlassCard.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import type { UserIdentityResponse } from '@/types'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

// ── Profile ──
const profileForm = reactive<{ full_name: string; email: string }>({
  full_name: '',
  email: '',
})
const savingProfile = ref<boolean>(false)
const profileSaved = ref<boolean>(false)
const profileDirty = computed<boolean>(
  () =>
    profileForm.full_name !== authStore.user?.full_name ||
    profileForm.email !== authStore.user?.email,
)

// ── Password ──
const passwordForm = reactive<{ old_password: string; new_password: string; confirm: string }>({
  old_password: '',
  new_password: '',
  confirm: '',
})
const savingPassword = ref<boolean>(false)
const passwordError = ref<string>('')
const passwordSaved = ref<boolean>(false)
const canChangePassword = computed<boolean>(
  () =>
    !!passwordForm.old_password &&
    passwordForm.new_password.length >= 8 &&
    passwordForm.new_password === passwordForm.confirm,
)

// ── Identities ──
const ssoEnabled = ref<boolean | null>(null)
const identities = ref<UserIdentityResponse[]>([])
const loadingIdentities = ref<boolean>(false)
const disconnectingId = ref<number | null>(null)

// ── Sign out ──
const signingOut = ref<boolean>(false)

onMounted(async () => {
  if (authStore.user) {
    profileForm.full_name = authStore.user.full_name
    profileForm.email = authStore.user.email
  }
  try {
    const res = await authApi.getSettings()
    ssoEnabled.value = res.data.sso_enabled
    if (res.data.sso_enabled) {
      await loadIdentities()
    }
  } catch {
    ssoEnabled.value = false
  }
})

async function loadIdentities(): Promise<void> {
  loadingIdentities.value = true
  try {
    const res = await usersApi.listMyIdentities()
    identities.value = res.data
  } catch {
    /* non-fatal */
  } finally {
    loadingIdentities.value = false
  }
}

async function saveProfile(): Promise<void> {
  if (!profileDirty.value) return
  savingProfile.value = true
  profileSaved.value = false
  try {
    const payload: { full_name?: string; email?: string } = {}
    if (profileForm.full_name !== authStore.user!.full_name)
      payload.full_name = profileForm.full_name
    if (profileForm.email !== authStore.user!.email) payload.email = profileForm.email
    const res = await usersApi.update(authStore.user!.id, payload)
    authStore.user = res.data
    profileSaved.value = true
    toast.success(t('account.toasts.profile_updated'))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('account.errors.profile_update_failed')))
  } finally {
    savingProfile.value = false
  }
}

async function changePassword(): Promise<void> {
  if (!canChangePassword.value) return
  savingPassword.value = true
  passwordError.value = ''
  passwordSaved.value = false
  try {
    await usersApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    passwordSaved.value = true
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm = ''
    toast.success(t('account.toasts.password_updated'))
  } catch (e) {
    passwordError.value = extractErrorMessage(e, t('account.errors.password_update_failed'))
  } finally {
    savingPassword.value = false
  }
}

async function disconnectIdentity(ident: UserIdentityResponse): Promise<void> {
  disconnectingId.value = ident.id
  try {
    await usersApi.deleteMyIdentity(ident.id)
    identities.value = identities.value.filter((i) => i.id !== ident.id)
    toast.success(t('account.toasts.disconnected', { name: ident.provider_name }))
  } catch (e) {
    toast.error(extractErrorMessage(e, t('account.errors.disconnect_failed')))
  } finally {
    disconnectingId.value = null
  }
}

async function signOut(everywhere: boolean): Promise<void> {
  signingOut.value = true
  try {
    await authStore.logout({ serverSide: true, everywhere })
    toast.success(t('account.toasts.signed_out'))
    router.push('/login')
  } finally {
    signingOut.value = false
  }
}
</script>
