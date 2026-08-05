<template>
  <div>
    <PageHeader
      :title="$t('admin.settings.title')"
      :subtitle="$t('admin.settings.subtitle')"
      class="mb-6"
    >
      <template #icon>
        <CircleDot class="w-5 h-5" aria-hidden="true" />
      </template>
    </PageHeader>

    <!-- Category Tabs -->
    <BaseTabGroup v-model="activeTab" :tabs="categoryTabs" class="mb-6" />

    <!-- Settings Form -->
    <form v-if="!loading" class="max-w-3xl mx-auto" @submit.prevent="save">
      <div
        v-for="(val, key) in filteredSettings"
        :key="key"
        class="grid grid-cols-1 md:grid-cols-3 gap-3 items-center py-2 border-b border-default"
      >
        <!-- Label & Description -->
        <div class="font-semibold flex flex-col text-content">
          <span>{{ val.label }}</span>
          <span class="text-xs text-content-subtle">{{ val.description }}</span>
        </div>

        <!-- Value Display -->
        <div class="text-xs text-content-subtle break-all">
          <template v-if="val.secret">
            <span v-if="val.is_set" class="text-green-700 dark:text-green-400">{{
              $t('admin.settings.set')
            }}</span>
            <span v-else class="text-red-500 dark:text-red-400">{{
              $t('admin.settings.not_set')
            }}</span>
          </template>
          <template v-else>
            <span v-if="val.override !== undefined && val.override !== null">
              <s>{{ val.original }}</s>
              <span class="ml-1 text-primary font-semibold">{{ val.override }}</span>
            </span>
            <span v-else>{{ val.original }}</span>
          </template>
        </div>

        <!-- Input/Edit Area -->
        <div>
          <!-- Read-only: .env only -->
          <template v-if="val.readonly">
            <div class="text-content-subtle flex flex-col gap-1">
              <span class="flex items-center gap-1">
                <Lock class="w-4 h-4 text-content-subtle" />
                {{ $t('admin.settings.set_in') }} <code>.env</code>
              </span>
              <span class="text-xs"
                >{{ $t('admin.settings.example') }} <code>{{ key }}={{ val.original }}</code></span
              >
            </div>
          </template>

          <!-- Editable Secret -->
          <template v-else-if="val.secret">
            <div class="flex flex-col gap-1">
              <div class="flex gap-2 mt-1">
                <BaseButton
                  type="button"
                  variant="secondary"
                  size="sm"
                  @click="showSecretInput[key] = !showSecretInput[key]"
                >
                  {{ val.is_set ? $t('admin.settings.update') : $t('admin.settings.set_action') }}
                </BaseButton>
                <BaseButton
                  v-if="val.is_set"
                  type="button"
                  variant="danger"
                  size="sm"
                  @click="pendingClearKey = key"
                >
                  {{ $t('admin.settings.clear') }}
                </BaseButton>
              </div>
              <div v-if="showSecretInput[key]" class="mt-2 flex gap-2">
                <input
                  v-model="secretDraft[key]"
                  type="password"
                  autocomplete="new-password"
                  :name="key.toLowerCase()"
                  data-1p-ignore
                  data-lpignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  :class="[inputClass, 'flex-1']"
                  :placeholder="$t('admin.settings.enter_new_value')"
                />
                <BaseButton type="button" variant="primary" size="sm" @click="saveSecret(key)">
                  {{ $t('admin.settings.save') }}
                </BaseButton>
                <BaseButton
                  type="button"
                  variant="secondary"
                  size="sm"
                  @click="cancelSecretInput(key)"
                >
                  {{ $t('admin.settings.cancel') }}
                </BaseButton>
              </div>
            </div>
          </template>

          <!-- Boolean -->
          <template v-else-if="val.type === 'bool'">
            <div class="flex items-center gap-2">
              <input v-model="draft[key]" type="checkbox" class="w-5 h-5 text-primary" />
              <BaseButton
                v-if="val.overridden"
                type="button"
                variant="danger"
                size="sm"
                @click="pendingRevertKey = key"
              >
                {{ $t('admin.settings.revert') }}
              </BaseButton>
            </div>
          </template>
          <!-- Integer -->
          <template v-else-if="val.type === 'int'">
            <div class="flex items-center gap-2">
              <input v-model.number="draft[key]" type="number" :class="[inputClass, 'flex-1']" />
              <BaseButton
                v-if="val.overridden"
                type="button"
                variant="danger"
                size="sm"
                @click="pendingRevertKey = key"
              >
                {{ $t('admin.settings.revert') }}
              </BaseButton>
            </div>
          </template>
          <!-- String (default) -->
          <template v-else>
            <div class="flex items-center gap-2">
              <input v-model="draft[key]" type="text" :class="[inputClass, 'flex-1']" />
              <BaseButton
                v-if="val.overridden"
                type="button"
                variant="danger"
                size="sm"
                @click="pendingRevertKey = key"
              >
                {{ $t('admin.settings.revert') }}
              </BaseButton>
            </div>
          </template>
        </div>
      </div>
      <div class="mt-8 flex flex-wrap gap-4">
        <BaseButton type="submit" variant="primary" :loading="saving" :disabled="saving">
          {{ saving ? $t('admin.settings.saving') : $t('admin.settings.save') }}
        </BaseButton>
        <BaseButton variant="secondary" @click="resetDraft">
          {{ $t('admin.settings.reset') }}
        </BaseButton>
        <!--
          Only on the Email tab: SMTP is the one category whose settings can look
          correct and still not deliver, so it gets a way to prove itself. Sends
          to the signed-in admin's own address.
        -->
        <BaseButton
          v-if="activeTab === 'Email'"
          type="button"
          variant="secondary"
          :loading="sendingTestEmail"
          :disabled="sendingTestEmail"
          @click="sendTestEmail"
        >
          {{ $t('admin.settings.send_test_email') }}
        </BaseButton>
      </div>
      <div v-if="success" class="mt-5 text-green-600 dark:text-green-400 font-semibold">
        {{ $t('admin.settings.saved') }}
      </div>
      <div v-if="error" class="mt-5 text-red-600 dark:text-red-400 font-semibold">{{ error }}</div>
    </form>
    <div v-else class="py-12 flex justify-center">
      <LoadingSpinner />
    </div>

    <!-- Confirm removing a system-wide override -->
    <ConfirmationDialog
      :open="pendingRevertKey !== null"
      :title="$t('admin.settings.revert_dialog.title')"
      :message="$t('admin.settings.revert_dialog.message', { key: pendingRevertKey ?? '' })"
      :confirm-text="$t('admin.settings.revert')"
      confirm-variant="danger"
      @confirm="confirmRevert"
      @cancel="pendingRevertKey = null"
    />

    <!-- Confirm clearing a stored secret -->
    <ConfirmationDialog
      :open="pendingClearKey !== null"
      :title="$t('admin.settings.clear_dialog.title')"
      :message="$t('admin.settings.clear_dialog.message', { key: pendingClearKey ?? '' })"
      :confirm-text="$t('admin.settings.clear')"
      confirm-variant="danger"
      @confirm="confirmClear"
      @cancel="pendingClearKey = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { CircleDot, Lock } from '@lucide/vue'
import { adminApi } from '@/services/adminApi'
import { useToast } from '@/composables/useToast'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import ConfirmationDialog from '@/components/common/ConfirmationDialog.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass } from '@/utils/formStyles'
import type { AdminSettings, AdminSettingEntry } from '@/types'

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()
const route = useRoute()
const router = useRouter()

const settings = reactive<AdminSettings>({})
// Draft values are a mix of booleans, numbers, and strings.
const draft = reactive<Record<string, string | number | boolean>>({})
const loading = ref<boolean>(true)
const saving = ref<boolean>(false)
const sendingTestEmail = ref<boolean>(false)
const error = ref<string>('')
const success = ref<boolean>(false)

// Preferred tab ordering. Tabs are derived from the categories actually
// present in the settings payload (so every setting stays reachable without a
// catch-all "All" tab); any category not listed here is appended afterwards.
const CATEGORY_ORDER: string[] = [
  'General',
  'Security',
  'SSO',
  'OpenAI',
  'OCR',
  'docling-serve',
  'Preprocessing',
  'Storage',
  'Database',
  'Email',
]

const categoryTabs = computed(() => {
  const present = Array.from(
    new Set(
      Object.values(settings)
        .map((v) => v.category)
        .filter((c): c is string => !!c),
    ),
  )
  present.sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a)
    const ib = CATEGORY_ORDER.indexOf(b)
    return (ia === -1 ? Number.MAX_SAFE_INTEGER : ia) - (ib === -1 ? Number.MAX_SAFE_INTEGER : ib)
  })
  return present.map((cat) => ({ label: cat, value: cat }))
})
const activeTab = ref<string>('')

// Mirror the active category into ?tab= so a refresh keeps the sub-tab. The
// param is omitted for the default (first) category; replace, not push — tab
// flips shouldn't pollute history, and other query params are preserved.
watch(activeTab, (tab) => {
  const defaultTab = categoryTabs.value[0]?.value
  const desired = tab && tab !== defaultTab ? tab : undefined
  if ((route.query.tab ?? undefined) === desired) return
  router.replace({ query: { ...route.query, tab: desired } })
})

const filteredSettings = computed<AdminSettings>(() =>
  Object.fromEntries(Object.entries(settings).filter(([_k, v]) => v.category === activeTab.value)),
)

// --- Secrets state ---
const showSecretInput = reactive<Record<string, boolean>>({})
const secretDraft = reactive<Record<string, string>>({})

// --- Destructive-action confirmations ---
const pendingRevertKey = ref<string | null>(null)
const pendingClearKey = ref<string | null>(null)

async function confirmRevert(): Promise<void> {
  const key = pendingRevertKey.value
  pendingRevertKey.value = null
  if (key) await deleteOverride(key)
}

async function confirmClear(): Promise<void> {
  const key = pendingClearKey.value
  pendingClearKey.value = null
  if (key) await clearSecret(key)
}

function cancelSecretInput(key: string): void {
  showSecretInput[key] = false
  secretDraft[key] = ''
}

async function saveSecret(key: string): Promise<void> {
  saving.value = true
  error.value = ''
  try {
    const draftValue = secretDraft[key] ?? ''
    await adminApi.setSecret(key, draftValue)
    // Mark as set in local state (don't show value)
    const entry = settings[key]
    if (entry) {
      entry.is_set = !!draftValue
      entry.override = null
      entry.effective = null
    }
    showSecretInput[key] = false
    secretDraft[key] = ''
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.settings.errors.save_secret'))
  } finally {
    saving.value = false
  }
}

async function clearSecret(key: string): Promise<void> {
  saving.value = true
  error.value = ''
  try {
    await adminApi.clearSecret(key) // Backend should treat empty string as unset
    const entry = settings[key]
    if (entry) {
      entry.is_set = false
      entry.override = null
      entry.effective = null
    }
    secretDraft[key] = ''
    toast.success(t('admin.settings.toasts.secret_cleared', { key }))
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.settings.errors.clear_secret'))
  } finally {
    saving.value = false
  }
}

// --- Normal (non-secret) settings ---

function resetDraft(): void {
  Object.keys(settings).forEach((k) => {
    const entry: AdminSettingEntry | undefined = settings[k]
    if (!entry || entry.readonly || entry.secret) return
    if (entry.type === 'bool') {
      // Backend may return booleans or their string representations for
      // bool-typed settings; the AdminSettingEntry types override/original
      // as `string | null`, so cast broadly to match runtime values. Parse
      // case-insensitively so legacy Python-style "True"/"False" overrides
      // still round-trip correctly.
      const asBool = (v: string | boolean | null): boolean =>
        v === true || String(v).toLowerCase() === 'true'
      const overrideBool = entry.override as string | boolean | null
      const originalBool = entry.original as string | boolean | null
      draft[k] =
        overrideBool !== undefined && overrideBool !== null
          ? asBool(overrideBool)
          : asBool(originalBool)
    } else if (entry.type === 'int') {
      draft[k] =
        entry.override !== undefined && entry.override !== null
          ? Number(entry.override)
          : Number(entry.original)
    } else {
      draft[k] = entry.override ?? entry.original ?? ''
    }
  })
}

async function fetchSettings(): Promise<void> {
  loading.value = true
  try {
    const res = await adminApi.getSettings()
    Object.assign(settings, res.data)
    resetDraft()
    // Restore the category tab from ?tab= (deep link / refresh) when valid;
    // otherwise default to the first available category once settings load.
    if (!activeTab.value && categoryTabs.value.length) {
      const fromQuery = typeof route.query.tab === 'string' ? route.query.tab : ''
      activeTab.value = categoryTabs.value.some((tabItem) => tabItem.value === fromQuery)
        ? fromQuery
        : categoryTabs.value[0].value
    }
  } catch {
    error.value = t('admin.settings.errors.load')
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  saving.value = true
  error.value = ''
  success.value = false
  try {
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([k]) => !(settings[k]?.readonly || settings[k]?.secret)),
    )
    await adminApi.updateSettings(payload)
    // Re-fetch so local state reflects exactly what the backend persisted.
    // The backend only stores overrides that differ from their default, so
    // marking every submitted setting as overridden here would wrongly show
    // unchanged settings as edited until the next reload.
    const res = await adminApi.getSettings()
    Object.assign(settings, res.data)
    resetDraft()
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.settings.errors.save'))
  } finally {
    saving.value = false
  }
}

/**
 * Verify SMTP end-to-end. Unsaved edits in the form are *not* used — the backend
 * sends with the settings it has stored, so a test after editing but before
 * saving would report on the old configuration. Hence the hint in the toast.
 */
async function sendTestEmail(): Promise<void> {
  sendingTestEmail.value = true
  try {
    const res = await adminApi.sendTestEmail()
    toast.success(t('admin.settings.toasts.test_email_sent', { email: res.data.recipient ?? '' }))
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.settings.errors.test_email'))
  } finally {
    sendingTestEmail.value = false
  }
}

async function deleteOverride(key: string): Promise<void> {
  try {
    await adminApi.deleteSetting(key)
    const entry = settings[key]
    if (entry) {
      entry.override = null
      entry.effective = entry.original
      entry.overridden = false
      draft[key] = entry.original ?? ''
    }
    toast.success(t('admin.settings.toasts.override_removed', { key }))
  } catch (e) {
    error.value = extractErrorMessage(e, t('admin.settings.errors.remove_override'))
  }
}

onMounted(fetchSettings)
</script>
