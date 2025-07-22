<template>
  <div class="w-full max-w-md">
    <div v-if="loading" class="flex flex-col items-center justify-center py-16">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
      <p class="mt-4 text-gray-500">Verifying your invitation...</p>
    </div>

    <div v-else-if="error" class="bg-white border border-red-200 rounded-xl p-8 text-center shadow-sm">
      <svg class="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <h3 class="mt-4 text-lg font-semibold text-red-800">Invalid invitation</h3>
      <p class="mt-2 text-sm text-gray-500">
        {{ error }}
      </p>
      <div class="mt-6">
        <router-link to="/login" class="text-sm font-medium text-blue-600 hover:underline">
          Go to login page
        </router-link>
      </div>
    </div>

    <div v-else class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm text-center">
      <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100">
        <svg class="h-10 w-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h3 class="mt-4 text-lg font-medium text-gray-900">Valid invitation</h3>
      <p v-if="invitedEmail" class="mt-2 text-sm text-gray-500">
        This invitation was sent to <span class="font-medium">{{ invitedEmail }}</span>
      </p>
      <div class="mt-6">
        <button
          @click="goToRegister"
          class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Create your account
        </button>
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
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'

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
    const response = await api.get(`/user/validate-invitation/${token.value}`)

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
      ...(invitedEmail.value ? { email: invitedEmail.value } : {})
    }
  })
}
</script>
