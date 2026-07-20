<template>
  <div class="space-y-6">
    <PageHeader :title="$t('admin.sso.title')" :subtitle="$t('admin.sso.subtitle')" class="mb-6">
      <template #icon>
        <KeyRound class="w-5 h-5" aria-hidden="true" />
      </template>
      <template #actions>
        <BaseButton variant="primary" @click="openCreate">
          <Plus class="w-4 h-4" /> {{ $t('admin.sso.add_provider') }}
        </BaseButton>
      </template>
    </PageHeader>

    <Callout v-if="!ssoEnabled" variant="warning" class="text-sm">
      {{ $t('admin.sso.globally_disabled_before') }}
      <router-link to="/admin/settings" class="font-semibold underline">{{
        $t('admin.sso.admin_settings_link')
      }}</router-link>
      {{ $t('admin.sso.globally_disabled_after') }}
    </Callout>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>
    <div v-else-if="error" class="py-4">
      <ErrorBanner :message="error" />
    </div>
    <EmptyState
      v-else-if="providers.length === 0"
      :title="$t('admin.sso.empty_title')"
      :description="$t('admin.sso.empty_description')"
    >
      <template #icon>
        <KeyRound class="h-12 w-12 mx-auto text-content-subtle" aria-hidden="true" />
      </template>
    </EmptyState>

    <ul v-else class="space-y-3">
      <li
        v-for="p in providers"
        :key="p.id"
        class="p-4 rounded-modal border border-default bg-surface flex items-center justify-between"
      >
        <div>
          <div class="flex items-center gap-2">
            <span class="font-semibold text-content">{{ p.name }}</span>
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="
                p.enabled
                  ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                  : 'bg-surface-sunken text-content-muted'
              "
            >
              {{ p.enabled ? $t('admin.sso.enabled') : $t('admin.sso.disabled') }}
            </span>
            <span v-if="!p.has_secret" class="text-xs text-amber-600 dark:text-amber-400">
              {{ $t('admin.sso.no_secret_set') }}
            </span>
          </div>
          <p class="text-xs text-content-subtle mt-1">
            {{ p.issuer_url }} · client_id: {{ p.client_id }} · scopes: {{ p.scopes }}
          </p>
        </div>
        <div class="flex gap-2">
          <BaseButton variant="secondary" size="sm" @click="openEdit(p)">{{
            $t('admin.sso.edit')
          }}</BaseButton>
          <BaseButton variant="secondary" size="sm" tone="red" @click="confirmDelete(p)">
            {{ $t('admin.sso.delete') }}
          </BaseButton>
        </div>
      </li>
    </ul>

    <!-- Create / Edit modal -->
    <BaseModal
      :open="showModal"
      :title="editing ? $t('admin.sso.edit_provider') : $t('admin.sso.add_provider')"
      size="md"
      @close="closeModal"
    >
      <form class="space-y-4" @submit.prevent="saveProvider">
        <div>
          <label :class="labelClass" for="sso-provider-name">{{
            $t('admin.sso.form.display_name')
          }}</label>
          <input
            id="sso-provider-name"
            v-model="form.name"
            type="text"
            :class="inputClass"
            :placeholder="$t('admin.sso.form.display_name_placeholder')"
          />
        </div>
        <div>
          <label :class="labelClass" for="sso-provider-issuer-url">{{
            $t('admin.sso.form.issuer_url')
          }}</label>
          <input
            id="sso-provider-issuer-url"
            v-model="form.issuer_url"
            type="url"
            :class="inputClass"
            placeholder="https://accounts.google.com"
          />
          <p class="mt-1 text-xs text-content-subtle">
            {{ $t('admin.sso.form.issuer_help') }}
            <code>{issuer}/.well-known/openid-configuration</code>.
          </p>
        </div>
        <div>
          <label :class="labelClass" for="sso-provider-client-id">{{
            $t('admin.sso.form.client_id')
          }}</label>
          <input
            id="sso-provider-client-id"
            v-model="form.client_id"
            type="text"
            :class="inputClass"
          />
        </div>
        <div>
          <label :class="labelClass" for="sso-provider-client-secret">{{
            $t('admin.sso.form.client_secret')
          }}</label>
          <input
            id="sso-provider-client-secret"
            v-model="form.client_secret"
            type="password"
            :class="inputClass"
            :placeholder="
              editing
                ? $t('admin.sso.form.client_secret_keep')
                : $t('admin.sso.form.client_secret_placeholder')
            "
            autocomplete="new-password"
          />
        </div>
        <div>
          <label :class="labelClass" for="sso-provider-scopes">{{
            $t('admin.sso.form.scopes')
          }}</label>
          <input id="sso-provider-scopes" v-model="form.scopes" type="text" :class="inputClass" />
        </div>
        <label class="flex items-center gap-2 text-sm text-content-muted">
          <input v-model="form.enabled" type="checkbox" class="rounded" />
          {{ $t('admin.sso.form.enabled') }}
        </label>
        <ErrorBanner v-if="formError" :message="formError" />
        <div class="flex justify-end gap-2 pt-2">
          <BaseButton variant="secondary" type="button" @click="closeModal">{{
            $t('admin.sso.cancel')
          }}</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving">{{
            editing ? $t('admin.sso.save') : $t('admin.sso.create')
          }}</BaseButton>
        </div>
      </form>
    </BaseModal>

    <ConfirmationDialog
      :open="!!toDelete"
      :title="$t('admin.sso.delete_provider_title')"
      :message="deleteMessage"
      :confirm-text="$t('admin.sso.delete')"
      confirm-variant="danger"
      :loading="deleting"
      @confirm="deleteProvider"
      @cancel="toDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { KeyRound, Plus } from '@lucide/vue'
import { ssoApi } from '@/services/ssoApi'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, labelClass } from '@/utils/formStyles'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import Callout from '@/components/common/Callout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import type { IdentityProviderResponse } from '@/types'

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()

const ssoEnabled = ref<boolean>(false)
const providers = ref<IdentityProviderResponse[]>([])
const loading = ref<boolean>(true)
const error = ref<string | null>(null)

const showModal = ref<boolean>(false)
const editing = ref<IdentityProviderResponse | null>(null)
const saving = ref<boolean>(false)
const formError = ref<string>('')
const form = reactive<{
  name: string
  issuer_url: string
  client_id: string
  client_secret: string
  scopes: string
  enabled: boolean
}>({
  name: '',
  issuer_url: '',
  client_id: '',
  client_secret: '',
  scopes: 'openid email profile',
  enabled: true,
})

const toDelete = ref<IdentityProviderResponse | null>(null)
const deleting = ref<boolean>(false)

const deleteMessage = computed<string>(() =>
  toDelete.value ? t('admin.sso.delete_provider_message', { name: toDelete.value.name }) : '',
)

onMounted(async () => {
  try {
    const res = await authApi.getSettings()
    ssoEnabled.value = !!res.data.sso_enabled
  } catch {
    /* ignore */
  }
  await load()
})

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await ssoApi.listProviders()
    providers.value = res.data
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.sso.errors.load'))
  } finally {
    loading.value = false
  }
}

function resetForm(): void {
  form.name = ''
  form.issuer_url = ''
  form.client_id = ''
  form.client_secret = ''
  form.scopes = 'openid email profile'
  form.enabled = true
  formError.value = ''
}

function openCreate(): void {
  editing.value = null
  resetForm()
  showModal.value = true
}

function openEdit(p: IdentityProviderResponse): void {
  editing.value = p
  form.name = p.name
  form.issuer_url = p.issuer_url
  form.client_id = p.client_id
  form.client_secret = ''
  form.scopes = p.scopes
  form.enabled = p.enabled
  formError.value = ''
  showModal.value = true
}

function closeModal(): void {
  showModal.value = false
}

async function saveProvider(): Promise<void> {
  saving.value = true
  formError.value = ''
  try {
    const payload: {
      name: string
      issuer_url: string
      client_id: string
      scopes: string
      enabled: boolean
      client_secret?: string
    } = {
      name: form.name,
      issuer_url: form.issuer_url,
      client_id: form.client_id,
      scopes: form.scopes,
      enabled: form.enabled,
    }
    if (form.client_secret) payload.client_secret = form.client_secret
    if (editing.value) {
      await ssoApi.updateProvider(editing.value.id, payload)
      toast.success(t('admin.sso.toast.updated'))
    } else {
      if (!form.client_secret)
        throw { response: { data: { detail: t('admin.sso.errors.client_secret_required') } } }
      await ssoApi.createProvider({ ...payload, client_secret: form.client_secret })
      toast.success(t('admin.sso.toast.created'))
    }
    showModal.value = false
    await load()
  } catch (e) {
    formError.value = extractErrorMessage(e, t('admin.sso.errors.save'))
  } finally {
    saving.value = false
  }
}

function confirmDelete(p: IdentityProviderResponse): void {
  toDelete.value = p
}

async function deleteProvider(): Promise<void> {
  if (!toDelete.value) return
  deleting.value = true
  try {
    await ssoApi.deleteProvider(toDelete.value.id)
    toast.success(t('admin.sso.toast.deleted'))
    toDelete.value = null
    await load()
  } catch (e) {
    toast.error(extractErrorMessage(e, t('admin.sso.errors.delete')))
  } finally {
    deleting.value = false
  }
}
</script>
