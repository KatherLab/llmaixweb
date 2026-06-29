<template>
  <div class="w-full max-w-md">
    <div v-if="loading" class="flex flex-col items-center justify-center py-16">
      <LoadingSpinner size="large" />
      <p class="mt-4 text-slate-500">Verifying your invitation...</p>
    </div>

    <div
      v-else-if="error"
      class="bg-white border border-red-200 rounded-xl p-8 text-center shadow-sm"
    >
      <TriangleAlert class="mx-auto h-12 w-12 text-red-500" />
      <h3 class="mt-4 text-lg font-semibold text-red-800">Invalid invitation</h3>
      <p class="mt-2 text-sm text-slate-500">
        {{ error }}
      </p>
      <div class="mt-6">
        <router-link to="/login" class="text-sm font-medium text-blue-600 hover:underline">
          Go to login page
        </router-link>
      </div>
    </div>

    <div v-else class="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">
      <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100">
        <Check class="h-10 w-10 text-green-600" />
      </div>
      <h3 class="mt-4 text-lg font-medium text-slate-900">Valid invitation</h3>
      <p v-if="invitedEmail" class="mt-2 text-sm text-slate-500">
        This invitation was sent to <span class="font-medium">{{ invitedEmail }}</span>
      </p>
      <div class="mt-6">
        <BaseButton variant="primary" class="w-full" @click="goToRegister">
          Create your account
        </BaseButton>
        <div class="mt-4 text-center">
          <router-link to="/login" class="text-sm font-medium text-blue-600 hover:underline">
            Already have an account? Sign in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { TriangleAlert, Check } from '@lucide/vue'
import { useRoute, useRouter } from 'vue-router'
import { usersApi } from '@/services/usersApi'
import { useToast } from 'vue-toastification'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const loading = ref(true)
const error = ref(null)
const invitedEmail = ref('')
const token = ref('')

onMounted(async () => {
  token.value = route.params.token

  if (!token.value) {
    error.value = 'No invitation token provided'
    loading.value = false
    return
  }

  await validateInvitation()
})

async function validateInvitation() {
  try {
    const response = await usersApi.validateInvitation(token.value)

    if (!response.data || !response.data.valid) {
      error.value = 'This invitation is invalid or has already been used'
      toast.error(error.value)
    } else {
      invitedEmail.value = response.data.email
    }
  } catch (err) {
    error.value = 'This invitation link is invalid or has expired'
    toast.error(error.value)
    console.error('Error validating invitation:', err)
  } finally {
    loading.value = false
  }
}

function goToRegister() {
  router.push({
    path: '/register',
    query: {
      token: token.value,
      ...(invitedEmail.value ? { email: invitedEmail.value } : {}),
    },
  })
}
</script>
