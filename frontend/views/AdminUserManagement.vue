<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-100 via-white to-blue-100">
    <header class="sticky top-0 z-30 bg-white shadow-lg">
      <div class="max-w-7xl mx-auto flex justify-between items-center py-5 px-6">
        <div class="flex items-center gap-3">
          <div class="bg-blue-100 text-blue-500 rounded-full p-2 shadow">
            <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24">
              <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2"/>
              <path d="M6 21v-2a4 4 0 014-4h0a4 4 0 014 4v2" stroke="currentColor" stroke-width="2"/>
            </svg>
          </div>
          <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
        </div>
        <button @click="showInviteModal = true"
                class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow transition">
          + Invite User
        </button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto py-8 px-6 space-y-12">
      <section class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold text-gray-900">Users
            <span class="ml-2 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">{{ users.length }} total</span>
          </h2>
          <input v-model="userSearch" type="search" placeholder="Search users…"
                 class="rounded-xl border border-gray-200 px-4 py-2 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 transition w-64" />
        </div>
        <div v-if="loading" class="flex justify-center py-20">
          <div class="animate-spin rounded-full h-10 w-10 border-b-4 border-blue-500"></div>
        </div>
        <UserGrid
          :rowData="users"
          :search="userSearch"
          :theme="materialTheme"
          @toggle-requested="confirmToggleUserStatus"
          @delete-requested="confirmDeleteUser"
          @set-password-requested="openSetPasswordModal" />
      </section>

      <section class="card">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold text-gray-900">
            Invitations
            <label class="ml-4 text-xs font-medium text-gray-600">
              <input type="checkbox" v-model="showUsedInvitations" class="mr-2 rounded border-gray-300 text-blue-600">Show used
            </label>
          </h2>
          <div class="flex items-center gap-4">
            <span class="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">{{ activeInvitations }} active</span>
            <input v-model="invitationSearch" type="search" placeholder="Search invitations…"
                   class="rounded-xl border border-gray-200 px-4 py-2 text-sm focus:ring-2 focus:ring-blue-300 focus:border-blue-400 transition w-64" />
          </div>
        </div>
        <div v-if="loadingInvitations" class="flex justify-center py-20">
          <div class="animate-spin rounded-full h-10 w-10 border-b-4 border-blue-500"></div>
        </div>
        <InvitationGrid :rowData="filteredInvitations"
                        :columnDefs="invitationColumnDefs"
                        :defaultColDef="invitationDefaultColDef"
                        :search="invitationSearch"
                        :theme="materialTheme"
                        :onGridReady="onInvitationGridReady" />
      </section>

      <transition name="fade">
        <div v-if="showInviteModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md p-4" @click="closeInviteModal">
          <div class="bg-white/90 rounded-2xl shadow-2xl w-full max-w-md" @click.stop style="backdrop-filter: blur(12px);">
            <div class="px-8 py-7">
              <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-bold text-gray-900">Invite New User</h3>
                <button @click="showInviteModal = false" class="text-gray-400 hover:text-gray-500 transition-colors">
                  <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                </button>
              </div>
              <form @submit.prevent="sendInvitation">
                <div class="mb-5">
                  <label for="email" class="block text-xs font-bold text-gray-600 mb-1">Email address</label>
                  <input
                    id="email"
                    v-model="inviteEmail"
                    type="email"
                    required
                    class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                    placeholder="Enter email address"
                  />
                </div>
                <div v-if="inviteError" class="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-md">
                  {{ inviteError }}
                </div>
                <div v-if="inviteSuccess" class="mb-4">
                  <div class="p-3 bg-green-50 text-green-700 text-xs rounded-md mb-2">
                    Invitation sent! Email will be auto-filled in registration.
                  </div>
                  <div class="flex items-center mt-2 gap-2">
                    <input
                      type="text"
                      readonly
                      :value="invitationLink"
                      class="block w-full px-4 py-2 text-xs border border-gray-200 rounded-lg pr-10"
                    />
                    <button
                      type="button"
                      @click="copyGeneratedLink"
                      class="p-1.5 rounded-lg border border-gray-200 text-blue-600 hover:bg-blue-50 transition-all relative"
                    >
                      <span v-if="copySuccess" class="absolute bg-gray-800 text-white text-xs px-2 py-1 rounded -top-8 left-1/2 -translate-x-1/2 z-10">
                        Copied!
                      </span>
                      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div class="mt-7 flex justify-end gap-2">
                  <button
                    type="button"
                    @click="showInviteModal = false"
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
                  >Cancel</button>
                  <button
                    type="submit"
                    :disabled="isInviting"
                    class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg shadow-sm hover:bg-blue-700 transition"
                  >{{ isInviting ? 'Sending...' : 'Send Invitation' }}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </transition>
      <transition name="fade">
        <div v-if="setPasswordUser" class="fixed inset-0 bg-black/30 backdrop-blur flex items-center justify-center z-50" @click="setPasswordUser = null">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md" @click.stop>
            <form @submit.prevent="setPassword">
              <div class="px-8 py-6">
                <div class="flex justify-between items-center mb-6">
                  <h3 class="text-lg font-bold text-gray-900">Set User Password</h3>
                  <button type="button" @click="setPasswordUser = null" class="text-gray-400 hover:text-gray-500">
                    <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
                <div class="mb-4 text-gray-700 text-sm">
                  For <span class="font-semibold">{{ setPasswordUser.full_name }}</span> ({{ setPasswordUser.email }})
                </div>
                <div class="mb-4">
                  <label class="block text-xs font-bold mb-1">New Password</label>
                  <input
                    v-model="newPassword"
                    type="password"
                    required
                    minlength="8"
                    class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                    placeholder="Enter new password"
                  />
                </div>
                <div v-if="setPasswordError" class="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-md">
                  {{ setPasswordError }}
                </div>
                <div v-if="setPasswordSuccess" class="mb-4 p-3 bg-green-50 text-green-700 text-xs rounded-md">
                  Password updated!
                </div>
                <div class="mt-6 flex justify-end gap-2">
                  <button
                    type="button"
                    @click="setPasswordUser = null"
                    class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                  >Cancel</button>
                  <button
                    type="submit"
                    :disabled="isSettingPassword"
                    class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                  >{{ isSettingPassword ? 'Updating...' : 'Set Password' }}</button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </transition>
      <transition name="fade">
        <div v-if="userToToggle" class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50" @click="userToToggle = null">
          <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full" @click.stop>
            <div class="px-6 py-5">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900">
                  {{ userToToggle.is_active ? 'Disable' : 'Enable' }} User
                </h3>
                <button @click="userToToggle = null" class="text-gray-400 hover:text-gray-500 transition-colors">
                  <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="mb-6">
                <p class="text-sm text-gray-500">
                  Are you sure you want to {{ userToToggle.is_active ? 'disable' : 'enable' }} this user?
                </p>
                <p class="mt-2 text-sm font-medium text-gray-900">
                  {{ userToToggle.full_name }} ({{ userToToggle.email }})
                </p>
              </div>
              <div class="flex justify-end space-x-3">
                <button
                  type="button"
                  @click="userToToggle = null"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
                >Cancel</button>
                <button
                  type="button"
                  @click="toggleUserStatus"
                  class="px-4 py-2 text-sm font-medium text-white bg-amber-600 border border-transparent rounded-lg shadow-sm hover:bg-amber-700 transition"
                  :disabled="isProcessingUser === userToToggle.id"
                >{{ isProcessingUser === userToToggle.id ? 'Processing...' : (userToToggle.is_active ? 'Disable' : 'Enable') }}</button>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <transition name="fade">
        <div v-if="deleteUserModal" class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50" @click="cancelDelete">
          <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full" @click.stop>
            <div class="px-6 py-5">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Delete User</h3>
                <button @click="cancelDelete" class="text-gray-400 hover:text-gray-500 transition-colors">
                  <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="mb-6">
                <p class="text-sm text-gray-500">
                  Are you sure you want to delete this user? This action cannot be undone.
                </p>
                <p v-if="userToDelete" class="mt-2 text-sm font-medium text-gray-900">
                  {{ userToDelete.full_name }} ({{ userToDelete.email }})
                </p>
              </div>
              <div class="flex justify-end space-x-3">
                <button
                  type="button"
                  @click="cancelDelete"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
                >Cancel</button>
                <button
                  type="button"
                  @click="deleteUser"
                  class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg shadow-sm hover:bg-red-700 transition"
                  :disabled="isProcessingDelete"
                >{{ isProcessingDelete ? 'Deleting...' : 'Delete' }}</button>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <transition name="fade">
        <div v-if="deleteInvitationModal" class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50" @click="cancelDeleteInvitation">
          <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full" @click.stop>
            <div class="px-6 py-5">
              <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900">Delete Invitation</h3>
                <button @click="cancelDeleteInvitation" class="text-gray-400 hover:text-gray-500 transition-colors">
                  <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div class="mb-6">
                <p class="text-sm text-gray-500">
                  Are you sure you want to delete this invitation? This action cannot be undone.
                </p>
                <p v-if="invitationToDelete" class="mt-2 text-sm font-medium text-gray-900">
                  {{ invitationToDelete.email }}
                </p>
              </div>
              <div class="flex justify-end space-x-3">
                <button
                  type="button"
                  @click="cancelDeleteInvitation"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
                >Cancel</button>
                <button
                  type="button"
                  @click="deleteInvitation"
                  class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg shadow-sm hover:bg-red-700 transition"
                  :disabled="isProcessingDelete"
                >{{ isProcessingDelete ? 'Deleting...' : 'Delete' }}</button>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import UserGrid from '@/components/UserGrid.vue'
import InvitationGrid from '@/components/InvitationGrid.vue'
import { api } from '@/services/api'
import { themeMaterial, iconSetMaterial } from 'ag-grid-community'

const materialTheme = themeMaterial.withPart(iconSetMaterial)

const userGrid = ref(null)
const users = ref([])
const loading = ref(true)
const userSearch = ref('')

const invitations = ref([])
const loadingInvitations = ref(true)
const invitationSearch = ref('')
const showUsedInvitations = ref(false)

const showInviteModal = ref(false)
const inviteEmail = ref('')
const isInviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref(false)
const invitationLink = ref('')
const copySuccess = ref(false)

const setPasswordUser = ref(null)
const newPassword = ref('')
const setPasswordError = ref('')
const setPasswordSuccess = ref(false)
const isSettingPassword = ref(false)

const userToToggle = ref(null)
const isProcessingUser = ref(null)
const deleteUserModal = ref(false)
const userToDelete = ref(null)
const isProcessingDelete = ref(false)
const deleteInvitationModal = ref(false)
const invitationToDelete = ref(null)

const activeInvitations = computed(() =>
  invitations.value.filter(inv => !inv.is_used).length
)
const filteredInvitations = computed(() => {
  let filtered = [...invitations.value];
  if (!showUsedInvitations.value) {
    filtered = filtered.filter(inv => !inv.is_used);
  }
  return filtered.sort((a, b) => {
    if (showUsedInvitations.value && a.is_used !== b.is_used) {
      return a.is_used ? 1 : -1;
    }
    return b.id - a.id;
  });
})

const invitationColumnDefs = [
  { field: 'email', headerName: 'Email', sortable: true, filter: true, flex: 1, minWidth: 140 },
  { field: 'is_used', headerName: 'Used', sortable: true, filter: true, flex: 1, minWidth: 70,
    valueFormatter: ({ value }) => value ? 'Yes' : 'No',
    cellRenderer: ({ value }) =>
      value
        ? '<span class="bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full text-xs">Yes</span>'
        : '<span class="bg-green-50 text-green-700 px-2 py-0.5 rounded-full text-xs">No</span>',
  },
  {
    headerName: 'Actions', field: 'actions', minWidth: 110, maxWidth: 130, sortable: false, filter: false, pinned: 'right',
    cellRenderer: params => {
      return `<button class="text-xs text-red-600 font-bold ag-action-btn" data-action="delete">Delete</button>`
    }
  },
]
const invitationDefaultColDef = { resizable: true, sortable: true, filter: true }

onMounted(async () => {
  await Promise.all([
    loadUsers(),
    loadInvitations()
  ])
})

async function loadUsers() {
  loading.value = true
  try {
    const response = await api.get('/user')
    users.value = response.data
  } finally {
    loading.value = false
  }
}

async function loadInvitations() {
  loadingInvitations.value = true
  try {
    const response = await api.get('/user/invitations')
    invitations.value = response.data
  } finally {
    loadingInvitations.value = false
  }
}

async function sendInvitation() {
  if (!inviteEmail.value) return
  isInviting.value = true
  inviteError.value = ''
  inviteSuccess.value = false
  try {
    const formData = new URLSearchParams()
    formData.append('email', inviteEmail.value)
    const response = await api.post('/user/invite', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    const baseUrl = window.location.origin
    invitationLink.value = `${baseUrl}/register?token=${response.data.token}`
    inviteSuccess.value = true
    await loadInvitations()
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
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    let success = false;
    try {
      success = document.execCommand('copy');
    } catch (err) {}
    document.body.removeChild(textArea);
    return success;
  };
  const baseUrl = window.location.origin;
  const token = invitationLink.value.split('token=')[1];
  const link = `${baseUrl}/register?token=${token}`;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(link)
      .then(() => {
        copySuccess.value = true;
        setTimeout(() => { copySuccess.value = false; }, 2000);
      })
      .catch(() => {
        const success = copyTextFallback(link);
        if (success) {
          copySuccess.value = true;
          setTimeout(() => { copySuccess.value = false; }, 2000);
        } else {
          alert(`Failed to copy. Please copy this link manually:\n${link}`);
        }
      });
  } else {
    const success = copyTextFallback(link);
    if (success) {
      copySuccess.value = true;
      setTimeout(() => { copySuccess.value = false; }, 2000);
    } else {
      alert(`Failed to copy. Please copy this link manually:\n${link}`);
    }
  }
}

function openSetPasswordModal(user) {
  setPasswordUser.value = user
  newPassword.value = ''
  setPasswordError.value = ''
  setPasswordSuccess.value = false
}

async function setPassword() {
  if (!setPasswordUser.value || !newPassword.value) return
  isSettingPassword.value = true
  setPasswordError.value = ''
  setPasswordSuccess.value = false
  try {
    await api.post(`/user/${setPasswordUser.value.id}/set-password`, { new_password: newPassword.value })
    setPasswordSuccess.value = true
    setTimeout(() => {
      setPasswordUser.value = null
    }, 1200)
    await loadUsers()
  } catch (error) {
    setPasswordError.value = error.response?.data?.detail || 'Failed to set password'
  } finally {
    isSettingPassword.value = false
  }
}

function confirmToggleUserStatus(user) {
  userToToggle.value = user
}
async function toggleUserStatus() {
  if (!userToToggle.value || isProcessingUser.value) return
  isProcessingUser.value = userToToggle.value.id
  try {
    await api.patch(`/user/${userToToggle.value.id}/toggle-status`)
    await loadUsers()
    userToToggle.value = null
  } finally {
    isProcessingUser.value = null
  }
}

function confirmDeleteUser(user) {
  userToDelete.value = user
  deleteUserModal.value = true
}
async function deleteUser() {
  if (!userToDelete.value || isProcessingDelete.value) return
  isProcessingDelete.value = true
  try {
    await api.delete(`/user/${userToDelete.value.id}`)
    await loadUsers()
    deleteUserModal.value = false
    userToDelete.value = null
  } finally {
    isProcessingDelete.value = false
  }
}
function cancelDelete() {
  deleteUserModal.value = false
  userToDelete.value = null
}

function onInvitationGridReady(params) {
  params.api.addEventListener('cellClicked', (event) => {
    if (event.colDef.field !== 'actions') return
    const invitation = event.data
    if (event.event.target.dataset.action === 'delete') {
      confirmDeleteInvitation(invitation)
    }
  })
}

function confirmDeleteInvitation(invitation) {
  invitationToDelete.value = invitation
  deleteInvitationModal.value = true
}
async function deleteInvitation() {
  if (!invitationToDelete.value || isProcessingDelete.value) return
  isProcessingDelete.value = true
  try {
    await api.delete(`/user/invitations/${invitationToDelete.value.id}`)
    await loadInvitations()
    deleteInvitationModal.value = false
    invitationToDelete.value = null
  } finally {
    isProcessingDelete.value = false
  }
}
function cancelDeleteInvitation() {
  deleteInvitationModal.value = false
  invitationToDelete.value = null
}
function closeInviteModal() {
  if (!isInviting.value) {
    showInviteModal.value = false
    if (inviteSuccess.value) {
      inviteEmail.value = ''
      inviteSuccess.value = false
    }
  }
}
</script>

<style>
.card {
  background: rgba(255,255,255,0.8);
  border-radius: 1.5rem;
  box-shadow: 0 6px 24px rgba(30,64,175,0.12);
  padding: 1.5rem;
  backdrop-filter: blur(8px);
}
</style>
