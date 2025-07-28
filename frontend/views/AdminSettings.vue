<template>
  <div>
    <h2 class="text-xl font-bold mb-5 flex items-center gap-2">
      <svg class="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" /><path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z"/></svg>
      App Settings
    </h2>
    <div v-if="loading" class="py-8 flex justify-center">
      <div class="animate-spin w-8 h-8 border-b-4 border-blue-500 rounded-full"></div>
    </div>
    <form v-else @submit.prevent="save" class="space-y-7 max-w-2xl">
      <div v-for="(value, key) in settings" :key="key" class="grid grid-cols-2 gap-4 items-center">
        <label class="font-semibold text-gray-700 dark:text-slate-200 flex items-center gap-2">
          {{ key }}
          <span v-if="isSensitive(key)" class="text-xs bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 px-2 py-0.5 rounded">Sensitive</span>
        </label>
        <input
          v-if="!isSensitive(key)"
          v-model="draft[key]"
          class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-300"
        />
        <input
          v-else
          :type="'password'"
          v-model="draft[key]"
          autocomplete="off"
          class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-300"
          placeholder="••••••••"
        />
      </div>
      <div class="flex gap-3 mt-8">
        <button
          type="submit"
          :disabled="saving"
          class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition"
        >
          <span v-if="saving"><span class="animate-spin inline-block mr-2 w-4 h-4 border-b-2 border-white rounded-full"></span>Saving...</span>
          <span v-else>Save Changes</span>
        </button>
        <button
          type="button"
          @click="resetDraft"
          class="bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-200 px-6 py-2 rounded-lg font-semibold border border-gray-200 dark:border-slate-700 hover:bg-gray-200 dark:hover:bg-slate-700 transition"
        >Reset</button>
      </div>
      <div v-if="success" class="mt-5 text-green-600 dark:text-green-400 font-semibold">Settings saved!</div>
      <div v-if="error" class="mt-5 text-red-600 dark:text-red-400 font-semibold">{{ error }}</div>
    </form>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '@/services/api'
const loading = ref(true)
const settings = reactive({})
const draft = reactive({})
const saving = ref(false)
const error = ref('')
const success = ref(false)

function isSensitive(key) {
  // Adjust as you wish
  return ['OPENAI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'SECRET_KEY'].includes(key)
}

function resetDraft() {
  Object.keys(settings).forEach(k => { draft[k] = settings[k] })
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
    await api.put('/admin/settings', draft)
    Object.assign(settings, draft)
    success.value = true
    setTimeout(() => { success.value = false }, 1500)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Failed to save settings'
  } finally {
    saving.value = false
  }
}
onMounted(fetchSettings)
</script>
