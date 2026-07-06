<template>
  <div class="w-full max-w-md">
    <div v-if="loading" class="flex flex-col items-center justify-center py-16">
      <LoadingSpinner size="large" />
      <p class="mt-4 text-slate-500 dark:text-slate-400">Verifying your invitation...</p>
    </div>

    <div
      v-else-if="error"
      class="bg-white dark:bg-slate-800 border border-red-200 dark:border-red-900 rounded-modal p-8 text-center shadow-sm"
    >
      <TriangleAlert class="mx-auto h-12 w-12 text-red-500 dark:text-red-400" />
      <h3 class="mt-4 text-lg font-semibold text-red-800 dark:text-red-300">Invalid invitation</h3>
      <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
        {{ error }}
      </p>
      <div class="mt-6">
        <router-link
          to="/login"
          class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
        >
          Go to login page
        </router-link>
      </div>
    </div>

    <div
      v-else
      class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-modal p-8 shadow-sm text-center"
    >
      <div
        class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 dark:bg-green-900/30"
      >
        <Check class="h-10 w-10 text-green-600 dark:text-green-400" />
      </div>
      <h3 class="mt-4 text-lg font-medium text-slate-900 dark:text-slate-100">Valid invitation</h3>
      <p v-if="invitedEmail" class="mt-2 text-sm text-slate-500 dark:text-slate-400">
        This invitation was sent to <span class="font-medium">{{ invitedEmail }}</span>
      </p>
      <div class="mt-6">
        <BaseButton variant="primary" class="w-full" @click="goToRegister">
          Create your account
        </BaseButton>
        <div class="mt-4 text-center">
          <router-link
            to="/login"
            class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
          >
            Already have an account? Sign in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { TriangleAlert, Check } from '@lucide/vue'
import { useRoute, useRouter } from 'vue-router'
import { usersApi } from '@/services/usersApi'
import { useToast } from '@/composables/useToast'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const loading = ref<boolean>(true)
const error = ref<string | null>(null)
const invitedEmail = ref<string>('')
const token = ref<string>('')

onMounted(async () => {
  token.value = String(route.params.token ?? '')

  if (!token.value) {
    error.value = 'No invitation token provided'
    loading.value = false
    return
  }

  await validateInvitation()
})

async function validateInvitation(): Promise<void> {
  try {
    const response = await usersApi.validateInvitation(token.value)

    if (!response.data || !response.data.valid) {
      error.value = 'This invitation is invalid or has already been used'
      toast.error(error.value)
    } else {
      invitedEmail.value = response.data.email ?? ''
    }
  } catch (err) {
    error.value = 'This invitation link is invalid or has expired'
    toast.error(error.value)
    console.error('Error validating invitation:', err)
  } finally {
    loading.value = false
  }
}

function goToRegister(): void {
  router.push({
    path: '/register',
    query: {
      token: token.value,
      ...(invitedEmail.value ? { email: invitedEmail.value } : {}),
    },
  })
}
</script>
