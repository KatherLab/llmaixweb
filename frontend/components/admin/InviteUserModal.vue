<template>
  <BaseModal :open="open" size="sm" :close-on-backdrop="!isInviting" @close="emit('close')">
    <template #header>
      <h3 class="text-lg font-semibold text-content">{{ $t('admin.invite_modal.title') }}</h3>
    </template>
    <form @submit.prevent="sendInvitation">
      <div class="mb-5">
        <label for="email" :class="labelClass">{{ $t('admin.invite_modal.email_label') }}</label>
        <input
          id="email"
          v-model="inviteEmail"
          type="email"
          required
          :class="inputClass"
          maxlength="254"
          :placeholder="$t('admin.invite_modal.email_placeholder')"
        />
      </div>
      <div class="mb-5">
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="sendInviteEmail" type="checkbox" :class="checkboxClass" />
          <span class="text-sm text-content-muted">{{
            $t('admin.invite_modal.send_via_email')
          }}</span>
        </label>
      </div>
      <Callout v-if="inviteError" variant="danger" class="mb-4 text-xs">
        {{ inviteError }}
      </Callout>
      <div v-if="inviteSuccess" class="mb-4">
        <Callout class="mb-2 text-xs" :variant="inviteEmailSent ? 'success' : 'warning'">
          <template v-if="inviteEmailSent">
            {{ $t('admin.invite_modal.sent_success') }}
          </template>
          <template v-else>
            {{ $t('admin.invite_modal.created_no_email') }}
          </template>
        </Callout>
        <div class="flex items-center mt-2 gap-2">
          <input
            type="text"
            readonly
            :value="invitationLink"
            :class="[inputClass, 'text-xs pr-10']"
          />
          <button
            type="button"
            :aria-label="$t('admin.invite_modal.copy_link')"
            class="p-1.5 rounded-card border border-default text-primary hover:bg-primary-soft transition-all relative"
            @click="copyGeneratedLink"
          >
            <span
              v-if="copySuccess"
              class="absolute bg-surface text-white text-xs px-2 py-1 rounded -top-8 left-1/2 -translate-x-1/2 z-10"
            >
              {{ $t('admin.invite_modal.copied') }}
            </span>
            <ClipboardCopy class="h-4 w-4" />
          </button>
        </div>
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="isInviting" @click="emit('close')">
        {{ $t('admin.invite_modal.cancel') }}
      </BaseButton>
      <BaseButton
        variant="primary"
        :loading="isInviting"
        :disabled="isInviting"
        @click="sendInvitation"
      >
        {{ isInviting ? $t('admin.invite_modal.sending') : $t('admin.invite_modal.send') }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ClipboardCopy } from '@lucide/vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import { useToast } from '@/composables/useToast'
import { inputClass, labelClass, checkboxClass } from '@/utils/formStyles'

interface Props {
  open: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'invited'): void
}>()

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

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

async function sendInvitation(): Promise<void> {
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
    inviteError.value = extractErrorMessage(error, t('admin.invite_modal.errors.send_failed'))
  } finally {
    isInviting.value = false
  }
}

function copyGeneratedLink(): void {
  const copyTextFallback = (text: string): boolean => {
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
          toast.error(t('admin.invite_modal.errors.copy_failed'))
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
      toast.error(t('admin.invite_modal.errors.copy_failed'))
    }
  }
}
</script>
