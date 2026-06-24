<template>
  <div>
    <h2 class="text-xl font-bold mb-5 flex items-center gap-2">
      <svg class="w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke="currentColor" />
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7z" />
      </svg>
      Celery Workers & Queues
    </h2>
    <div v-if="loading" class="py-8 flex justify-center">
      <LoadingSpinner size="medium" />
    </div>
    <div v-else>
      <div class="flex gap-4 mb-8">
        <BaseButton variant="primary" @click="fetchAll">Refresh</BaseButton>
      </div>
      <div>
        <h3 class="font-semibold text-lg mb-2">Workers</h3>
        <pre
          class="bg-gray-50 dark:bg-slate-900 p-4 rounded-lg border border-gray-100 dark:border-slate-800 overflow-x-auto text-sm"
          >{{ pretty(workers) }}</pre
        >
      </div>
      <div class="mt-8">
        <h3 class="font-semibold text-lg mb-2">Queues & Tasks</h3>
        <pre
          class="bg-gray-50 dark:bg-slate-900 p-4 rounded-lg border border-gray-100 dark:border-slate-800 overflow-x-auto text-sm"
          >{{ pretty(queues) }}</pre
        >
      </div>
      <div class="mt-8">
        <label class="block font-semibold mb-2">Inspect Task by ID:</label>
        <form class="flex gap-2 mb-4" @submit.prevent="inspectTask">
          <input
            v-model="taskId"
            class="rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900 text-gray-800 dark:text-white focus:ring-2 focus:ring-blue-300"
            placeholder="Paste task ID here"
          />
          <BaseButton type="submit" variant="primary">Inspect</BaseButton>
        </form>
        <div v-if="taskStatus">
          <pre
            class="bg-gray-50 dark:bg-slate-900 p-4 rounded-lg border border-gray-100 dark:border-slate-800 overflow-x-auto text-sm"
            >{{ pretty(taskStatus) }}</pre
          >
          <BaseButton
            v-if="['PENDING', 'STARTED', 'RETRY'].includes(taskStatus.status)"
            variant="danger"
            class="mt-2"
            @click="revokeTask(taskStatus.id)"
          >
            Revoke/Terminate
          </BaseButton>
        </div>
      </div>
      <div v-if="revokedId" class="mt-4 text-green-700 dark:text-green-400 font-semibold">
        Task {{ revokedId }} revoked!
      </div>
      <div v-if="error" class="mt-5 text-red-600 dark:text-red-400 font-semibold">{{ error }}</div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { adminApi } from '@/services/adminApi'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { extractErrorMessage } from '@/utils/errors'

const loading = ref(true)
const error = ref('')
const workers = ref({})
const queues = ref({})
const taskId = ref('')
const taskStatus = ref(null)
const revokedId = ref('')

function pretty(obj) {
  return JSON.stringify(obj, null, 2)
}

async function fetchWorkers() {
  const res = await adminApi.celeryWorkers()
  workers.value = res.data
}
async function fetchQueues() {
  const res = await adminApi.celeryQueues()
  queues.value = res.data
}
async function fetchAll() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([fetchWorkers(), fetchQueues()])
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to fetch celery status')
  } finally {
    loading.value = false
  }
}
async function inspectTask() {
  if (!taskId.value) return
  error.value = ''
  taskStatus.value = null
  try {
    const res = await adminApi.celeryTask(taskId.value)
    taskStatus.value = res.data
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to inspect task')
  }
}
async function revokeTask(id) {
  error.value = ''
  revokedId.value = ''
  try {
    await adminApi.revokeTask(id)
    revokedId.value = id
    setTimeout(() => {
      revokedId.value = ''
    }, 1800)
    // Optionally refresh queue info
    await fetchAll()
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to revoke task')
  }
}
onMounted(fetchAll)
</script>
