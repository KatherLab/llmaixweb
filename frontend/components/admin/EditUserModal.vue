<template>
  <BaseModal :open="open" size="md" @close="emit('close')">
    <template #header>
      <div>
        <h3 class="text-lg font-bold text-content">Edit User</h3>
        <p class="text-sm text-content-subtle mt-0.5">#{{ user?.id }} &middot; {{ user?.email }}</p>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Error / Success -->
      <Callout v-if="editError" variant="danger" class="text-xs">
        {{ editError }}
      </Callout>
      <Callout v-if="editSuccess" variant="success" class="text-xs">
        User updated successfully!
      </Callout>
      <Callout v-if="setPasswordSuccessMsg" variant="success" class="text-xs">
        Password updated successfully!
      </Callout>

      <!-- === General Settings === -->
      <div>
        <h4 class="text-xs font-bold text-content-subtle uppercase tracking-wider mb-3">General</h4>
        <div class="space-y-4">
          <div>
            <label :class="labelClass">Full Name</label>
            <input v-model="editForm.full_name" type="text" :class="inputClass" />
          </div>
          <div>
            <label :class="labelClass">Email</label>
            <input v-model="editForm.email" type="email" :class="inputClass" maxlength="254" />
          </div>
          <div class="flex gap-4">
            <div class="flex-1">
              <label :class="labelClass">Role</label>
              <select
                v-model="editForm.role"
                :class="selectClass"
                :disabled="user?.id === currentUserId"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <p
                v-if="user?.id === currentUserId"
                class="text-xs text-amber-600 dark:text-amber-400 mt-1"
              >
                You cannot change your own role.
              </p>
            </div>
            <div class="flex-1">
              <label :class="labelClass">Status</label>
              <div class="flex items-center gap-3 mt-2">
                <button
                  type="button"
                  role="switch"
                  :aria-checked="editForm.is_active"
                  :aria-label="`User account ${editForm.is_active ? 'active' : 'inactive'}`"
                  :disabled="user?.id === currentUserId"
                  class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                  :class="[
                    editForm.is_active ? 'bg-green-500' : 'bg-surface-sunken',
                    user?.id === currentUserId ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
                  ]"
                  @click="toggleEditUserActive"
                >
                  <span
                    class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                    :class="editForm.is_active ? 'translate-x-6' : 'translate-x-1'"
                  />
                </button>
                <span
                  class="text-sm"
                  :class="
                    editForm.is_active
                      ? 'text-green-700 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  "
                >
                  {{ editForm.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <hr class="border-default" />

      <!-- === Set Password === -->
      <div>
        <h4 class="text-xs font-bold text-content-subtle uppercase tracking-wider mb-3">
          Set Password
        </h4>
        <div class="flex gap-2 items-start">
          <div class="flex-1">
            <input
              v-model="editPassword"
              type="password"
              :class="inputClass"
              placeholder="Enter new password (optional)"
            />
          </div>
          <BaseButton
            type="button"
            variant="primary"
            size="sm"
            :disabled="!editPassword || isSettingPassword"
            :loading="isSettingPassword"
            @click="setPasswordForEditUser"
          >
            Set
          </BaseButton>
        </div>
      </div>

      <!-- Divider -->
      <hr class="border-default" />

      <!-- === Danger Zone === -->
      <Callout variant="danger" title="Danger Zone">
        <p class="text-xs mt-1">Delete this user and all associated data. This cannot be undone.</p>
        <BaseButton variant="danger" size="sm" class="mt-3" @click="confirmDeleteFromModal">
          Delete User
        </BaseButton>
      </Callout>
    </div>

    <template #footer>
      <BaseButton
        variant="secondary"
        class="dark:bg-surface dark:text-content-muted dark:border-strong dark:hover:bg-surface-sunken"
        @click="emit('close')"
      >
        Cancel
      </BaseButton>
      <BaseButton
        variant="primary"
        :disabled="isSavingEdit"
        class="dark:bg-primary dark:hover:bg-primary-hover"
        @click="saveEditUser"
      >
        {{ isSavingEdit ? 'Saving...' : 'Save Changes' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { UserResponse, UserUpdateAdmin, UserRole } from '@/types'
import { useToast } from '@/composables/useToast'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import Callout from '@/components/common/Callout.vue'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, selectClass, labelClass } from '@/utils/formStyles'

interface Props {
  open: boolean
  user?: UserResponse | null
  currentUserId?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  user: null,
  currentUserId: null,
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', user: UserResponse): void
  (e: 'delete-requested', user: UserResponse): void
}>()

const toast = useToast()

interface EditForm {
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
}

const editForm = ref<EditForm>({ full_name: '', email: '', role: 'user', is_active: true })
const editPassword = ref('')
const editError = ref('')
const editSuccess = ref(false)
const isSavingEdit = ref(false)
const isSettingPassword = ref(false)
const setPasswordSuccessMsg = ref(false)

function initForm(): void {
  if (!props.user) return
  editForm.value = {
    full_name: props.user.full_name,
    email: props.user.email,
    role: props.user.role,
    is_active: props.user.is_active,
  }
  editPassword.value = ''
  editError.value = ''
  editSuccess.value = false
  setPasswordSuccessMsg.value = false
}

// Initialize/reset the form whenever a different user is opened.
// Using user.id so that re-saving (parent replaces editUser with the updated
// object, same id) does NOT reset the form and clear the success message.
watch(
  () => props.user?.id,
  (newId, oldId) => {
    if (newId && newId !== oldId) {
      initForm()
    }
  },
)

function toggleEditUserActive(): void {
  if (props.user && props.user.id !== props.currentUserId) {
    editForm.value.is_active = !editForm.value.is_active
  }
}

async function saveEditUser(): Promise<void> {
  if (!props.user) return
  isSavingEdit.value = true
  editError.value = ''
  editSuccess.value = false
  try {
    const payload: UserUpdateAdmin = {}
    if (editForm.value.full_name !== props.user.full_name)
      payload.full_name = editForm.value.full_name
    if (editForm.value.email !== props.user.email) payload.email = editForm.value.email
    if (editForm.value.role !== props.user.role) payload.role = editForm.value.role
    if (editForm.value.is_active !== props.user.is_active)
      payload.is_active = editForm.value.is_active

    if (Object.keys(payload).length === 0) {
      editSuccess.value = true
      return
    }

    const response = await usersApi.update(props.user.id, payload)
    const updatedUser = response.data
    editSuccess.value = true
    toast.success(`User "${updatedUser.full_name}" updated.`)
    emit('saved', updatedUser)
  } catch (error) {
    editError.value = extractErrorMessage(error, 'Failed to update user.')
  } finally {
    isSavingEdit.value = false
  }
}

async function setPasswordForEditUser(): Promise<void> {
  if (!props.user || !editPassword.value) return
  isSettingPassword.value = true
  setPasswordSuccessMsg.value = false
  try {
    await usersApi.setPassword(props.user.id, { new_password: editPassword.value })
    setPasswordSuccessMsg.value = true
    editPassword.value = ''
    toast.success('Password updated.')
  } catch (error) {
    editError.value = extractErrorMessage(error, 'Failed to set password')
  } finally {
    isSettingPassword.value = false
  }
}

function confirmDeleteFromModal(): void {
  if (!props.user) return
  emit('delete-requested', props.user)
}
</script>
