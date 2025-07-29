<template>
  <div>
    <h2 class="text-2xl font-bold mb-6 flex items-center gap-2">
      <svg class="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke="currentColor" />
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z"/>
      </svg>
      App Settings
    </h2>

    <!-- Category Tabs -->
    <nav class="flex gap-2 mb-6 border-b border-gray-100 dark:border-slate-800">
      <button
        v-for="cat in categories"
        :key="cat"
        @click="activeTab = cat"
        class="px-4 py-2 text-base rounded-t-lg font-medium border border-b-0 transition-all"
        :class="activeTab === cat
          ? 'bg-white dark:bg-slate-900 border-blue-400 dark:border-blue-500 text-blue-700 dark:text-blue-300'
          : 'bg-gray-50 dark:bg-slate-900 border-gray-100 dark:border-slate-800 text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-950'"
      >{{ cat }}</button>
    </nav>

    <!-- Settings Form -->
    <form v-if="!loading" @submit.prevent="save" class="max-w-3xl mx-auto">
      <div v-for="(val, key) in filteredSettings" :key="key"
        class="grid grid-cols-1 md:grid-cols-3 gap-3 items-center py-2 border-b border-gray-100 dark:border-slate-800">
        <!-- Label & Description -->
        <div class="font-semibold flex flex-col">
          <span>{{ val.label }}</span>
          <span class="text-xs text-gray-400">{{ val.description }}</span>
        </div>

        <!-- Value Display -->
        <div class="text-xs text-gray-500 break-all">
          <template v-if="val.secret">
            <span v-if="val.is_set" class="text-green-700 dark:text-green-400">Set</span>
            <span v-else class="text-red-500">Not Set</span>
          </template>
          <template v-else>
            <span v-if="val.override !== undefined && val.override !== null">
              <s>{{ val.original }}</s>
              <span class="ml-1 text-blue-700 font-semibold">{{ val.override }}</span>
            </span>
            <span v-else>{{ val.original }}</span>
          </template>
        </div>

        <!-- Input/Edit Area -->
        <div>
          <!-- Read-only: .env only -->
          <template v-if="val.readonly">
            <div class="text-gray-400 flex flex-col gap-1">
              <span class="flex items-center gap-1">
                <svg class="w-4 h-4 mr-1 text-gray-400 inline-block" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-width="2" d="M6.5 11V7a5.5 5.5 0 0 1 11 0v4m-13 7.3V15a2.5 2.5 0 0 1 2.5-2.5h11A2.5 2.5 0 0 1 20.5 15v3.3c0 .71-.58 1.29-1.29 1.29H7.79c-.71 0-1.29-.58-1.29-1.29z"/></svg>
                Set in <code>.env</code>
              </span>
              <span class="text-xs">Example: <code>{{ key }}={{ val.original }}</code></span>
            </div>
          </template>

          <!-- Editable Secret -->
          <template v-else-if="val.secret">
            <div class="flex flex-col gap-1">
              <div class="flex gap-2 mt-1">
                <button type="button" @click="showSecretInput[key] = !showSecretInput[key]"
                  class="px-2 py-1 rounded bg-blue-100 text-blue-700 text-xs font-medium hover:bg-blue-200">
                  {{ val.is_set ? 'Update' : 'Set' }}
                </button>
                <button v-if="val.is_set" type="button" @click="clearSecret(key)"
                  class="px-2 py-1 rounded bg-red-100 text-red-600 text-xs font-medium hover:bg-red-200">
                  Clear
                </button>
              </div>
              <div v-if="showSecretInput[key]" class="mt-2 flex gap-2">
                <input
                  v-model="secretDraft[key]"
                  type="password"
                  autocomplete="off"
                  class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white flex-1"
                  placeholder="Enter new value"
                />
                <button type="button" @click="saveSecret(key)"
                  class="px-3 py-2 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700">
                  Save
                </button>
                <button type="button" @click="cancelSecretInput(key)"
                  class="px-3 py-2 rounded bg-gray-200 text-gray-600 font-semibold hover:bg-gray-300">
                  Cancel
                </button>
              </div>
            </div>
          </template>

          <!-- Boolean -->
          <template v-else-if="val.type === 'bool'">
            <div class="flex items-center gap-2">
              <input type="checkbox" v-model="draft[key]" class="w-5 h-5 text-blue-600" />
              <button v-if="val.overridden" type="button" @click="deleteOverride(key)"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200">Revert</button>
            </div>
          </template>
          <!-- Integer -->
          <template v-else-if="val.type === 'int'">
            <div class="flex items-center gap-2">
              <input type="number" v-model.number="draft[key]"
                class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-300 flex-1" />
              <button v-if="val.overridden" type="button" @click="deleteOverride(key)"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200">Revert</button>
            </div>
          </template>
          <!-- String (default) -->
          <template v-else>
            <div class="flex items-center gap-2">
              <input v-model="draft[key]" type="text"
                class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-300 flex-1" />
              <button v-if="val.overridden" type="button" @click="deleteOverride(key)"
                class="px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-300 text-xs font-medium hover:bg-red-200">Revert</button>
            </div>
          </template>
        </div>
      </div>
      <div class="mt-8 flex gap-4">
        <button type="submit" :disabled="saving"
          class="bg-blue-600 text-white px-6 py-2 rounded font-bold shadow hover:bg-blue-700 transition">
          <span v-if="saving"><span
              class="animate-spin inline-block mr-2 w-4 h-4 border-b-2 border-white rounded-full"></span>Saving...</span>
          <span v-else>Save</span>
        </button>
        <button type="button" @click="resetDraft"
          class="bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-200 px-6 py-2 rounded font-semibold border border-gray-200 dark:border-slate-700 hover:bg-gray-200 dark:hover:bg-slate-700 transition">
          Reset
        </button>
      </div>
      <div v-if="success" class="mt-5 text-green-600 dark:text-green-400 font-semibold">Settings saved!</div>
      <div v-if="error" class="mt-5 text-red-600 dark:text-red-400 font-semibold">{{ error }}</div>
    </form>
    <div v-else class="py-12 flex justify-center">Loading...</div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '@/services/api'

const settings = reactive({})
const draft = reactive({})
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref(false)

const categories = ["All", "General", "OpenAI", "Storage", "Database", "Security", "Celery"]
const activeTab = ref("All")

const filteredSettings = computed(() => {
  if (activeTab.value === "All") return settings
  return Object.fromEntries(
    Object.entries(settings).filter(([k, v]) => v.category === activeTab.value)
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
    await api.put('/admin/settings', { [key]: secretDraft[key] })
    // Mark as set in local state (don't show value)
    settings[key].is_set = !!secretDraft[key]
    settings[key].override = null
    settings[key].effective = null
    showSecretInput[key] = false
    secretDraft[key] = ''
    success.value = true
    setTimeout(() => { success.value = false }, 1200)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to save secret'
  } finally {
    saving.value = false
  }
}

async function clearSecret(key) {
  saving.value = true
  error.value = ''
  try {
    await api.put('/admin/settings', { [key]: '' })  // Backend should treat empty string as unset
    settings[key].is_set = false
    settings[key].override = null
    settings[key].effective = null
    secretDraft[key] = ''
    success.value = true
    setTimeout(() => { success.value = false }, 1200)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to clear secret'
  } finally {
    saving.value = false
  }
}

// --- Normal (non-secret) settings ---

function resetDraft() {
  Object.keys(settings).forEach(k => {
    if (!settings[k].readonly && !settings[k].secret) {
      if (settings[k].type === "bool") {
        draft[k] = settings[k].override !== undefined && settings[k].override !== null
          ? (settings[k].override === true || settings[k].override === "true")
          : (settings[k].original === true || settings[k].original === "true")
      } else if (settings[k].type === "int") {
        draft[k] = settings[k].override !== undefined && settings[k].override !== null
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
    const res = await api.get('/admin/settings')
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
      Object.entries(draft).filter(([k]) => !settings[k].readonly && !settings[k].secret)
    )
    await api.put('/admin/settings', payload)
    Object.entries(payload).forEach(([k, v]) => {
      settings[k].override = v
      settings[k].effective = v
      settings[k].overridden = true
    })
    success.value = true
    setTimeout(() => { success.value = false }, 1200)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

async function deleteOverride(key) {
  try {
    await api.delete(`/admin/settings/${key}`)
    settings[key].override = undefined
    settings[key].effective = settings[key].original
    settings[key].overridden = false
    draft[key] = settings[key].original
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to remove override'
  }
}

onMounted(fetchSettings)
</script>
