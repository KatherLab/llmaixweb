<template>
  <BaseModal
    :open="open"
    size="sm"
    panel-class="dark:bg-slate-900 dark:border-slate-700"
    :close-on-backdrop="!isInviting"
    @close="emit('close')"
  >
    <template #header>
      <h3 class="text-lg font-bold text-gray-900 dark:text-white">Invite New User</h3>
    </template>
    <form @submit.prevent="sendInvitation">
      <div class="mb-5">
        <label for="email" class="block text-xs font-bold text-gray-600 dark:text-slate-300 mb-1"
          >Email address</label
        >
        <input
          id="email"
          v-model="inviteEmail"
          type="email"
          required
          class="block w-full px-4 py-2 text-sm border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-400"
          placeholder="Enter email address"
        />
      </div>
      <div class="mb-5">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="sendInviteEmail"
            type="checkbox"
            class="rounded border-gray-300 dark:border-slate-600 text-blue-600 dark:text-blue-400"
          />
          <span class="text-sm text-gray-700 dark:text-slate-300">Send invitation via email</span>
        </label>
      </div>
      <div
        v-if="inviteError"
        class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded-md"
      >
        {{ inviteError }}
      </div>
      <div v-if="inviteSuccess" class="mb-4">
        <div
          class="p-3 text-xs rounded-md mb-2"
          :class="
            inviteEmailSent
              ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
              : 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
          "
        >
          <template v-if="inviteEmailSent"> Invitation sent to email successfully! </template>
          <template v-else>
            Invitation created but email delivery is not configured. Copy the link manually.
          </template>
        </div>
        <div class="flex items-center mt-2 gap-2">
          <input
            type="text"
            readonly
            :value="invitationLink"
            class="block w-full px-4 py-2 text-xs border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg pr-10"
          />
          <button
            type="button"
            class="p-1.5 rounded-lg border border-gray-200 dark:border-slate-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-slate-800 transition-all relative"
            @click="copyGeneratedLink"
          >
            <span
              v-if="copySuccess"
              class="absolute bg-gray-800 dark:bg-slate-700 text-white text-xs px-2 py-1 rounded -top-8 left-1/2 -translate-x-1/2 z-10"
            >
              Copied!
            </span>
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
              />
            </svg>
          </button>
        </div>
      </div>
      <div class="mt-7 flex justify-end gap-2">
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-slate-700 transition"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button
          type="submit"
          :disabled="isInviting"
          class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 dark:bg-blue-500 rounded-lg shadow-sm hover:bg-blue-700 dark:hover:bg-blue-600 transition disabled:opacity-50"
        >
          {{ isInviting ? 'Sending...' : 'Send Invitation' }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { usersApi } from '@/services/usersApi'

const props = defineProps({
  open: { type: Boolean, required: true },
})

const emit = defineEmits(['close', 'invited'])

const inviteEmail = ref('')
const isInviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref(false)
const inviteEmailSent = ref(false)
const sendInviteEmail = ref(false)
const invitationLink = ref('')
const copySuccess = ref(false)

// Reset all internal state when the modal closes.
watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      inviteEmail.value = ''
      sendInviteEmail.value = false
      inviteError.value = ''
      inviteSuccess.value = false
      inviteEmailSent.value = false
      invitationLink.value = ''
      copySuccess.value = false
    }
  },
)

async function sendInvitation() {
  if (!inviteEmail.value) return
  isInviting.value = true
  inviteError.value = ''
  inviteSuccess.value = false
  inviteEmailSent.value = false
  try {
    const formData = new URLSearchParams()
    formData.append('email', inviteEmail.value)
    formData.append('send_email', sendInviteEmail.value ? 'true' : 'false')
    const response = await usersApi.invite(formData.toString())
    const baseUrl = window.location.origin
    invitationLink.value = `${baseUrl}/register?token=${response.data.token}`
    inviteEmailSent.value = response.data.email_sent || false
    inviteSuccess.value = true
    emit('invited')
  } catch (error) {
    if (error.response?.data?.detail) {
      inviteError.value = error.response.data.detail
    } else if (error.response?.data) {
      const validationError = error.response.data[0]
      inviteError.value = validationError?.msg || 'Failed to send invitation.'
    } else {
      inviteError.value = 'Failed to send invitation. Please try again.'
    }
  } finally {
    isInviting.value = false
  }
}

function copyGeneratedLink() {
  const copyTextFallback = (text) => {
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    let success = false
    try {
      success = document.execCommand('copy')
    } catch {
      /* ignore */
    }
    document.body.removeChild(textArea)
    return success
  }
  const baseUrl = window.location.origin
  const token = invitationLink.value.split('token=')[1]
  const link = `${baseUrl}/register?token=${token}`
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard
      .writeText(link)
      .then(() => {
        copySuccess.value = true
        setTimeout(() => {
          copySuccess.value = false
        }, 2000)
      })
      .catch(() => {
        const success = copyTextFallback(link)
        if (success) {
          copySuccess.value = true
          setTimeout(() => {
            copySuccess.value = false
          }, 2000)
        } else {
          alert(`Failed to copy. Please copy this link manually:\n${link}`)
        }
      })
  } else {
    const success = copyTextFallback(link)
    if (success) {
      copySuccess.value = true
      setTimeout(() => {
        copySuccess.value = false
      }, 2000)
    } else {
      alert(`Failed to copy. Please copy this link manually:\n${link}`)
    }
  }
}
</script>
