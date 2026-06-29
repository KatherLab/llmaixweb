<template>
  <div class="w-full max-w-md mx-auto py-10">
    <div class="mb-8 text-center">
      <div class="flex justify-center mb-2">
        <CircleUser class="w-14 h-14 text-blue-700 dark:text-blue-400" aria-hidden="true" />
      </div>
      <h1 class="text-3xl font-extrabold text-blue-700 dark:text-blue-400 mb-1">
        Welcome to LLMAIx-v2
      </h1>
      <p class="text-base text-slate-500 dark:text-slate-400">
        First-time setup: Create your admin account
      </p>
    </div>
    <form
      class="bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded-xl p-8 shadow-lg flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
      <FormField
        v-model="fullName"
        label="Full Name"
        type="text"
        required
        placeholder="Full name"
      />
      <FormField
        v-model="email"
        label="Email address"
        type="email"
        required
        placeholder="admin@yourcompany.com"
      />
      <FormField
        v-model="password"
        label="Password"
        type="password"
        required
        placeholder="Password"
      />
      <FormField
        v-model="confirmPassword"
        label="Confirm Password"
        type="password"
        required
        placeholder="Confirm password"
      />
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading || !isFormValid"
        class="w-full py-2.5"
      >
        {{ isLoading ? 'Creating admin...' : 'Create Admin Account' }}
      </BaseButton>
      <transition name="fade">
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
    </form>
    <div class="text-center text-slate-400 dark:text-slate-500 text-xs mt-8">
      Powered by LLMAIx (v2)
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { CircleUser } from '@lucide/vue'
import { authApi } from '@/services/authApi'
import { usersApi } from '@/services/usersApi'
import { useAuthStore } from '@/stores/auth'
import { useToast } from 'vue-toastification'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { extractErrorMessage } from '@/utils/errors'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref(null)

const isFormValid = computed(
  () =>
    fullName.value.length >= 2 &&
    email.value.includes('@') &&
    password.value.length >= 8 &&
    password.value === confirmPassword.value,
)

async function handleSubmit() {
  if (!isFormValid.value || isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    await usersApi.createFirstAdmin({
      full_name: fullName.value,
      email: email.value,
      password: password.value,
      role: 'admin',
    })
    // Auto-login
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)
    const resp = await authApi.login(formData.toString())
    await authStore.setToken(resp.data.access_token)
    await authStore.fetchUser()
    // --- Re-check first-admin state (to update Pinia) ---
    const firstAdminStore = useFirstAdminStore()
    await firstAdminStore.checkFirstAdmin()

    // --- Only then, route away
    toast.success('Admin account created! Welcome 👋')
    router.push('/')
  } catch (err) {
    error.value = extractErrorMessage(err, 'Failed to create admin. Try again.')
    toast.error(error.value)
  } finally {
    isLoading.value = false
  }
}
</script>
