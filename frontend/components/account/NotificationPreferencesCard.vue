<template>
  <GlassCard>
    <div class="p-6">
      <h2 class="text-base font-semibold text-content mb-1">
        {{ $t('account.notifications.title') }}
      </h2>
      <p class="text-xs text-content-subtle mb-4">
        {{ $t('account.notifications.subtitle') }}
      </p>

      <div v-if="loading" class="flex justify-center py-6">
        <LoadingSpinner size="medium" />
      </div>

      <template v-else-if="prefs">
        <!--
          Without SMTP configured every toggle below is inert, so say so once
          instead of letting the user set preferences that can never take effect.
        -->
        <Callout v-if="!prefs.email_configured" variant="warning" class="mb-4">
          {{ $t('account.notifications.email_not_configured') }}
        </Callout>

        <div class="divide-y divide-default-border">
          <NotificationToggle
            v-model="prefs.job_finished"
            :label="$t('account.notifications.job_finished')"
            :description="$t('account.notifications.job_finished_hint')"
            :disabled="saving"
            @update:model-value="(v: boolean) => save({ job_finished: v })"
          />
          <NotificationToggle
            v-model="prefs.project_shared"
            :label="$t('account.notifications.project_shared')"
            :description="$t('account.notifications.project_shared_hint')"
            :disabled="saving"
            @update:model-value="(v: boolean) => save({ project_shared: v })"
          />
          <NotificationToggle
            v-model="prefs.security"
            :label="$t('account.notifications.security')"
            :description="$t('account.notifications.security_hint')"
            :disabled="saving"
            @update:model-value="(v: boolean) => save({ security: v })"
          />
          <NotificationToggle
            v-if="isAdmin"
            v-model="prefs.admin_alerts"
            :label="$t('account.notifications.admin_alerts')"
            :description="$t('account.notifications.admin_alerts_hint')"
            :disabled="saving"
            @update:model-value="(v: boolean) => save({ admin_alerts: v })"
          />
        </div>

        <h3 class="mt-6 mb-1 text-sm font-semibold text-content">
          {{ $t('account.notifications.delivery_title') }}
        </h3>
        <div class="divide-y divide-default-border">
          <NotificationToggle
            v-model="prefs.only_when_away"
            :label="$t('account.notifications.only_when_away')"
            :description="$t('account.notifications.only_when_away_hint')"
            :disabled="saving || !prefs.job_finished"
            @update:model-value="(v: boolean) => save({ only_when_away: v })"
          />
          <div class="py-3">
            <label
              for="min-job-minutes"
              class="block text-sm font-medium text-content"
              :class="{ 'opacity-50': !prefs.job_finished }"
            >
              {{ $t('account.notifications.min_duration') }}
            </label>
            <p class="mt-0.5 mb-2 text-xs text-content-subtle">
              {{ $t('account.notifications.min_duration_hint') }}
            </p>
            <div class="flex items-center gap-2">
              <input
                id="min-job-minutes"
                v-model="minMinutes"
                type="number"
                min="0"
                max="1440"
                step="1"
                :disabled="saving || !prefs.job_finished"
                :placeholder="$t('account.notifications.min_duration_default')"
                class="w-24 rounded-lg bg-surface text-content text-sm px-3 py-1.5 ring-1 ring-default-border focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                @change="saveMinDuration"
              />
              <span class="text-xs text-content-subtle">
                {{ $t('account.notifications.minutes') }}
              </span>
            </div>
          </div>
        </div>

        <p v-if="error" class="mt-3 text-xs text-red-600 dark:text-red-400">{{ error }}</p>
      </template>

      <ErrorBanner v-else-if="error" :message="error" class="mt-2" />
    </div>
  </GlassCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { usersApi } from '@/services/usersApi'
import { extractErrorMessage } from '@/utils/errors'
import Callout from '@/components/common/Callout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import GlassCard from '@/components/common/GlassCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import NotificationToggle from './NotificationToggle.vue'
import type { NotificationPreferences, NotificationPreferencesUpdate } from '@/types'

const { t } = useI18n({ useScope: 'global' })
const authStore = useAuthStore()
const toast = useToast()

const prefs = ref<NotificationPreferences | null>(null)
const loading = ref<boolean>(true)
const saving = ref<boolean>(false)
const error = ref<string>('')

const isAdmin = computed<boolean>(() => authStore.isAdmin)

// The API stores seconds (it shares the threshold with a server-side setting);
// minutes are what a person thinks in. Empty means "no override".
const minMinutes = ref<string>('')

onMounted(async () => {
  try {
    const res = await usersApi.getNotificationPreferences()
    prefs.value = res.data
    minMinutes.value =
      res.data.min_job_seconds === null ? '' : String(Math.round(res.data.min_job_seconds / 60))
  } catch (e) {
    error.value = extractErrorMessage(e, t('account.notifications.load_failed'))
  } finally {
    loading.value = false
  }
})

/**
 * Persist one changed field. Each toggle saves on change rather than behind a
 * Save button: there is nothing to review, and a half-applied set of
 * notification switches has no meaning worth confirming.
 *
 * On failure the server's answer is authoritative — we adopt the response body
 * so the UI can't drift from what is actually stored.
 */
async function save(patch: NotificationPreferencesUpdate): Promise<void> {
  if (!prefs.value) return
  saving.value = true
  error.value = ''
  try {
    const res = await usersApi.updateNotificationPreferences(patch)
    prefs.value = res.data
  } catch (e) {
    error.value = extractErrorMessage(e, t('account.notifications.save_failed'))
    // Re-read rather than guessing what the failed write did or didn't apply.
    try {
      const res = await usersApi.getNotificationPreferences()
      prefs.value = res.data
    } catch {
      /* keep the optimistic value; the error message already explains */
    }
  } finally {
    saving.value = false
  }
}

async function saveMinDuration(): Promise<void> {
  const raw = minMinutes.value.trim()
  if (raw === '') {
    await save({ min_job_seconds: null })
    return
  }
  const minutes = Number(raw)
  if (!Number.isFinite(minutes) || minutes < 0 || minutes > 1440) {
    toast.error(t('account.notifications.min_duration_invalid'))
    // Snap the field back to what is stored.
    minMinutes.value =
      prefs.value?.min_job_seconds == null
        ? ''
        : String(Math.round(prefs.value.min_job_seconds / 60))
    return
  }
  await save({ min_job_seconds: Math.round(minutes * 60) })
}
</script>
