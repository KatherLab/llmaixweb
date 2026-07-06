<template>
  <div
    class="h-screen bg-gradient-to-br from-slate-100 via-white to-blue-100 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 flex flex-col"
  >
    <PageHeader
      title="User Management"
      subtitle="Manage user accounts, roles, and invitations."
      class="mb-6"
    >
      <template #icon>
        <Users class="w-5 h-5" aria-hidden="true" />
      </template>
      <template #actions>
        <BaseButton
          variant="primary"
          size="sm"
          class="dark:bg-blue-500 dark:hover:bg-blue-600"
          @click="showInviteModal = true"
        >
          + Invite User
        </BaseButton>
      </template>
    </PageHeader>

    <main class="flex-1 max-w-7xl mx-auto w-full px-2 py-2 sm:px-6 min-h-0">
      <div class="h-full flex flex-col gap-4">
        <!-- Users Section -->
        <GlassCard>
          <div class="h-full flex flex-col min-h-0">
            <div
              class="flex items-center justify-between mb-3 pb-3 border-b border-slate-200 dark:border-slate-700"
            >
              <h2 class="text-base font-semibold text-slate-900 dark:text-white">
                Users
                <span
                  class="ml-2 text-xs bg-blue-50 dark:bg-slate-700 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full border border-blue-100 dark:border-slate-600"
                  >{{ users.length }} total</span
                >
              </h2>
              <SearchInput v-model="userSearch" placeholder="Search users…" />
            </div>
            <div class="flex-1 min-h-0">
              <div v-if="loading" class="flex justify-center py-12">
                <LoadingSpinner size="medium" />
              </div>
              <div v-else-if="loadUsersError" class="py-8">
                <ErrorBanner :message="loadUsersError" />
                <div class="mt-3 text-center">
                  <BaseButton variant="secondary" size="sm" @click="loadUsers"
                    >Try again</BaseButton
                  >
                </div>
              </div>
              <UserGrid
                v-else
                :row-data="users"
                :search="userSearch"
                @edit-requested="openEditModal"
              />
            </div>
          </div>
        </GlassCard>

        <!-- Invitations Section -->
        <GlassCard>
          <div class="h-full flex flex-col min-h-0">
            <div
              class="flex items-center justify-between mb-3 pb-3 border-b border-slate-200 dark:border-slate-700"
            >
              <h2 class="text-base font-semibold text-slate-900 dark:text-white">
                Invitations
                <label class="ml-4 text-xs font-medium text-slate-600 dark:text-slate-400">
                  <input
                    v-model="showUsedInvitations"
                    type="checkbox"
                    class="mr-2 rounded border-slate-300 dark:border-slate-600 text-blue-600 dark:text-blue-400"
                  />Show used
                </label>
              </h2>
              <div class="flex items-center gap-4">
                <span
                  class="text-xs bg-blue-50 dark:bg-slate-700 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full border border-blue-100 dark:border-slate-600"
                  >{{ activeInvitations }} active</span
                >
                <SearchInput v-model="invitationSearch" placeholder="Search invitations…" />
              </div>
            </div>
            <div class="flex-1 min-h-0">
              <div v-if="loadingInvitations" class="flex justify-center py-12">
                <LoadingSpinner size="medium" />
              </div>
              <div v-else-if="loadInvitationsError" class="py-8">
                <ErrorBanner :message="loadInvitationsError" />
                <div class="mt-3 text-center">
                  <BaseButton variant="secondary" size="sm" @click="loadInvitations">
                    Try again
                  </BaseButton>
                </div>
              </div>
              <InvitationGrid
                v-else
                :row-data="filteredInvitations"
                :search="invitationSearch"
                @delete-requested="confirmDeleteInvitation"
              />
            </div>
          </div>
        </GlassCard>
      </div>
    </main>

    <!-- Invite User Modal -->
    <InviteUserModal
      :open="showInviteModal"
      @close="showInviteModal = false"
      @invited="loadInvitations"
    />

    <!-- Edit User Modal -->
    <EditUserModal
      :open="!!editUser"
      :user="editUser"
      :current-user-id="currentUserId"
      @close="editUser = null"
      @saved="handleUserSaved"
      @delete-requested="handleDeleteRequested"
    />

    <!-- Delete User Confirmation -->
    <ConfirmationDialog
      :open="deleteUserModal"
      title="Delete User"
      :message="deleteUserMessage"
      confirm-text="Permanently Delete"
      confirm-variant="danger"
      :loading="isProcessingDelete"
      @confirm="deleteUser"
      @cancel="cancelDelete"
    />

    <!-- Delete Invitation Confirmation -->
    <ConfirmationDialog
      :open="deleteInvitationModal"
      title="Delete Invitation"
      :message="deleteInvitationMessage"
      confirm-text="Delete"
      confirm-variant="danger"
      :loading="isProcessingDelete"
      @confirm="deleteInvitation"
      @cancel="cancelDeleteInvitation"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { Users } from '@lucide/vue'
import UserGrid from '@/components/admin/UserGrid.vue'
import InvitationGrid from '@/components/admin/InvitationGrid.vue'
import InviteUserModal from '@/components/admin/InviteUserModal.vue'
import EditUserModal from '@/components/admin/EditUserModal.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import SearchInput from '@/components/common/SearchInput.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import GlassCard from '@/components/common/GlassCard.vue'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { UserResponse, InvitationResponse } from '@/types'

const toast = useToast()

const currentUserId = ref<number | null>(null)

const users = ref<UserResponse[]>([])
const loading = ref<boolean>(true)
const loadUsersError = ref<string | null>(null)
const userSearch = ref<string>('')

const invitations = ref<InvitationResponse[]>([])
const loadingInvitations = ref<boolean>(true)
const loadInvitationsError = ref<string | null>(null)
const invitationSearch = ref<string>('')
const showUsedInvitations = ref<boolean>(false)

// --- Invite modal ---
const showInviteModal = ref<boolean>(false)

// --- Edit modal ---
const editUser = ref<UserResponse | null>(null)

// --- Delete state (shared by user + invitation delete) ---
const deleteUserModal = ref<boolean>(false)
const userToDelete = ref<UserResponse | null>(null)
const deleteInvitationModal = ref<boolean>(false)
const invitationToDelete = ref<InvitationResponse | null>(null)
const isProcessingDelete = ref<boolean>(false)

const activeInvitations = computed<number>(
  () => invitations.value.filter((inv) => !inv.is_used).length,
)
const filteredInvitations = computed<InvitationResponse[]>(() => {
  let filtered = [...invitations.value]
  if (!showUsedInvitations.value) {
    filtered = filtered.filter((inv) => !inv.is_used)
  }
  return filtered.sort((a, b) => {
    if (showUsedInvitations.value && a.is_used !== b.is_used) {
      return a.is_used ? 1 : -1
    }
    return b.id - a.id
  })
})

const deleteUserMessage = computed<string>(() => {
  if (!userToDelete.value) return ''
  return `This will permanently delete the user account and all associated data, including all projects owned by this user (files, documents, schemas, prompts, trials, evaluations) and uploaded files removed from storage.\n\nAre you sure you want to delete this user?\n${userToDelete.value.full_name} (${userToDelete.value.email})`
})

const deleteInvitationMessage = computed<string>(() => {
  if (!invitationToDelete.value) return ''
  return `Are you sure you want to delete this invitation? This action cannot be undone.\n${invitationToDelete.value.email}`
})

onMounted(async () => {
  try {
    const me = await usersApi.me()
    currentUserId.value = me.data.id
  } catch {
    /* ignore */
  }
  await Promise.all([loadUsers(), loadInvitations()])
})

async function loadUsers(): Promise<void> {
  loading.value = true
  loadUsersError.value = null
  try {
    const response = await usersApi.list()
    users.value = response.data
  } catch (error) {
    loadUsersError.value = extractErrorMessage(error, 'Failed to load users.')
  } finally {
    loading.value = false
  }
}

async function loadInvitations(): Promise<void> {
  loadingInvitations.value = true
  loadInvitationsError.value = null
  try {
    const response = await usersApi.listInvitations()
    invitations.value = response.data
  } catch (error) {
    loadInvitationsError.value = extractErrorMessage(error, 'Failed to load invitations.')
  } finally {
    loadingInvitations.value = false
  }
}

// --- Edit User ---
function openEditModal(user: UserResponse): void {
  editUser.value = user
}

function handleUserSaved(updatedUser: UserResponse): void {
  const idx = users.value.findIndex((u) => u.id === updatedUser.id)
  if (idx !== -1) {
    users.value[idx] = updatedUser
    users.value = [...users.value]
  }
  editUser.value = updatedUser
}

function handleDeleteRequested(user: UserResponse): void {
  userToDelete.value = user
  deleteUserModal.value = true
}

// --- Delete user ---
async function deleteUser(): Promise<void> {
  if (!userToDelete.value || isProcessingDelete.value) return
  isProcessingDelete.value = true
  const target = userToDelete.value
  const userName = target.full_name
  try {
    await usersApi.delete(target.id)
    users.value = users.value.filter((u) => u.id !== target.id)
    toast.success(`User "${userName}" deleted successfully.`)
    deleteUserModal.value = false
    userToDelete.value = null
    editUser.value = null // close edit modal too
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to delete user.'))
  } finally {
    isProcessingDelete.value = false
  }
}

function cancelDelete(): void {
  deleteUserModal.value = false
  userToDelete.value = null
}

// --- Delete invitation ---
function confirmDeleteInvitation(invitation: InvitationResponse): void {
  invitationToDelete.value = invitation
  deleteInvitationModal.value = true
}

async function deleteInvitation(): Promise<void> {
  if (!invitationToDelete.value || isProcessingDelete.value) return
  isProcessingDelete.value = true
  const target = invitationToDelete.value
  try {
    await usersApi.deleteInvitation(target.id)
    invitations.value = invitations.value.filter((inv) => inv.id !== target.id)
    toast.success(`Invitation for "${target.email}" deleted.`)
    deleteInvitationModal.value = false
    invitationToDelete.value = null
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to delete invitation.'))
  } finally {
    isProcessingDelete.value = false
  }
}

function cancelDeleteInvitation(): void {
  deleteInvitationModal.value = false
  invitationToDelete.value = null
}
</script>
