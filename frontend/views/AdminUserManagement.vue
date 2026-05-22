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
          @edit-requested="openEditModal" />
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

      <!-- === INVITE MODAL === -->
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
                <div class="mb-5">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="sendInviteEmail" class="rounded border-gray-300 text-blue-600" />
                    <span class="text-sm text-gray-700">Send invitation via email</span>
                  </label>
                </div>
                <div v-if="inviteError" class="mb-4 p-3 bg-red-50 text-red-700 text-xs rounded-md">
                  {{ inviteError }}
                </div>
                <div v-if="inviteSuccess" class="mb-4">
                  <div
                    class="p-3 text-xs rounded-md mb-2"
                    :class="inviteEmailSent ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'"
                  >
                    <template v-if="inviteEmailSent">
                      Invitation sent to email successfully!
                    </template>
                    <template v-else>
                      Invitation created but email delivery is not configured. Copy the link manually.
                    </template>
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

      <!-- === UNIFIED EDIT USER MODAL === -->
      <transition name="fade">
        <div v-if="editUser" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-md p-4" @click="closeEditModal">
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" @click.stop>
            <!-- Header -->
            <div class="flex items-center justify-between px-8 pt-7 pb-4 border-b border-gray-100">
              <div>
                <h3 class="text-lg font-bold text-gray-900">Edit User</h3>
                <p class="text-sm text-gray-500 mt-0.5">#{{ editUser.id }} &middot; {{ editUser.email }}</p>
              </div>
              <button @click="closeEditModal" class="text-gray-400 hover:text-gray-500 transition-colors">
                <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <div class="px-8 py-6 space-y-6">
              <!-- Error / Success -->
              <div v-if="editError" class="p-3 bg-red-50 text-red-700 text-xs rounded-md">{{ editError }}</div>
              <div v-if="editSuccess" class="p-3 bg-green-50 text-green-700 text-xs rounded-md">User updated successfully!</div>
              <div v-if="setPasswordSuccessMsg" class="p-3 bg-green-50 text-green-700 text-xs rounded-md">Password updated successfully!</div>

              <!-- === General Settings === -->
              <div>
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">General</h4>
                <div class="space-y-4">
                  <div>
                    <label class="block text-xs font-bold text-gray-600 mb-1">Full Name</label>
                    <input
                      v-model="editForm.full_name"
                      type="text"
                      class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-bold text-gray-600 mb-1">Email</label>
                    <input
                      v-model="editForm.email"
                      type="email"
                      class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                    />
                  </div>
                  <div class="flex gap-4">
                    <div class="flex-1">
                      <label class="block text-xs font-bold text-gray-600 mb-1">Role</label>
                      <select
                        v-model="editForm.role"
                        class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                        :disabled="editUser.id === currentUserId"
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
                      </select>
                      <p v-if="editUser.id === currentUserId" class="text-xs text-amber-600 mt-1">You cannot change your own role.</p>
                    </div>
                    <div class="flex-1">
                      <label class="block text-xs font-bold text-gray-600 mb-1">Status</label>
                      <div class="flex items-center gap-3 mt-2">
                        <button
                          type="button"
                          @click="toggleEditUserActive"
                          class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                          :class="[editForm.is_active ? 'bg-green-500' : 'bg-gray-300', editUser.id === currentUserId ? 'cursor-not-allowed opacity-50' : 'cursor-pointer']"
                        >
                          <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                                :class="editForm.is_active ? 'translate-x-6' : 'translate-x-1'" />
                        </button>
                        <span class="text-sm" :class="editForm.is_active ? 'text-green-700' : 'text-red-600'">
                          {{ editForm.is_active ? 'Active' : 'Inactive' }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Divider -->
              <hr class="border-gray-100" />

              <!-- === Set Password === -->
              <div>
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Set Password</h4>
                <div class="flex gap-2 items-start">
                  <div class="flex-1">
                    <input
                      v-model="editPassword"
                      type="password"
                      class="block w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400"
                      placeholder="Enter new password (optional)"
                    />
                  </div>
                  <button
                    type="button"
                    @click="setPasswordForEditUser"
                    :disabled="!editPassword || isSettingPassword"
                    class="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 transition disabled:opacity-50"
                  >{{ isSettingPassword ? '...' : 'Set' }}</button>
                </div>
              </div>

              <!-- Divider -->
              <hr class="border-gray-100" />

              <!-- === Danger Zone === -->
              <div class="p-4 border border-red-200 rounded-xl bg-red-50/50">
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <div class="flex-1">
                    <h4 class="text-sm font-bold text-red-800">Danger Zone</h4>
                    <p class="text-xs text-red-600 mt-1">Delete this user and all associated data. This cannot be undone.</p>
                    <button
                      type="button"
                      @click="confirmDeleteFromModal"
                      class="mt-3 px-4 py-1.5 text-xs font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition"
                    >Delete User</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex justify-end gap-2 px-8 pb-7 pt-4 border-t border-gray-100">
              <button
                type="button"
                @click="closeEditModal"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
              >Cancel</button>
              <button
                type="button"
                @click="saveEditUser"
                :disabled="isSavingEdit"
                class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg shadow-sm hover:bg-blue-700 transition disabled:opacity-50"
              >{{ isSavingEdit ? 'Saving...' : 'Save Changes' }}</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- === DELETE CONFIRMATION MODAL (from edit modal or grid) === -->
      <transition name="fade">
        <div v-if="deleteUserModal" class="fixed inset-0 z-[60] bg-black/30 backdrop-blur-md flex items-center justify-center p-4" @click="cancelDelete">
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
                <div class="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl mb-4">
                  <svg class="w-6 h-6 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <div>
                    <p class="text-sm font-semibold text-red-800">This will permanently delete:</p>
                    <ul class="mt-2 text-sm text-red-700 list-disc list-inside space-y-1">
                      <li>The user account and all associated data</li>
                      <li><strong>All projects</strong> owned by this user, including files, documents, schemas, prompts, trials, and evaluations</li>
                      <li><strong>Uploaded files</strong> will be removed from storage</li>
                    </ul>
                  </div>
                </div>
                <p class="text-sm text-gray-500">
                  Are you sure you want to delete this user?
                </p>
                <p class="mt-2 text-sm font-medium text-gray-900">
                  {{ userToDelete?.full_name }} ({{ userToDelete?.email }})
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
                >{{ isProcessingDelete ? 'Deleting...' : 'Permanently Delete' }}</button>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- === DELETE INVITATION MODAL === -->
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import UserGrid from '@/components/UserGrid.vue'
import InvitationGrid from '@/components/InvitationGrid.vue'
import { api } from '@/services/api'
import { useToast } from 'vue-toastification'
import { themeMaterial, iconSetMaterial } from 'ag-grid-community'

const materialTheme = themeMaterial.withPart(iconSetMaterial)
const toast = useToast()

const currentUserId = ref(null)

const users = ref([])
const loading = ref(true)
const userSearch = ref('')

const invitations = ref([])
const loadingInvitations = ref(true)
const invitationSearch = ref('')
const showUsedInvitations = ref(false)

// --- Invite modal ---
const showInviteModal = ref(false)
const inviteEmail = ref('')
const isInviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref(false)
const inviteEmailSent = ref(false)
const sendInviteEmail = ref(false)
const invitationLink = ref('')
const copySuccess = ref(false)

// --- Edit modal ---
const editUser = ref(null)
const editForm = ref({ full_name: '', email: '', role: 'user', is_active: true })
const editPassword = ref('')
const editError = ref('')
const editSuccess = ref(false)
const isSavingEdit = ref(false)
const isSettingPassword = ref(false)
const setPasswordSuccessMsg = ref(false)

// Disable background scrolling when edit modal is open
watch(editUser, (val) => {
  document.body.classList.toggle('overflow-hidden', !!val)
})
onUnmounted(() => {
  document.body.classList.remove('overflow-hidden')
})

// --- Delete user ---
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
  // Get current user info
  try {
    const me = await api.get('/user/me')
    currentUserId.value = me.data.id
  } catch (_) {}
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

// --- Invite ---
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
    const response = await api.post('/user/invite', formData.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    const baseUrl = window.location.origin
    invitationLink.value = `${baseUrl}/register?token=${response.data.token}`
    inviteEmailSent.value = response.data.email_sent || false
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

// --- Edit User ---
function openEditModal(user) {
  editForm.value = {
    full_name: user.full_name,
    email: user.email,
    role: user.role,
    is_active: user.is_active,
  }
  editPassword.value = ''
  editError.value = ''
  editSuccess.value = false
  setPasswordSuccessMsg.value = false
  editUser.value = user
}

function closeEditModal() {
  editUser.value = null
}

function toggleEditUserActive() {
  if (editUser.value && editUser.value.id !== currentUserId.value) {
    editForm.value.is_active = !editForm.value.is_active
  }
}

async function saveEditUser() {
  if (!editUser.value) return
  isSavingEdit.value = true
  editError.value = ''
  editSuccess.value = false
  try {
    const payload = {}
    if (editForm.value.full_name !== editUser.value.full_name) payload.full_name = editForm.value.full_name
    if (editForm.value.email !== editUser.value.email) payload.email = editForm.value.email
    if (editForm.value.role !== editUser.value.role) payload.role = editForm.value.role
    if (editForm.value.is_active !== editUser.value.is_active) payload.is_active = editForm.value.is_active

    if (Object.keys(payload).length === 0) {
      editSuccess.value = true
      return
    }

    const response = await api.patch(`/user/${editUser.value.id}`, payload)
    const updatedUser = response.data
    const idx = users.value.findIndex(u => u.id === updatedUser.id)
    if (idx !== -1) {
      users.value[idx] = updatedUser
      users.value = [...users.value]
    }
    editUser.value = updatedUser
    editSuccess.value = true
    toast.success(`User "${updatedUser.full_name}" updated.`)
  } catch (error) {
    editError.value = error.response?.data?.detail || 'Failed to update user.'
  } finally {
    isSavingEdit.value = false
  }
}

async function setPasswordForEditUser() {
  if (!editUser.value || !editPassword.value) return
  isSettingPassword.value = true
  setPasswordSuccessMsg.value = false
  try {
    await api.post(`/user/${editUser.value.id}/set-password`, { new_password: editPassword.value })
    setPasswordSuccessMsg.value = true
    editPassword.value = ''
    toast.success('Password updated.')
  } catch (error) {
    editError.value = error.response?.data?.detail || 'Failed to set password'
  } finally {
    isSettingPassword.value = false
  }
}

// --- Delete user ---
function confirmDeleteFromModal() {
  if (!editUser.value) return
  userToDelete.value = editUser.value
  deleteUserModal.value = true
}

async function deleteUser() {
  if (!userToDelete.value || isProcessingDelete.value) return
  isProcessingDelete.value = true
  const userName = userToDelete.value.full_name
  try {
    await api.delete(`/user/${userToDelete.value.id}`)
    users.value = users.value.filter(u => u.id !== userToDelete.value.id)
    toast.success(`User "${userName}" deleted successfully.`)
    deleteUserModal.value = false
    userToDelete.value = null
    editUser.value = null // close edit modal too
  } catch (error) {
    toast.error(error.response?.data?.detail || 'Failed to delete user.')
  } finally {
    isProcessingDelete.value = false
  }
}
function cancelDelete() {
  deleteUserModal.value = false
  userToDelete.value = null
}

// --- Delete invitation ---
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
    invitations.value = invitations.value.filter(inv => inv.id !== invitationToDelete.value.id)
    toast.success(`Invitation for "${invitationToDelete.value.email}" deleted.`)
    deleteInvitationModal.value = false
    invitationToDelete.value = null
  } catch (error) {
    toast.error(error.response?.data?.detail || 'Failed to delete invitation.')
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
