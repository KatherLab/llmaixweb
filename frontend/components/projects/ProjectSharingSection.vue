<!-- frontend/components/projects/ProjectSharingSection.vue -->
<template>
  <div>
    <h3 class="text-sm font-semibold text-content-muted uppercase tracking-wide mb-3">
      {{ $t('projects.share.title') }}
    </h3>

    <!-- Add a collaborator. Owner-only: a write-level collaborator can change
         the project but not who else can reach it. -->
    <form v-if="canManage" class="mb-4" @submit.prevent="addShare">
      <div class="flex flex-col sm:flex-row gap-2">
        <div class="flex-1">
          <label :for="emailFieldId" class="sr-only">{{ $t('projects.share.email_label') }}</label>
          <input
            :id="emailFieldId"
            v-model="email"
            type="email"
            autocomplete="off"
            :class="inputClass"
            :placeholder="$t('projects.share.email_placeholder')"
            :disabled="isAdding"
          />
        </div>
        <div class="sm:w-40">
          <label :for="permissionFieldId" class="sr-only">
            {{ $t('projects.share.permission_label') }}
          </label>
          <select
            :id="permissionFieldId"
            v-model="permission"
            :class="selectClass"
            :disabled="isAdding"
          >
            <option value="read">{{ $t('projects.share.permission.read') }}</option>
            <option value="write">{{ $t('projects.share.permission.write') }}</option>
          </select>
        </div>
        <BaseButton type="submit" :loading="isAdding" :disabled="!email.trim() || isAdding">
          <UserPlus class="w-4 h-4" />
          {{ $t('projects.share.add') }}
        </BaseButton>
      </div>
      <p class="mt-2 text-xs text-content-subtle">
        {{ $t('projects.share.email_hint') }}
      </p>
    </form>

    <ErrorBanner v-if="error" :message="error" dismissable class="mb-3" @dismiss="error = ''" />

    <!-- People with access -->
    <div class="rounded-card border border-default-border divide-y divide-default-border">
      <!-- The owner is not a share row, but leaving them out of the list makes
           it read as "nobody has access" on an unshared project. -->
      <div class="flex items-center gap-3 px-3 py-2.5">
        <div
          class="w-8 h-8 rounded-full bg-primary-soft text-primary flex items-center justify-center text-xs font-semibold shrink-0"
        >
          {{ initials(owner?.full_name, owner?.email) }}
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-content truncate">
            {{ owner?.full_name || owner?.email || $t('projects.share.unknown_user') }}
          </p>
          <p class="text-xs text-content-subtle truncate">{{ owner?.email }}</p>
        </div>
        <span class="text-xs font-medium text-content-muted shrink-0">
          {{ $t('projects.share.permission.owner') }}
        </span>
      </div>

      <div v-if="isLoading" class="px-3 py-4 flex items-center gap-2 text-sm text-content-subtle">
        <LoadingSpinner size="small" label="" inline />
        {{ $t('projects.share.loading') }}
      </div>

      <template v-else-if="shares.length">
        <div v-for="share in shares" :key="share.id" class="flex items-center gap-3 px-3 py-2.5">
          <div
            class="w-8 h-8 rounded-full bg-surface-muted text-content-muted flex items-center justify-center text-xs font-semibold shrink-0"
          >
            {{ initials(share.user.full_name, share.user.email) }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-content truncate">
              {{ share.user.full_name || share.user.email }}
            </p>
            <p class="text-xs text-content-subtle truncate">{{ share.user.email }}</p>
          </div>

          <!-- Width lives on the wrapper, not the <select>: `selectClass` starts
               with `w-full`, so a `w-32` on the element itself loses the Tailwind
               ordering fight and the select stretches over the remove button. -->
          <div v-if="canManage" class="w-32 shrink-0">
            <select
              :value="share.permission"
              :class="[selectClass, '!px-2 !py-1 text-xs']"
              :disabled="busyShareId === share.id"
              :aria-label="$t('projects.share.permission_label')"
              @change="changePermission(share, ($event.target as HTMLSelectElement).value)"
            >
              <option value="read">{{ $t('projects.share.permission.read') }}</option>
              <option value="write">{{ $t('projects.share.permission.write') }}</option>
            </select>
          </div>
          <span v-else class="text-xs font-medium text-content-muted shrink-0">
            {{ $t(`projects.share.permission.${share.permission}`) }}
          </span>

          <BaseButton
            v-if="canManage"
            variant="icon"
            tone="red"
            :disabled="busyShareId === share.id"
            :aria-label="$t('projects.share.remove')"
            :title="$t('projects.share.remove')"
            @click="confirmRemove(share)"
          >
            <X class="w-4 h-4" />
          </BaseButton>
        </div>
      </template>

      <p v-else class="px-3 py-4 text-sm text-content-subtle">
        {{ $t('projects.share.empty') }}
      </p>
    </div>

    <ConfirmationDialog
      :open="!!pendingRemoval"
      :title="$t('projects.share.remove_title')"
      :message="
        $t('projects.share.remove_message', {
          name: pendingRemoval?.user.full_name || pendingRemoval?.user.email || '',
        })
      "
      :confirm-text="$t('projects.share.remove')"
      confirm-variant="danger"
      :loading="busyShareId === pendingRemoval?.id"
      @confirm="removeShare"
      @cancel="pendingRemoval = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import { UserPlus, X } from '@lucide/vue'
import BaseButton from '@/components/common/BaseButton.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { projectsApi } from '@/services/projectsApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, selectClass } from '@/utils/formStyles'
import type { ProjectPermission, ProjectShare, UserPublic } from '@/types'

interface Props {
  projectId: number | string
  /** The project owner, rendered as the (non-removable) first row. */
  owner: UserPublic | null
  /** Only the owner may add, re-permission, or revoke shares. */
  canManage: boolean
  /** Load the list only once the containing modal is actually open. */
  open: boolean
}

const props = defineProps<Props>()
const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

const emailFieldId = useId()
const permissionFieldId = useId()

const shares = ref<ProjectShare[]>([])
const isLoading = ref(false)
const isAdding = ref(false)
const busyShareId = ref<number | null>(null)
const pendingRemoval = ref<ProjectShare | null>(null)
const email = ref('')
const permission = ref<ProjectPermission>('read')
const error = ref('')

function initials(fullName?: string | null, email?: string | null): string {
  const source = (fullName || email || '?').trim()
  const parts = source.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return source.slice(0, 2).toUpperCase()
}

async function loadShares(): Promise<void> {
  isLoading.value = true
  error.value = ''
  try {
    const { data } = await projectsApi.listShares(props.projectId)
    shares.value = data
  } catch (err) {
    error.value = extractErrorMessage(err, t('projects.share.load_error'))
  } finally {
    isLoading.value = false
  }
}

async function addShare(): Promise<void> {
  const trimmed = email.value.trim()
  if (!trimmed) return
  isAdding.value = true
  error.value = ''
  try {
    await projectsApi.addShare(props.projectId, {
      email: trimmed,
      permission: permission.value,
    })
    email.value = ''
    permission.value = 'read'
    toast.success(t('projects.share.add_success'))
    await loadShares()
  } catch (err) {
    error.value = extractErrorMessage(err, t('projects.share.add_error'))
  } finally {
    isAdding.value = false
  }
}

async function changePermission(share: ProjectShare, value: string): Promise<void> {
  const next = value as ProjectPermission
  if (next === share.permission) return
  busyShareId.value = share.id
  error.value = ''
  try {
    const { data } = await projectsApi.updateShare(props.projectId, share.id, {
      permission: next,
    })
    // Replace in place so the row keeps its position in the list.
    const index = shares.value.findIndex((s) => s.id === share.id)
    if (index !== -1) shares.value[index] = data
    toast.success(t('projects.share.update_success'))
  } catch (err) {
    error.value = extractErrorMessage(err, t('projects.share.update_error'))
    // The <select> is uncontrolled during the request; re-sync it with the
    // server state so a failed change doesn't leave a lie on screen.
    await loadShares()
  } finally {
    busyShareId.value = null
  }
}

async function removeShare(): Promise<void> {
  const share = pendingRemoval.value
  if (!share) return
  busyShareId.value = share.id
  error.value = ''
  try {
    await projectsApi.removeShare(props.projectId, share.id)
    shares.value = shares.value.filter((s) => s.id !== share.id)
    toast.success(t('projects.share.remove_success'))
  } catch (err) {
    error.value = extractErrorMessage(err, t('projects.share.remove_error'))
  } finally {
    busyShareId.value = null
    pendingRemoval.value = null
  }
}

function confirmRemove(share: ProjectShare): void {
  pendingRemoval.value = share
}

watch(
  () => [props.open, props.projectId] as const,
  ([isOpen]) => {
    if (isOpen) loadShares()
  },
  { immediate: true },
)
</script>
