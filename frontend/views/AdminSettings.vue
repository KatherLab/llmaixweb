<template>
  <div>
    <h2 class="text-2xl font-bold mb-6 flex items-center gap-2 text-slate-900 dark:text-white">
      <CircleDot class="w-7 h-7 text-blue-600" />
      App Settings
    </h2>

    <!-- Category Tabs -->
    <BaseTabGroup v-model="activeTab" :tabs="categoryTabs" class="mb-6" />

    <!-- Settings Form -->
    <form v-if="!loading" class="max-w-3xl mx-auto" @submit.prevent="save">
      <div
        v-for="(val, key) in filteredSettings"
        :key="key"
        class="grid grid-cols-1 md:grid-cols-3 gap-3 items-center py-2 border-b border-slate-100 dark:border-slate-800"
      >
        <!-- Label & Description -->
        <div class="font-semibold flex flex-col">
          <span>{{ val.label }}</span>
          <span class="text-xs text-slate-400 dark:text-slate-500">{{ val.description }}</span>
        </div>

        <!-- Value Display -->
        <div class="text-xs text-slate-500 dark:text-slate-400 break-all">
          <template v-if="val.secret">
            <span v-if="val.is_set" class="text-green-700 dark:text-green-400">Set</span>
            <span v-else class="text-red-500 dark:text-red-400">Not Set</span>
          </template>
          <template v-else>
            <span v-if="val.override !== undefined && val.override !== null">
              <s>{{ val.original }}</s>
              <span class="ml-1 text-blue-700 dark:text-blue-300 font-semibold">{{
                val.override
              }}</span>
            </span>
            <span v-else>{{ val.original }}</span>
          </template>
        </div>

        <!-- Input/Edit Area -->
        <div>
          <!-- Read-only: .env only -->
          <template v-if="val.readonly">
            <div class="text-slate-400 dark:text-slate-500 flex flex-col gap-1">
              <span class="flex items-center gap-1">
                <Lock class="w-4 h-4 mr-1 text-slate-400 dark:text-slate-500 inline-block" />
                Set in <code>.env</code>
              </span>
              <span class="text-xs"
                >Example: <code>{{ key }}={{ val.original }}</code></span
              >
            </div>
          </template>

          <!-- Editable Secret -->
          <template v-else-if="val.secret">
            <div class="flex flex-col gap-1">
              <div class="flex gap-2 mt-1">
                <button
                  type="button"
                  class="px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50"
                  @click="showSecretInput[key] = !showSecretInput[key]"
                >
                  {{ val.is_set ? 'Update' : 'Set' }}
                </button>
                <button
                  v-if="val.is_set"
                  type="button"
                  class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/50"
                  @click="clearSecret(key)"
                >
                  Clear
                </button>
              </div>
              <div v-if="showSecretInput[key]" class="mt-2 flex gap-2">
                <input
                  v-model="secretDraft[key]"
                  type="password"
                  autocomplete="off"
                  :class="[inputClass, 'flex-1']"
                  placeholder="Enter new value"
                />
                <BaseButton type="button" variant="primary" size="sm" @click="saveSecret(key)">
                  Save
                </BaseButton>
                <BaseButton
                  type="button"
                  variant="secondary"
                  size="sm"
                  @click="cancelSecretInput(key)"
                >
                  Cancel
                </BaseButton>
              </div>
            </div>
          </template>

          <!-- Boolean -->
          <template v-else-if="val.type === 'bool'">
            <div class="flex items-center gap-2">
              <input
                v-model="draft[key]"
                type="checkbox"
                class="w-5 h-5 text-blue-600 dark:text-blue-400"
              />
              <button
                v-if="val.overridden"
                type="button"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/50"
                @click="deleteOverride(key)"
              >
                Revert
              </button>
            </div>
          </template>
          <!-- Integer -->
          <template v-else-if="val.type === 'int'">
            <div class="flex items-center gap-2">
              <input v-model.number="draft[key]" type="number" :class="[inputClass, 'flex-1']" />
              <button
                v-if="val.overridden"
                type="button"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/50"
                @click="deleteOverride(key)"
              >
                Revert
              </button>
            </div>
          </template>
          <!-- String (default) -->
          <template v-else>
            <div class="flex items-center gap-2">
              <input v-model="draft[key]" type="text" :class="[inputClass, 'flex-1']" />
              <button
                v-if="val.overridden"
                type="button"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200 dark:hover:bg-red-900/50"
                @click="deleteOverride(key)"
              >
                Revert
              </button>
            </div>
          </template>
        </div>
      </div>
      <div class="mt-8 flex gap-4">
        <BaseButton type="submit" variant="primary" :loading="saving" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save' }}
        </BaseButton>
        <BaseButton
          variant="secondary"
          class="dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700 dark:hover:bg-slate-700"
          @click="resetDraft"
        >
          Reset
        </BaseButton>
      </div>
      <div v-if="success" class="mt-5 text-green-600 dark:text-green-400 font-semibold">
        Settings saved!
      </div>
      <div v-if="error" class="mt-5 text-red-600 dark:text-red-400 font-semibold">{{ error }}</div>
    </form>
    <div v-else class="py-12 flex justify-center">Loading...</div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { CircleDot, Lock } from '@lucide/vue'
import { adminApi } from '@/services/adminApi'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseTabGroup from '@/components/common/BaseTabGroup.vue'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass } from '@/utils/formStyles'

const settings = reactive({})
const draft = reactive({})
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref(false)

const categories = [
  'All',
  'General',
  'OpenAI',
  'OCR',
  'Storage',
  'Database',
  'Security',
  'Celery',
  'Email',
]
const categoryTabs = computed(() => categories.map((cat) => ({ label: cat, value: cat })))
const activeTab = ref('All')

const filteredSettings = computed(() => {
  if (activeTab.value === 'All') return settings
  return Object.fromEntries(
    Object.entries(settings).filter(([k, v]) => v.category === activeTab.value),
  )
})

// --- Secrets state ---
const showSecretInput = reactive({})
const secretDraft = reactive({})

function cancelSecretInput(key) {
  showSecretInput[key] = false
  secretDraft[key] = ''
}

async function saveSecret(key) {
  saving.value = true
  error.value = ''
  try {
    await adminApi.setSecret(key, secretDraft[key])
    // Mark as set in local state (don't show value)
    settings[key].is_set = !!secretDraft[key]
    settings[key].override = null
    settings[key].effective = null
    showSecretInput[key] = false
    secretDraft[key] = ''
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to save secret')
  } finally {
    saving.value = false
  }
}

async function clearSecret(key) {
  saving.value = true
  error.value = ''
  try {
    await adminApi.clearSecret(key) // Backend should treat empty string as unset
    settings[key].is_set = false
    settings[key].override = null
    settings[key].effective = null
    secretDraft[key] = ''
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to clear secret')
  } finally {
    saving.value = false
  }
}

// --- Normal (non-secret) settings ---

function resetDraft() {
  Object.keys(settings).forEach((k) => {
    if (!settings[k].readonly && !settings[k].secret) {
      if (settings[k].type === 'bool') {
        draft[k] =
          settings[k].override !== undefined && settings[k].override !== null
            ? settings[k].override === true || settings[k].override === 'true'
            : settings[k].original === true || settings[k].original === 'true'
      } else if (settings[k].type === 'int') {
        draft[k] =
          settings[k].override !== undefined && settings[k].override !== null
            ? Number(settings[k].override)
            : Number(settings[k].original)
      } else {
        draft[k] = settings[k].override ?? settings[k].original
      }
    }
  })
}

async function fetchSettings() {
  loading.value = true
  try {
    const res = await adminApi.getSettings()
    Object.assign(settings, res.data)
    resetDraft()
  } catch (e) {
    error.value = 'Failed to load settings'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  success.value = false
  try {
    const payload = Object.fromEntries(
      Object.entries(draft).filter(([k]) => !settings[k].readonly && !settings[k].secret),
    )
    await adminApi.updateSettings(payload)
    Object.entries(payload).forEach(([k, v]) => {
      settings[k].override = v
      settings[k].effective = v
      settings[k].overridden = true
    })
    success.value = true
    setTimeout(() => {
      success.value = false
    }, 1200)
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to save settings')
  } finally {
    saving.value = false
  }
}

async function deleteOverride(key) {
  try {
    await adminApi.deleteSetting(key)
    settings[key].override = undefined
    settings[key].effective = settings[key].original
    settings[key].overridden = false
    draft[key] = settings[key].original
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to remove override')
  }
}

onMounted(fetchSettings)
</script>
