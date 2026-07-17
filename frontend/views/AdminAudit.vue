<template>
  <div>
    <PageHeader
      title="Audit Log"
      subtitle="Accountability trail: who did what, when, and from where. Append-only."
      class="mb-6"
    >
      <template #icon>
        <ScrollText class="w-5 h-5" aria-hidden="true" />
      </template>
      <template #actions>
        <BaseButton
          v-if="mode === 'activity'"
          variant="secondary"
          :loading="exporting"
          @click="exportCsv"
        >
          Export CSV
        </BaseButton>
        <BaseButton variant="primary" :loading="loading" @click="refresh">Refresh</BaseButton>
      </template>
    </PageHeader>

    <!-- Mode toggle: durable activity trail vs. central error log -->
    <div class="flex gap-2 mb-4">
      <button
        v-for="m in modes"
        :key="m.value"
        type="button"
        :class="[
          'px-3 py-1.5 text-sm font-medium rounded-card border transition',
          mode === m.value
            ? 'bg-primary text-white border-primary'
            : 'bg-surface text-content-muted border-default hover:bg-surface-muted',
        ]"
        @click="setMode(m.value)"
      >
        {{ m.label }}
      </button>
    </div>

    <!-- ─────────────── Activity trail ─────────────── -->
    <div v-if="mode === 'activity'">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div>
          <label :class="labelClass" for="audit-filter-action">Action</label>
          <select
            id="audit-filter-action"
            v-model="filters.action"
            :class="inputClass"
            @change="applyFilters"
          >
            <option :value="undefined">All actions</option>
            <optgroup v-for="group in actionGroups" :key="group.label" :label="group.label">
              <option v-for="a in group.actions" :key="a" :value="a">{{ actionLabel(a) }}</option>
            </optgroup>
          </select>
        </div>
        <div>
          <label :class="labelClass" for="audit-filter-outcome">Outcome</label>
          <select
            id="audit-filter-outcome"
            v-model="filters.outcome"
            :class="inputClass"
            @change="applyFilters"
          >
            <option :value="undefined">All outcomes</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
            <option value="denied">Denied</option>
          </select>
        </div>
        <div>
          <label :class="labelClass" for="audit-filter-resource-type">Resource type</label>
          <input
            id="audit-filter-resource-type"
            v-model.trim="filters.resource_type"
            :class="inputClass"
            placeholder="e.g. document, trial"
            @keyup.enter="applyFilters"
          />
        </div>
        <div>
          <label :class="labelClass" for="audit-filter-request-id">Request / error ID</label>
          <input
            id="audit-filter-request-id"
            v-model.trim="filters.request_id"
            :class="inputClass"
            placeholder="Correlation ID"
            @keyup.enter="applyFilters"
          />
        </div>
      </div>

      <div v-if="loading" class="py-10 flex justify-center"><LoadingSpinner size="medium" /></div>
      <ErrorBanner v-else-if="error" :message="error" class="mb-4" />
      <EmptyState
        v-else-if="!auditRows.length"
        title="No audit events"
        description="No events match the current filters."
      />
      <div v-else class="bg-surface border border-default rounded-card overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-surface-sunken text-content-muted">
            <tr>
              <th class="text-left px-3 py-2 font-semibold">Time</th>
              <th class="text-left px-3 py-2 font-semibold">Actor</th>
              <th class="text-left px-3 py-2 font-semibold">Action</th>
              <th class="text-left px-3 py-2 font-semibold">Resource</th>
              <th class="text-left px-3 py-2 font-semibold">Outcome</th>
              <th class="text-left px-3 py-2 font-semibold">IP</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default-border">
            <tr
              v-for="row in auditRows"
              :key="row.id"
              class="hover:bg-surface-muted cursor-pointer"
              @click="selected = row"
            >
              <td class="px-3 py-2 text-content-muted whitespace-nowrap">
                {{ formatTime(row.created_at) }}
              </td>
              <td class="px-3 py-2 text-content">
                {{ row.actor_email || (row.actor_user_id ? `#${row.actor_user_id}` : 'system') }}
              </td>
              <td class="px-3 py-2">
                <span class="font-medium text-content">{{ actionLabel(row.action) }}</span>
              </td>
              <td class="px-3 py-2 text-content-muted">
                <template v-if="row.resource_type">
                  {{ row.resource_type }}<span v-if="row.resource_id">#{{ row.resource_id }}</span>
                </template>
                <span v-else>—</span>
              </td>
              <td class="px-3 py-2">
                <StatusBadge :status="outcomeStatus(row.outcome)" :label="row.outcome" />
              </td>
              <td class="px-3 py-2 text-content-subtle font-mono text-xs">
                {{ row.actor_ip || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <PaginationControls
        v-if="!loading && totalPages > 1"
        class="mt-4"
        :model-value="page"
        :total-pages="totalPages"
        :visible-pages="visiblePages"
        :total-items="total"
        :page-size="pageSize"
        item-label="events"
        @update:model-value="goToPage"
      />
    </div>

    <!-- ─────────────── Error log ─────────────── -->
    <div v-else>
      <div class="flex gap-2 mb-4 max-w-md">
        <input
          v-model.trim="errorIdQuery"
          :class="inputClass"
          placeholder="Look up an error ID a user reported…"
          @keyup.enter="fetchErrors"
        />
        <BaseButton variant="primary" @click="fetchErrors">Find</BaseButton>
        <BaseButton v-if="errorIdQuery" variant="ghost" @click="clearErrorSearch">Clear</BaseButton>
      </div>

      <div v-if="loading" class="py-10 flex justify-center"><LoadingSpinner size="medium" /></div>
      <ErrorBanner v-else-if="error" :message="error" class="mb-4" />
      <EmptyState
        v-else-if="!errorRows.length"
        title="No errors logged"
        :description="
          errorIdQuery
            ? 'No error matches that ID.'
            : 'The server has not logged any unhandled errors.'
        "
      />
      <div v-else class="bg-surface border border-default rounded-card overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-surface-sunken text-content-muted">
            <tr>
              <th class="text-left px-3 py-2 font-semibold">Time</th>
              <th class="text-left px-3 py-2 font-semibold">Error ID</th>
              <th class="text-left px-3 py-2 font-semibold">Endpoint</th>
              <th class="text-left px-3 py-2 font-semibold">Type</th>
              <th class="text-left px-3 py-2 font-semibold">Actor</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-default-border">
            <tr
              v-for="row in errorRows"
              :key="row.id"
              class="hover:bg-surface-muted cursor-pointer"
              @click="selectedError = row"
            >
              <td class="px-3 py-2 text-content-muted whitespace-nowrap">
                {{ formatTime(row.created_at) }}
              </td>
              <td class="px-3 py-2 font-mono text-xs text-content">{{ row.error_id }}</td>
              <td class="px-3 py-2 text-content-muted">
                <span class="font-mono text-xs">{{ row.method }} {{ row.path }}</span>
              </td>
              <td class="px-3 py-2 text-content-muted">{{ row.exception_type }}</td>
              <td class="px-3 py-2 text-content-muted">{{ row.actor_email || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Audit detail drawer -->
    <BaseModal v-if="selected" :open="true" title="Audit event" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Time</dt>
          <dd class="text-content">{{ formatTime(selected.created_at) }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Actor</dt>
          <dd class="text-content">{{ selected.actor_email || 'system' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Action</dt>
          <dd class="text-content">{{ actionLabel(selected.action) }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Resource</dt>
          <dd class="text-content">
            {{ selected.resource_type || '—'
            }}{{ selected.resource_id ? `#${selected.resource_id}` : '' }}
          </dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Project</dt>
          <dd class="text-content">{{ selected.project_id ?? '—' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Outcome</dt>
          <dd class="text-content">{{ selected.outcome }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">IP</dt>
          <dd class="text-content font-mono text-xs">{{ selected.actor_ip || '—' }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Correlation ID</dt>
          <dd class="text-content font-mono text-xs">{{ selected.request_id || '—' }}</dd>
        </div>
      </dl>
      <div v-if="selected.detail" class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-content-subtle mb-1">Detail</p>
        <pre
          class="bg-surface-sunken p-3 rounded-card border border-default overflow-x-auto text-xs"
          >{{ pretty(selected.detail) }}</pre>
      </div>
    </BaseModal>

    <!-- Error detail drawer -->
    <BaseModal v-if="selectedError" :open="true" title="Server error" @close="selectedError = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Error ID</dt>
          <dd class="text-content font-mono text-xs">{{ selectedError.error_id }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Time</dt>
          <dd class="text-content">{{ formatTime(selectedError.created_at) }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Endpoint</dt>
          <dd class="text-content font-mono text-xs">
            {{ selectedError.method }} {{ selectedError.path }}
          </dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Exception</dt>
          <dd class="text-content">{{ selectedError.exception_type }}</dd>
        </div>
        <div class="flex justify-between gap-4">
          <dt class="text-content-subtle">Actor</dt>
          <dd class="text-content">{{ selectedError.actor_email || '—' }}</dd>
        </div>
      </dl>
      <div v-if="selectedError.message" class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-content-subtle mb-1">
          Message
        </p>
        <p class="text-sm text-content">{{ selectedError.message }}</p>
      </div>
      <div v-if="selectedError.traceback" class="mt-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-content-subtle mb-1">
          Traceback
        </p>
        <pre
          class="bg-surface-sunken p-3 rounded-card border border-default overflow-x-auto text-xs max-h-96"
          >{{ selectedError.traceback }}</pre>
      </div>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ScrollText } from '@lucide/vue'
import { computeVisiblePages } from '@/composables/usePagination'
import { auditApi } from '@/services/auditApi'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import PaginationControls from '@/components/common/PaginationControls.vue'
import { inputClass, labelClass } from '@/utils/formStyles'
import { extractErrorMessage } from '@/utils/errors'
import { useFileDownload } from '@/composables/useFileDownload'
import { useToast } from '@/composables/useToast'
import type { AuditAction, AuditLogEntry, AuditLogQuery, ErrorLogEntry } from '@/types'

type Mode = 'activity' | 'errors'

const modes: { label: string; value: Mode }[] = [
  { label: 'Activity', value: 'activity' },
  { label: 'Errors', value: 'errors' },
]

const actionGroups: { label: string; actions: AuditAction[] }[] = [
  {
    label: 'Authentication',
    actions: [
      'login_success',
      'login_failure',
      'logout',
      'account_locked',
      'password_change',
      'password_reset',
      'sso_login',
    ],
  },
  {
    label: 'Access (PHI)',
    actions: ['document_view', 'document_download', 'file_download', 'trial_result_view', 'export'],
  },
  { label: 'Mutations', actions: ['create', 'update', 'delete', 'cancel'] },
  { label: 'Egress', actions: ['llm_extraction_call', 'ocr_external_call'] },
  {
    label: 'Administration',
    actions: [
      'setting_change',
      'user_create',
      'user_role_change',
      'user_deactivate',
      'invitation_send',
      'sso_provider_change',
    ],
  },
]

const { downloadBlob } = useFileDownload()
const toast = useToast()

const mode = ref<Mode>('activity')
const loading = ref(false)
const exporting = ref(false)
const error = ref('')

const auditRows = ref<AuditLogEntry[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 100
const selected = ref<AuditLogEntry | null>(null)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const visiblePages = computed(() => computeVisiblePages(page.value, totalPages.value))

const filters = reactive<AuditLogQuery>({
  action: undefined,
  outcome: undefined,
  resource_type: undefined,
  request_id: undefined,
})

const errorRows = ref<ErrorLogEntry[]>([])
const errorIdQuery = ref('')
const selectedError = ref<ErrorLogEntry | null>(null)

function pretty(obj: unknown): string {
  return JSON.stringify(obj, null, 2)
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString()
}

function actionLabel(action: string): string {
  return action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function outcomeStatus(outcome: string): string {
  if (outcome === 'success') return 'COMPLETED'
  if (outcome === 'denied') return 'CANCELLED'
  return 'FAILED'
}

function buildQuery(): AuditLogQuery {
  const q: AuditLogQuery = {
    limit: pageSize,
    offset: (page.value - 1) * pageSize,
  }
  if (filters.action) q.action = filters.action
  if (filters.outcome) q.outcome = filters.outcome
  if (filters.resource_type) q.resource_type = filters.resource_type
  if (filters.request_id) q.request_id = filters.request_id
  return q
}

async function fetchAudit(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const res = await auditApi.list(buildQuery())
    auditRows.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to load audit log')
  } finally {
    loading.value = false
  }
}

async function fetchErrors(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const res = await auditApi.listErrors(
      errorIdQuery.value ? { error_id: errorIdQuery.value } : { limit: 100 },
    )
    errorRows.value = res.data.items
  } catch (e) {
    error.value = extractErrorMessage(e, 'Failed to load error log')
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  fetchAudit()
}

function goToPage(p: number): void {
  page.value = p
  fetchAudit()
}

function refresh(): void {
  if (mode.value === 'activity') fetchAudit()
  else fetchErrors()
}

function setMode(m: Mode): void {
  mode.value = m
  refresh()
}

function clearErrorSearch(): void {
  errorIdQuery.value = ''
  fetchErrors()
}

async function exportCsv(): Promise<void> {
  exporting.value = true
  try {
    const params: AuditLogQuery = {}
    if (filters.action) params.action = filters.action
    if (filters.outcome) params.outcome = filters.outcome
    if (filters.resource_type) params.resource_type = filters.resource_type
    if (filters.request_id) params.request_id = filters.request_id
    const res = await auditApi.exportCsv(params)
    downloadBlob(res.data, 'audit-log.csv', 'text/csv')
  } catch (e) {
    toast.error(extractErrorMessage(e, 'Export failed'))
  } finally {
    exporting.value = false
  }
}

onMounted(fetchAudit)
</script>
