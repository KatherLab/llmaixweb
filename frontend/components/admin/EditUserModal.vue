<template>
  <BaseModal
    :open="open"
    size="md"
    panel-class="dark:bg-slate-900 dark:border-slate-700"
    header-class="dark:border-slate-800"
    footer-class="dark:border-slate-800 dark:bg-slate-900"
    @close="emit('close')"
  >
    <template #header>
      <div>
        <h3 class="text-lg font-bold text-gray-900 dark:text-white">Edit User</h3>
        <p class="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
          #{{ user?.id }} &middot; {{ user?.email }}
        </p>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Error / Success -->
      <div
        v-if="editError"
        class="p-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded-md"
      >
        {{ editError }}
      </div>
      <div
        v-if="editSuccess"
        class="p-3 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs rounded-md"
      >
        User updated successfully!
      </div>
      <div
        v-if="setPasswordSuccessMsg"
        class="p-3 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs rounded-md"
      >
        Password updated successfully!
      </div>

      <!-- === General Settings === -->
      <div>
        <h4
          class="text-xs font-bold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3"
        >
          General
        </h4>
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-gray-600 dark:text-slate-300 mb-1"
              >Full Name</label
            >
            <input
              v-model="editForm.full_name"
              type="text"
              class="block w-full px-4 py-2 text-sm border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-600 dark:text-slate-300 mb-1"
              >Email</label
            >
            <input
              v-model="editForm.email"
              type="email"
              class="block w-full px-4 py-2 text-sm border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-400"
            />
          </div>
          <div class="flex gap-4">
            <div class="flex-1">
              <label class="block text-xs font-bold text-gray-600 dark:text-slate-300 mb-1"
                >Role</label
              >
              <select
                v-model="editForm.role"
                class="block w-full px-4 py-2 text-sm border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-400"
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
              <label class="block text-xs font-bold text-gray-600 dark:text-slate-300 mb-1"
                >Status</label
              >
              <div class="flex items-center gap-3 mt-2">
                <button
                  type="button"
                  class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                  :class="[
                    editForm.is_active ? 'bg-green-500' : 'bg-gray-300 dark:bg-slate-600',
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
      <hr class="border-gray-100 dark:border-slate-800" />

      <!-- === Set Password === -->
      <div>
        <h4
          class="text-xs font-bold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3"
        >
          Set Password
        </h4>
        <div class="flex gap-2 items-start">
          <div class="flex-1">
            <input
              v-model="editPassword"
              type="password"
              class="block w-full px-4 py-2 text-sm border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-400"
              placeholder="Enter new password (optional)"
            />
          </div>
          <button
            type="button"
            :disabled="!editPassword || isSettingPassword"
            class="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 dark:bg-indigo-500 rounded-lg shadow-sm hover:bg-indigo-700 dark:hover:bg-indigo-600 transition disabled:opacity-50"
            @click="setPasswordForEditUser"
          >
            {{ isSettingPassword ? '...' : 'Set' }}
          </button>
        </div>
      </div>

      <!-- Divider -->
      <hr class="border-gray-100 dark:border-slate-800" />

      <!-- === Danger Zone === -->
      <div
        class="p-4 border border-red-200 dark:border-red-900 rounded-xl bg-red-50/50 dark:bg-red-900/20"
      >
        <div class="flex items-start gap-3">
          <svg
            class="w-5 h-5 text-red-500 dark:text-red-400 shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <div class="flex-1">
            <h4 class="text-sm font-bold text-red-800 dark:text-red-300">Danger Zone</h4>
            <p class="text-xs text-red-600 dark:text-red-400 mt-1">
              Delete this user and all associated data. This cannot be undone.
            </p>
            <BaseButton
              variant="danger"
              size="sm"
              class="mt-3 dark:bg-red-500 dark:hover:bg-red-600"
              @click="confirmDeleteFromModal"
            >
              Delete User
            </BaseButton>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <BaseButton
        variant="secondary"
        class="dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600 dark:hover:bg-slate-700"
        @click="emit('close')"
      >
        Cancel
      </BaseButton>
      <BaseButton
        variant="primary"
        :disabled="isSavingEdit"
        class="dark:bg-blue-500 dark:hover:bg-blue-600"
        @click="saveEditUser"
      >
        {{ isSavingEdit ? 'Saving...' : 'Save Changes' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useToast } from 'vue-toastification'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'

const props = defineProps({
  open: { type: Boolean, required: true },
  user: { type: Object, default: null },
  currentUserId: { type: Number, default: null },
})

const emit = defineEmits(['close', 'saved', 'delete-requested'])

const toast = useToast()

const editForm = ref({ full_name: '', email: '', role: 'user', is_active: true })
const editPassword = ref('')
const editError = ref('')
const editSuccess = ref(false)
const isSavingEdit = ref(false)
const isSettingPassword = ref(false)
const setPasswordSuccessMsg = ref(false)

function initForm() {
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

function toggleEditUserActive() {
  if (props.user && props.user.id !== props.currentUserId) {
    editForm.value.is_active = !editForm.value.is_active
  }
}

async function saveEditUser() {
  if (!props.user) return
  isSavingEdit.value = true
  editError.value = ''
  editSuccess.value = false
  try {
    const payload = {}
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

async function setPasswordForEditUser() {
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

function confirmDeleteFromModal() {
  if (!props.user) return
  emit('delete-requested', props.user)
}
</script>
