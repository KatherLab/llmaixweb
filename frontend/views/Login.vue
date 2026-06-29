<template>
  <div class="w-full max-w-md">
    <div class="mb-8 text-center">
      <h1 class="text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
        LLMAIx-v2
      </h1>
      <p class="text-base text-slate-500 dark:text-slate-400 mt-2">
        Extract information from documents using LLMs.
      </p>
    </div>
    <form
      class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-8 shadow-sm flex flex-col gap-5"
      autocomplete="on"
      @submit.prevent="handleSubmit"
    >
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
      <FormField
        v-model="password"
        label="Password"
        type="password"
        required
        placeholder="Password"
        autocomplete="current-password"
      >
        <template #trailing>
          <router-link to="/forgot-password" class="text-xs text-blue-600 hover:underline">
            Forgot your password?
          </router-link>
        </template>
      </FormField>
      <BaseButton
        type="submit"
        size="lg"
        :loading="isLoading"
        :disabled="isLoading"
        class="w-full py-2.5"
      >
        <Lock v-if="!isLoading" class="h-5 w-5" aria-hidden="true" />
        <span>{{ isLoading ? 'Signing in...' : 'Sign in' }}</span>
      </BaseButton>
      <transition name="fade">
        <ErrorBanner v-if="error" :message="error" class="text-center" />
      </transition>
      <router-link
        to="/register"
        class="block mt-3 text-center text-blue-600 hover:underline text-sm transition"
      >
        Don’t have an account? <span class="font-semibold">Register here</span>
      </router-link>
    </form>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Lock } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
import { useFirstAdminStore } from '@/stores/firstAdmin'
import BaseButton from '@/components/common/BaseButton.vue'
import FormField from '@/components/common/FormField.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()
const firstAdminStore = useFirstAdminStore()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref(null)

onMounted(async () => {
  // If first-admin flow is needed, redirect to it (extra safe)
  if (!firstAdminStore.checked) {
    await firstAdminStore.checkFirstAdmin()
  }
  if (firstAdminStore.needsFirstAdmin) {
    router.replace('/first-admin')
  }
})

async function handleSubmit() {
  if (isLoading.value) return
  isLoading.value = true
  error.value = null

  try {
    const formData = new URLSearchParams()
    formData.append('username', email.value)
    formData.append('password', password.value)

    const response = await authApi.login(formData.toString())

    await authStore.setToken(response.data.access_token)
    await authStore.fetchUser()
    router.push(authStore.isAdmin ? '/' : '/')
  } catch (err) {
    error.value = 'Invalid email or password'
    toast.error('Invalid email or password', {
      timeout: 3500,
    })
    console.error('Login error:', err)
  } finally {
    isLoading.value = false
  }
}
</script>
