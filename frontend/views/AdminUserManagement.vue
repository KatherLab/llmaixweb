<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <!-- User Actions -->
      <div class="mb-6 flex justify-end">
        <button
          @click="showInviteModal = true"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
        >
          <svg class="-ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Invite User
        </button>
      </div>

      <!-- User List -->
      <div class="bg-white shadow rounded-lg mb-8 overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
          <h2 class="text-lg font-medium text-gray-900">Users</h2>
          <span class="text-sm text-gray-500">{{ users.length }} total users</span>
        </div>

        <div v-if="loading" class="flex justify-center items-center p-6">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
        </div>

        <div v-else class="p-4">
          <UserGrid
            ref="userGrid"
            @toggle-requested="confirmToggleUserStatus"
            @delete-requested="confirmDeleteUser"
          />
        </div>
      </div>

      <!-- Invitations Section -->
      <div class="bg-white shadow rounded-lg overflow-hidden">
        <div class="px-6 py-5 border-b border-gray-200 flex justify-between items-center">
          <div class="flex items-center">
            <h2 class="text-lg font-medium text-gray-900">Invitations</h2>
            <div class="ml-4">
              <label class="inline-flex items-center text-sm text-gray-600">
                <input
                  type="checkbox"
                  v-model="showUsedInvitations"
                  class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span class="ml-2">Show used invitations</span>
              </label>
            </div>
          </div>
          <span class="text-sm text-gray-500">{{ activeInvitations }} active invitations</span>
        </div>

        <div v-if="loadingInvitations" class="flex justify-center items-center p-6">
          <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
        </div>

        <div v-else class="p-4">
          <InvitationsGrid
            :invitations="filteredInvitations"
            @confirm-delete-invitation="confirmDeleteInvitation"
          />
        </div>
      </div>
    </main>

    <!-- Invite Modal -->
    <div v-if="showInviteModal" class="fixed inset-0 bg-black/30 backdrop-blur-md flex items-center justify-center p-4 z-50" @click="closeInviteModal">
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full" @click.stop>
        <div class="px-6 py-5">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold text-gray-900">Invite New User</h3>
            <button @click="showInviteModal = false" class="text-gray-400 hover:text-gray-500 transition-colors">
              <svg class="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <form @submit.prevent="sendInvitation">
            <div class="mb-4">
              <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email address</label>
              <input
                id="email"
                v-model="inviteEmail"
                type="email"
                required
                class="block w-full px-4 py-2.5 text-sm text-gray-900 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter email address"
              />
            </div>
            <div v-if="inviteError" class="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded-md">
              {{ inviteError }}
            </div>
            <div v-if="inviteSuccess" class="mb-4">
              <div class="p-3 bg-green-50 text-green-700 text-sm rounded-md mb-2">
                Invitation sent successfully! Email will be automatically pre-filled when the user opens the link.
              </div>
              <div class="flex items-center mt-2">
                <input
                  type="text"
                  readonly
                  :value="invitationLink"
                  class="block w-full px-4 py-2.5 text-sm text-gray-900 border border-gray-300 rounded-lg pr-10"
                />
                <button
                  type="button"
                  @click="copyGeneratedLink"
                  class="ml-2 inline-flex items-center p-1.5 border border-transparent rounded-md text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  <span v-if="copySuccess" class="absolute bg-gray-800 text-white text-xs px-2 py-1 rounded -mt-10 ml-1">
                    Copied!
                  </span>
                  <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="mt-5 sm:mt-6 flex justify-end">
              <button
                type="button"
                @click="showInviteModal = false"
                class="mr-3 inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="isInviting"
                class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                {{ isInviting ? 'Sending...' : 'Send Invitation' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Toggle User Status Confirmation Modal -->
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
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="toggleUserStatus"
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-amber-600 border border-transparent rounded-lg shadow-sm hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
              :disabled="isProcessingUser === userToToggle.id"
            >
              {{ isProcessingUser === userToToggle.id ? 'Processing...' : (userToToggle.is_active ? 'Disable' : 'Enable') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete User Confirmation Modal -->
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
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="deleteUser"
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
              :disabled="isProcessingDelete"
            >
              {{ isProcessingDelete ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Invitation Confirmation Modal -->
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
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="deleteInvitation"
              class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
              :disabled="isProcessingDelete"
            >
              {{ isProcessingDelete ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import UserGrid from '@/components/UserGrid.vue';
import InvitationsGrid from '@/components/InvitationsGrid.vue';

const userGrid = ref(null);

// Store
const authStore = useAuthStore()
const router = useRouter()

// State
const users = ref([])
const invitations = ref([])
const loading = ref(true)
const loadingInvitations = ref(true)
const showInviteModal = ref(false)
const inviteEmail = ref('')
const isInviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref(false)
const invitationLink = ref('')

const isProcessingUser = ref(null)
const isProcessingDelete = ref(false)
const copySuccess = ref(false)
const showUsedInvitations = ref(false)

// Toggle user state
const userToToggle = ref(null)

// Delete user modal
const deleteUserModal = ref(false)
const userToDelete = ref(null)

// Delete invitation modal
const deleteInvitationModal = ref(false)
const invitationToDelete = ref(null)

// Computed properties
const activeInvitations = computed(() => {
  return invitations.value.filter(inv => !inv.is_used).length
})

const filteredInvitations = computed(() => {
  // Only show used invitations if toggled on
  let filtered = [...invitations.value];

  if (!showUsedInvitations.value) {
    filtered = filtered.filter(inv => !inv.is_used);
  }

  // Sort invitations (recent first, non-used first if both types are shown)
  return filtered.sort((a, b) => {
    // First sort by usage status (non-used first) if showing both types
    if (showUsedInvitations.value && a.is_used !== b.is_used) {
      return a.is_used ? 1 : -1;
    }
    // Then sort by id (most recent first)
    return b.id - a.id;
  });
})

// Lifecycle hooks
onMounted(async () => {
  await Promise.all([
    loadUsers(),
    loadInvitations()
  ])
})

// Methods
async function loadUsers() {
  loading.value = true
  try {
    const response = await api.get('/user')
    users.value = response.data
  } catch (error) {
    console.error('Error loading users:', error)
  } finally {
    loading.value = false
  }
}

async function loadInvitations() {
  loadingInvitations.value = true
  try {
    const response = await api.get('/user/invitations')
    invitations.value = response.data
  } catch (error) {
    console.error('Error loading invitations:', error)
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
    // Use URLSearchParams for form data submission
    const formData = new URLSearchParams()
    formData.append('email', inviteEmail.value)

    const response = await api.post('/user/invite', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })

    // Generate invitation link without email parameter
    const baseUrl = window.location.origin
    invitationLink.value = `${baseUrl}/register?token=${response.data.token}`

    inviteSuccess.value = true

    // Refresh invitations list
    await loadInvitations()
  } catch (error) {
    console.error('Invite error:', error)
    if (error.response?.data?.detail) {
      inviteError.value = error.response.data.detail
    } else if (error.response?.data) {
      // Handle validation errors array
      const validationError = error.response.data[0]
      inviteError.value = validationError?.msg || 'Failed to send invitation.'
    } else {
      inviteError.value = 'Failed to send invitation. Please try again.'
    }
  } finally {
    isInviting.value = false
  }
}

// Copy text to clipboard with fallback
function copyGeneratedLink() {
  // Fallback for non-secure contexts or when the Clipboard API is not available
  const copyTextFallback = (text) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;

    // Make the textarea hidden
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);

    // Select the text
    textArea.focus();
    textArea.select();

    let success = false;
    try {
      // Execute the copy command
      success = document.execCommand('copy');
    } catch (err) {
      console.error('Unable to copy with fallback method', err);
    }

    // Remove the textarea
    document.body.removeChild(textArea);
    return success;
  };

  const baseUrl = window.location.origin;
  const token = invitationLink.value.split('token=')[1];
  const link = `${baseUrl}/register?token=${token}`;

  // Try the modern Clipboard API first
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(link)
      .then(() => {
        copySuccess.value = true;
        setTimeout(() => {
          copySuccess.value = false;
        }, 2000);
      })
      .catch(err => {
        console.error('Error with Clipboard API:', err);
        // Fall back to the older method
        const success = copyTextFallback(link);
        if (success) {
          copySuccess.value = true;
          setTimeout(() => {
            copySuccess.value = false;
          }, 2000);
        } else {
          alert(`Failed to copy. Please copy this link manually:\n${link}`);
        }
      });
  } else {
    // Use fallback for non-secure contexts
    const success = copyTextFallback(link);
    if (success) {
      copySuccess.value = true;
      setTimeout(() => {
        copySuccess.value = false;
      }, 2000);
    } else {
      alert(`Failed to copy. Please copy this link manually:\n${link}`);
    }
  }
}

// Toggle user confirmation and execution
function confirmToggleUserStatus(user) {
  userToToggle.value = user;
}

async function toggleUserStatus() {
  if (!userToToggle.value || isProcessingUser.value) return;

  isProcessingUser.value = userToToggle.value.id;

  try {
    await api.patch(`/user/${userToToggle.value.id}/toggle-status`);

    // Update the user in the list
    const index = users.value.findIndex(u => u.id === userToToggle.value.id);
    if (index !== -1) {
      users.value[index].is_active = !users.value[index].is_active;
    }

    // Refresh grid by reloading users
    if (userGrid.value) {
      await userGrid.value.loadUsers();
    }
    userToToggle.value = null;
  } catch (error) {
    console.error('Error toggling user status:', error);
  } finally {
    isProcessingUser.value = null;
  }
}

// Delete user functions
function confirmDeleteUser(user) {
  userToDelete.value = user;
  deleteUserModal.value = true;
}

async function deleteUser() {
  if (!userToDelete.value || isProcessingDelete.value) return;

  isProcessingDelete.value = true;

  try {
    await api.delete(`/user/${userToDelete.value.id}`);

    // Remove user from the list
    users.value = users.value.filter(user => user.id !== userToDelete.value.id);

    // Refresh grid
    if (userGrid.value) {
      await userGrid.value.loadUsers();
    }
    deleteUserModal.value = false;
    userToDelete.value = null;
  } catch (error) {
    console.error('Error deleting user:', error);
  } finally {
    isProcessingDelete.value = false;
  }
}

function cancelDelete() {
  deleteUserModal.value = false;
  userToDelete.value = null;
}

// Delete invitation functions
function confirmDeleteInvitation(invitation) {
  invitationToDelete.value = invitation;
  deleteInvitationModal.value = true;
}

async function deleteInvitation() {
  if (!invitationToDelete.value || isProcessingDelete.value) return;

  isProcessingDelete.value = true;

  try {
    await api.delete(`/user/invitations/${invitationToDelete.value.id}`);

    // Remove invitation from the list
    invitations.value = invitations.value.filter(inv => inv.id !== invitationToDelete.value.id);

    // Close the modal
    deleteInvitationModal.value = false;
    invitationToDelete.value = null;

    // Refresh invitations
    await loadInvitations();
  } catch (error) {
    console.error('Error deleting invitation:', error);
  } finally {
    isProcessingDelete.value = false;
  }
}

function cancelDeleteInvitation() {
  deleteInvitationModal.value = false;
  invitationToDelete.value = null;
}

function closeInviteModal() {
  if (!isInviting.value) {
    showInviteModal.value = false;
    if (inviteSuccess.value) {
      inviteEmail.value = '';
      inviteSuccess.value = false;
    }
  }
}
</script>
