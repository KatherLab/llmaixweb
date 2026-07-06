<template>
  <div>
    <PageHeader
      title="Celery Workers & Queues"
      subtitle="Monitor Celery workers, queues, and tasks."
      class="mb-6"
    >
      <template #icon>
        <CircleDot class="w-5 h-5" aria-hidden="true" />
      </template>
      <template #actions>
        <BaseButton variant="primary" :loading="loading" @click="fetchAll">Refresh</BaseButton>
      </template>
    </PageHeader>
    <div v-if="loading" class="py-8 flex justify-center">
      <LoadingSpinner size="medium" />
    </div>
    <div v-else>
      <!-- Worker status cards -->
      <div>
        <h3 class="font-semibold text-lg mb-3 text-content">Workers</h3>
        <div v-if="workerList.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="w in workerList"
            :key="w.name"
            class="bg-surface border border-default rounded-card p-4 shadow-sm"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-semibold text-content truncate" :title="w.name">{{ w.name }}</span>
              <StatusBadge
                :status="w.status === 'ok' ? 'COMPLETED' : 'FAILED'"
                :label="w.status === 'ok' ? 'Online' : 'Offline'"
              />
            </div>
            <dl class="text-sm space-y-1 text-content-muted">
              <div v-if="w.pool" class="flex justify-between">
                <dt class="text-content-subtle">Pool</dt>
                <dd>{{ w.pool }}</dd>
              </div>
              <div v-if="w.concurrency !== undefined" class="flex justify-between">
                <dt class="text-content-subtle">Concurrency</dt>
                <dd>{{ w.concurrency }}</dd>
              </div>
              <div v-if="w.processes !== undefined" class="flex justify-between">
                <dt class="text-content-subtle">Processes</dt>
                <dd>{{ w.processes }}</dd>
              </div>
            </dl>
          </div>
        </div>
        <p v-else class="text-sm text-content-subtle italic">No workers reported.</p>
        <details class="mt-3">
          <summary class="text-xs text-content-subtle cursor-pointer hover:text-content-muted">
            Show raw worker JSON
          </summary>
          <pre
            class="bg-surface-sunken p-4 rounded-card border border-default overflow-x-auto text-sm mt-2"
            >{{ pretty(workers) }}</pre>
        </details>
      </div>

      <!-- Queue table -->
      <div class="mt-8">
        <h3 class="font-semibold text-lg mb-3 text-content">Queues & Tasks</h3>
        <div
          v-if="queueRows.length"
          class="bg-surface border border-default rounded-card overflow-hidden"
        >
          <table class="w-full text-sm">
            <thead class="bg-surface-sunken text-content-muted">
              <tr>
                <th class="text-left px-4 py-2 font-semibold">Queue</th>
                <th class="text-left px-4 py-2 font-semibold">Active</th>
                <th class="text-left px-4 py-2 font-semibold">Scheduled</th>
                <th class="text-left px-4 py-2 font-semibold">Reserved</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-default">
              <tr v-for="row in queueRows" :key="row.name" class="hover:bg-surface-muted">
                <td class="px-4 py-2 font-medium text-content">{{ row.name }}</td>
                <td class="px-4 py-2 text-content-muted">{{ row.active }}</td>
                <td class="px-4 py-2 text-content-muted">{{ row.scheduled }}</td>
                <td class="px-4 py-2 text-content-muted">{{ row.reserved }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-sm text-content-subtle italic">No queue data available.</p>
        <details class="mt-3">
          <summary class="text-xs text-content-subtle cursor-pointer hover:text-content-muted">
            Show raw queue JSON
          </summary>
          <pre
            class="bg-surface-sunken p-4 rounded-card border border-default overflow-x-auto text-sm mt-2"
            >{{ pretty(queues) }}</pre>
        </details>
      </div>

      <!-- Task inspection -->
      <div class="mt-8">
        <label :class="labelClass">Inspect Task by ID:</label>
        <form class="flex gap-2 mb-4" @submit.prevent="inspectTask">
          <input v-model="taskId" :class="inputClass" placeholder="Paste task ID here" />
          <BaseButton type="submit" variant="primary">Inspect</BaseButton>
        </form>
        <div v-if="taskStatus">
          <details open>
            <summary class="text-xs text-content-subtle cursor-pointer hover:text-content-muted">
              Task details (raw JSON)
            </summary>
            <pre
              class="bg-surface-sunken p-4 rounded-card border border-default overflow-x-auto text-sm mt-2"
              >{{ pretty(taskStatus) }}</pre>
          </details>
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
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CircleDot } from '@lucide/vue'
import { adminApi } from '@/services/adminApi'
import BaseButton from '@/components/common/BaseButton.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { extractErrorMessage } from '@/utils/errors'
import { inputClass, labelClass } from '@/utils/formStyles'
import type { CeleryWorkersResponse, CeleryQueuesResponse } from '@/types'

interface CeleryTaskStatus {
  id: string
  status: string
  [key: string]: unknown
}

interface WorkerCard {
  name: string
  status: string
  pool?: string
  concurrency?: string | number
  processes?: string | number
}

interface QueueRow {
  name: string
  active: number
  scheduled: number
  reserved: number
}

const loading = ref<boolean>(true)
const error = ref<string>('')
const workers = ref<CeleryWorkersResponse | Record<string, unknown>>({})
const queues = ref<CeleryQueuesResponse | Record<string, unknown>>({})
const taskId = ref<string>('')
const taskStatus = ref<CeleryTaskStatus | null>(null)
const revokedId = ref<string>('')

function pretty(obj: unknown): string {
  return JSON.stringify(obj, null, 2)
}

// Derive worker cards from the ping + stats payloads. Celery's inspect.ping
// returns { "worker@host": { ok: "pong" } } and inspect.stats returns rich
// per-worker info including pool impl and concurrency.
const workerList = computed<WorkerCard[]>(() => {
  const data = workers.value as Partial<CeleryWorkersResponse>
  const ping = (data.ping || {}) as Record<string, unknown>
  const stats = (data.stats || {}) as Record<string, unknown>
  const names = Object.keys(ping).length ? Object.keys(ping) : Object.keys(stats)
  if (!names.length) return []
  return names.map((name) => {
    const pingEntry = ping[name] as Record<string, unknown> | undefined
    const statsEntry = stats[name] as Record<string, unknown> | undefined
    const pool = statsEntry?.pool as Record<string, unknown> | undefined
    const concurrency: string | number | undefined =
      (pool?.max_concurrency as string | number | undefined) ??
      (statsEntry?.max_concurrency as string | number | undefined)
    const processes: string | number | undefined =
      (statsEntry?.max_tasks_per_child as string | number | undefined) ??
      (statsEntry?.processes as string | number | undefined)
    return {
      name,
      status: pingEntry?.ok === 'pong' ? 'ok' : pingEntry ? 'down' : 'unknown',
      pool: pool?.implementation as string | undefined,
      concurrency,
      processes,
    }
  })
})

// Derive queue rows from the active/scheduled/reserved payloads. Each is keyed
// by queue name; the value is a list (or object) of task entries.
const queueRows = computed<QueueRow[]>(() => {
  const data = queues.value as Partial<CeleryQueuesResponse>
  const active = (data.active || {}) as Record<string, unknown>
  const scheduled = (data.scheduled || {}) as Record<string, unknown>
  const reserved = (data.reserved || {}) as Record<string, unknown>
  const names = new Set([
    ...Object.keys(active),
    ...Object.keys(scheduled),
    ...Object.keys(reserved),
  ])
  if (!names.size) return []
  const count = (v: unknown): number => {
    if (Array.isArray(v)) return v.length
    if (v && typeof v === 'object') return Object.keys(v).length
    return 0
  }
  return Array.from(names).map((name) => ({
    name,
    active: count(active[name]),
    scheduled: count(scheduled[name]),
    reserved: count(reserved[name]),
  }))
})

async function fetchWorkers(): Promise<void> {
  const res = await adminApi.celeryWorkers()
  workers.value = res.data
}
async function fetchQueues(): Promise<void> {
  const res = await adminApi.celeryQueues()
  queues.value = res.data
}
async function fetchAll(): Promise<void> {
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
async function inspectTask(): Promise<void> {
  if (!taskId.value) return
  error.value = ''
  taskStatus.value = null
  try {
    const res = await adminApi.celeryTask(taskId.value)
    taskStatus.value = res.data as CeleryTaskStatus
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to inspect task')
  }
}
async function revokeTask(id: string): Promise<void> {
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
