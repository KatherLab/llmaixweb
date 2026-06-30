<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Account settings</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
        Manage your profile, password, and connected sign-in methods.
      </p>
    </div>

    <div class="space-y-6">
      <!-- Profile -->
      <GlassCard>
        <div class="p-6">
          <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-4">Profile</h2>
          <div class="space-y-4">
            <div>
              <label :class="labelClass">Full Name</label>
              <input v-model="profileForm.full_name" type="text" :class="inputClass" />
            </div>
            <div>
              <label :class="labelClass">Email</label>
              <input v-model="profileForm.email" type="email" :class="inputClass" maxlength="254" />
            </div>
            <div class="flex items-center gap-3">
              <BaseButton
                variant="primary"
                :disabled="!profileDirty || savingProfile"
                :loading="savingProfile"
                @click="saveProfile"
              >
                Save profile
              </BaseButton>
              <p v-if="profileSaved" class="text-xs text-green-600 dark:text-green-400">Saved.</p>
            </div>
          </div>
        </div>
      </GlassCard>

      <!-- Change password -->
      <GlassCard>
        <div class="p-6">
          <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-1">
            Change password
          </h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Leave blank if you sign in exclusively via SSO — you can still set a password as a
            fallback.
          </p>
          <div class="space-y-4 max-w-md">
            <FormField
              v-model="passwordForm.old_password"
              label="Current password"
              type="password"
              autocomplete="current-password"
              placeholder="Your current password"
            />
            <PasswordInput
              v-model="passwordForm.new_password"
              label="New password"
              autocomplete="new-password"
              placeholder="New password"
            />
            <FormField
              v-model="passwordForm.confirm"
              label="Confirm new password"
              type="password"
              autocomplete="new-password"
              placeholder="Repeat new password"
              :invalid="
                !!passwordForm.confirm && passwordForm.confirm !== passwordForm.new_password
              "
            >
              <template
                v-if="!!passwordForm.confirm && passwordForm.confirm !== passwordForm.new_password"
                #error
              >
                Passwords do not match
              </template>
            </FormField>
            <div class="flex items-center gap-3">
              <BaseButton
                variant="primary"
                :disabled="!canChangePassword || savingPassword"
                :loading="savingPassword"
                @click="changePassword"
              >
                Update password
              </BaseButton>
            </div>
            <p v-if="passwordError" class="text-xs text-red-600 dark:text-red-400">
              {{ passwordError }}
            </p>
            <p v-if="passwordSaved" class="text-xs text-green-600 dark:text-green-400">
              Password updated. Other sessions were signed out.
            </p>
          </div>
        </div>
      </GlassCard>

      <!-- Connected accounts (SSO) -->
      <GlassCard v-if="ssoEnabled !== false">
        <div class="p-6">
          <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-1">
            Connected accounts
          </h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">
            External identity providers linked to your account.
          </p>
          <div v-if="loadingIdentities" class="flex justify-center py-6">
            <LoadingSpinner size="medium" />
          </div>
          <div
            v-else-if="identities.length === 0"
            class="text-sm text-slate-500 dark:text-slate-400"
          >
            No external accounts connected.
          </div>
          <ul v-else class="divide-y divide-slate-200 dark:divide-slate-700">
            <li
              v-for="ident in identities"
              :key="ident.id"
              class="flex items-center justify-between py-3"
            >
              <div>
                <p class="text-sm font-medium text-slate-900 dark:text-white">
                  {{ ident.provider_name }}
                </p>
                <p class="text-xs text-slate-500 dark:text-slate-400">
                  {{ ident.external_subject }}
                  <span v-if="ident.last_login_at">
                    · last login {{ formatDate(ident.last_login_at) }}</span
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
                {{ disconnectingId === ident.id ? '...' : 'Disconnect' }}
              </BaseButton>
            </li>
          </ul>
        </div>
      </GlassCard>

      <!-- Sign out -->
      <GlassCard>
        <div class="p-6 flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-slate-900 dark:text-white">Sign out</h2>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Sign out of this device, or all sessions.
            </p>
          </div>
          <div class="flex gap-2">
            <BaseButton variant="secondary" :loading="signingOut" @click="signOut(false)">
              Sign out
            </BaseButton>
            <BaseButton variant="secondary" tone="red" :loading="signingOut" @click="signOut(true)">
              Sign out everywhere
            </BaseButton>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, labelClass } from '@/utils/formStyles'
import { formatDate } from '@/utils/formatters'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import PasswordInput from '@/components/common/PasswordInput.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import GlassCard from '@/components/common/GlassCard.vue'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

// ── Profile ──
const profileForm = reactive({ full_name: '', email: '' })
const savingProfile = ref(false)
const profileSaved = ref(false)
const profileDirty = computed(
  () =>
    profileForm.full_name !== authStore.user?.full_name ||
    profileForm.email !== authStore.user?.email,
)

// ── Password ──
const passwordForm = reactive({ old_password: '', new_password: '', confirm: '' })
const savingPassword = ref(false)
const passwordError = ref('')
const passwordSaved = ref(false)
const canChangePassword = computed(
  () =>
    passwordForm.old_password &&
    passwordForm.new_password.length >= 8 &&
    passwordForm.new_password === passwordForm.confirm,
)

// ── Identities ──
const ssoEnabled = ref(null)
const identities = ref([])
const loadingIdentities = ref(false)
const disconnectingId = ref(null)

// ── Sign out ──
const signingOut = ref(false)

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
  } catch (e) {
    ssoEnabled.value = false
  }
})

async function loadIdentities() {
  loadingIdentities.value = true
  try {
    const res = await usersApi.listMyIdentities()
    identities.value = res.data
  } catch (e) {
    /* non-fatal */
  } finally {
    loadingIdentities.value = false
  }
}

async function saveProfile() {
  if (!profileDirty.value) return
  savingProfile.value = true
  profileSaved.value = false
  try {
    const payload = {}
    if (profileForm.full_name !== authStore.user.full_name)
      payload.full_name = profileForm.full_name
    if (profileForm.email !== authStore.user.email) payload.email = profileForm.email
    const res = await usersApi.update(authStore.user.id, payload)
    authStore.user = res.data
    profileSaved.value = true
    toast.success('Profile updated.')
  } catch (e) {
    toast.error(extractErrorMessage(e, 'Failed to update profile.'))
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
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
    toast.success('Password updated.')
  } catch (e) {
    passwordError.value = extractErrorMessage(e, 'Failed to update password.')
  } finally {
    savingPassword.value = false
  }
}

async function disconnectIdentity(ident) {
  disconnectingId.value = ident.id
  try {
    await usersApi.deleteMyIdentity(ident.id)
    identities.value = identities.value.filter((i) => i.id !== ident.id)
    toast.success(`Disconnected ${ident.provider_name}.`)
  } catch (e) {
    toast.error(extractErrorMessage(e, 'Failed to disconnect.'))
  } finally {
    disconnectingId.value = null
  }
}

async function signOut(everywhere) {
  signingOut.value = true
  try {
    await authStore.logout({ serverSide: true, everywhere })
    toast.success('Signed out.')
    router.push('/login')
  } finally {
    signingOut.value = false
  }
}
</script>
