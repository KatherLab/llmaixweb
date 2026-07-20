<template>
  <div class="w-full max-w-md">
    <div class="flex flex-col items-center justify-center py-16">
      <LoadingSpinner size="large" />
      <p class="mt-4 text-content-muted">{{ statusMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * SSO completion route.
 *
 * The backend `/auth/sso/{slug}/callback` redirects here with the access +
 * refresh tokens in the URL fragment (never the query string, so they don't
 * leak into server logs or the Referer header). This view reads the fragment,
 * establishes the session, then redirects to the originally-requested path.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const statusMessage = ref<string>(t('auth.sso.completing'))

interface FragmentTokens {
  accessToken: string | null
  refreshToken: string | null
  redirect: string
}

function parseFragment(): FragmentTokens {
  const hash = window.location.hash.replace(/^#/, '')
  const params = new URLSearchParams(hash)
  return {
    accessToken: params.get('access_token'),
    refreshToken: params.get('refresh_token'),
    redirect: params.get('redirect') || '/projects',
  }
}

onMounted(async () => {
  const { accessToken, refreshToken, redirect } = parseFragment()
  if (!accessToken) {
    statusMessage.value = t('auth.sso.no_token')
    toast.error(t('auth.sso.failed_toast'))
    setTimeout(() => router.replace('/login'), 1500)
    return
  }
  try {
    await authStore.setSession(accessToken, refreshToken)
    toast.success(t('auth.sso.signed_in_toast'))
    // Whitelist redirect to an absolute path on this origin (open-redirect guard).
    const safe = redirect.startsWith('/') && !redirect.startsWith('//') ? redirect : '/projects'
    router.replace(safe)
  } catch {
    statusMessage.value = t('auth.sso.failed')
    setTimeout(() => router.replace('/login'), 1500)
  }
})
</script>
