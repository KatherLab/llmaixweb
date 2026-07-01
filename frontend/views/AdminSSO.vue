<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-900 dark:text-white">Single Sign-On (OIDC)</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Configure OpenID Connect identity providers. Users can sign in with these providers in
          addition to local passwords.
        </p>
      </div>
      <BaseButton variant="primary" @click="openCreate">
        <Plus class="w-4 h-4 inline-block mr-1" /> Add provider
      </BaseButton>
    </div>

    <div
      v-if="!ssoEnabled"
      class="p-4 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 text-sm"
    >
      SSO is globally disabled. Enable it in
      <router-link to="/admin/settings" class="font-semibold underline">Admin Settings</router-link>
      (SSO Enabled) to activate configured providers.
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingSpinner size="medium" />
    </div>
    <div v-else-if="error" class="py-4">
      <ErrorBanner :message="error" />
    </div>
    <div
      v-else-if="providers.length === 0"
      class="text-center py-12 text-slate-500 dark:text-slate-400 text-sm"
    >
      No identity providers configured.
    </div>

    <ul v-else class="space-y-3">
      <li
        v-for="p in providers"
        :key="p.id"
        class="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-between"
      >
        <div>
          <div class="flex items-center gap-2">
            <span class="font-semibold text-slate-900 dark:text-white">{{ p.name }}</span>
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="
                p.enabled
                  ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
              "
            >
              {{ p.enabled ? 'Enabled' : 'Disabled' }}
            </span>
            <span v-if="!p.has_secret" class="text-xs text-amber-600 dark:text-amber-400">
              no secret set
            </span>
          </div>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {{ p.issuer_url }} · client_id: {{ p.client_id }} · scopes: {{ p.scopes }}
          </p>
        </div>
        <div class="flex gap-2">
          <BaseButton variant="secondary" size="sm" @click="openEdit(p)">Edit</BaseButton>
          <BaseButton variant="secondary" size="sm" tone="red" @click="confirmDelete(p)">
            Delete
          </BaseButton>
        </div>
      </li>
    </ul>

    <!-- Create / Edit modal -->
    <BaseModal
      :open="showModal"
      :title="editing ? 'Edit provider' : 'Add provider'"
      size="md"
      @close="closeModal"
    >
      <form class="space-y-4" @submit.prevent="saveProvider">
        <div>
          <label :class="labelClass">Display name</label>
          <input v-model="form.name" type="text" :class="inputClass" placeholder="e.g. Google" />
        </div>
        <div>
          <label :class="labelClass">Issuer URL</label>
          <input
            v-model="form.issuer_url"
            type="url"
            :class="inputClass"
            placeholder="https://accounts.google.com"
          />
          <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
            The IdP base URL; discovery is fetched from
            <code>{issuer}/.well-known/openid-configuration</code>.
          </p>
        </div>
        <div>
          <label :class="labelClass">Client ID</label>
          <input v-model="form.client_id" type="text" :class="inputClass" />
        </div>
        <div>
          <label :class="labelClass">Client secret</label>
          <input
            v-model="form.client_secret"
            type="password"
            :class="inputClass"
            :placeholder="editing ? 'Leave blank to keep current' : 'Provider client secret'"
            autocomplete="new-password"
          />
        </div>
        <div>
          <label :class="labelClass">Scopes</label>
          <input v-model="form.scopes" type="text" :class="inputClass" />
        </div>
        <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input v-model="form.enabled" type="checkbox" class="rounded" />
          Enabled
        </label>
        <ErrorBanner v-if="formError" :message="formError" />
        <div class="flex justify-end gap-2 pt-2">
          <BaseButton variant="secondary" type="button" @click="closeModal">Cancel</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving">{{
            editing ? 'Save' : 'Create'
          }}</BaseButton>
        </div>
      </form>
    </BaseModal>

    <ConfirmationDialog
      :open="!!toDelete"
      title="Delete provider"
      :message="deleteMessage"
      confirm-text="Delete"
      confirm-variant="danger"
      :loading="deleting"
      @confirm="deleteProvider"
      @cancel="toDelete = null"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@lucide/vue'
import { ssoApi } from '@/services/ssoApi'
import { authApi } from '@/services/authApi'
import { useToast } from '@/composables/useToast'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, labelClass } from '@/utils/formStyles'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'

const toast = useToast()

const ssoEnabled = ref(false)
const providers = ref([])
const loading = ref(true)
const error = ref(null)

const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const form = reactive({
  name: '',
  issuer_url: '',
  client_id: '',
  client_secret: '',
  scopes: 'openid email profile',
  enabled: true,
})

const toDelete = ref(null)
const deleting = ref(false)

const deleteMessage = computed(() =>
  toDelete.value
    ? `Delete the "${toDelete.value.name}" provider? Linked users keep their accounts but can no longer sign in via this provider.`
    : '',
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

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await ssoApi.listProviders()
    providers.value = res.data
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to load providers.')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.issuer_url = ''
  form.client_id = ''
  form.client_secret = ''
  form.scopes = 'openid email profile'
  form.enabled = true
  formError.value = ''
}

function openCreate() {
  editing.value = null
  resetForm()
  showModal.value = true
}

function openEdit(p) {
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

function closeModal() {
  showModal.value = false
}

async function saveProvider() {
  saving.value = true
  formError.value = ''
  try {
    const payload = {
      name: form.name,
      issuer_url: form.issuer_url,
      client_id: form.client_id,
      scopes: form.scopes,
      enabled: form.enabled,
    }
    if (form.client_secret) payload.client_secret = form.client_secret
    if (editing.value) {
      await ssoApi.updateProvider(editing.value.id, payload)
      toast.success('Provider updated.')
    } else {
      if (!form.client_secret)
        throw { response: { data: { detail: 'Client secret is required.' } } }
      await ssoApi.createProvider(payload)
      toast.success('Provider created.')
    }
    showModal.value = false
    await load()
  } catch (e) {
    formError.value = extractErrorMessage(e, 'Failed to save provider.')
  } finally {
    saving.value = false
  }
}

function confirmDelete(p) {
  toDelete.value = p
}

async function deleteProvider() {
  if (!toDelete.value) return
  deleting.value = true
  try {
    await ssoApi.deleteProvider(toDelete.value.id)
    toast.success('Provider deleted.')
    toDelete.value = null
    await load()
  } catch (e) {
    toast.error(extractErrorMessage(e, 'Failed to delete provider.'))
  } finally {
    deleting.value = false
  }
}
</script>
