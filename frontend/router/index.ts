import { watch } from 'vue'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { i18n } from '@/i18n'

// Layouts + landing are eager: they're part of the first paint.
import Landing from '@/views/Landing.vue'
import AppLayout from '@/views/AppLayout.vue'
import AuthLayout from '@/views/AuthLayout.vue'

// Route views are lazy-loaded via dynamic import() so each page is code-split
// into its own chunk instead of everything landing in the initial bundle.
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')
const ForgotPassword = () => import('@/views/ForgotPassword.vue')
const ResetPassword = () => import('@/views/ResetPassword.vue')
const InvitationLanding = () => import('@/views/InvitationLandingPage.vue')
const SsoComplete = () => import('@/views/SsoComplete.vue')
const NotFound = () => import('@/views/NotFound.vue')

const ProjectOverview = () => import('@/views/ProjectOverview.vue')
const ProjectDetail = () => import('@/views/ProjectDetail.vue')
const AccountSettings = () => import('@/views/AccountSettings.vue')
const AdminUserManagement = () => import('@/views/AdminUserManagement.vue')
const AdminDashboard = () => import('@/views/AdminDashboard.vue')
const AdminSettings = () => import('@/views/AdminSettings.vue')
const AdminCelery = () => import('@/views/AdminCelery.vue')
const AdminSSO = () => import('@/views/AdminSSO.vue')
const AdminAudit = () => import('@/views/AdminAudit.vue')

const FirstAdminSetup = () => import('@/views/FirstAdminSetup.vue')

import { useAuthStore } from '@/stores/auth'
import { useFirstAdminStore } from '@/stores/firstAdmin'

const routes: RouteRecordRaw[] = [
  // Landing page — its own clean, navbar-less layout (full-bleed marketing).
  { path: '', component: Landing },

  // Authenticated app routes (navbar visible)
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: 'projects',
        component: ProjectOverview,
        meta: { requiresAuth: true, titleKey: 'routes.projects' },
      },
      {
        path: 'account',
        component: AccountSettings,
        meta: { requiresAuth: true, titleKey: 'routes.account_settings' },
      },
      {
        path: 'projects/:projectId',
        component: ProjectDetail,
        props: true,
        meta: { requiresAuth: true, titleKey: 'routes.project' },
      },
      // Admin routes — all nested under /admin so they share the AdminDashboard
      // tab layout (single entry point: the gear "Admin" link in the navbar).
      {
        path: 'admin',
        component: AdminDashboard,
        meta: { requiresAuth: true, adminOnly: true, titleKey: 'routes.admin' },
        children: [
          {
            path: 'user-management',
            component: AdminUserManagement,
            meta: { titleKey: 'routes.user_management' },
          },
          {
            path: 'settings',
            component: AdminSettings,
            meta: { titleKey: 'routes.admin_settings' },
          },
          { path: 'sso', component: AdminSSO, meta: { titleKey: 'routes.sso_providers' } },
          { path: 'audit', component: AdminAudit, meta: { titleKey: 'routes.audit_log' } },
          { path: 'celery', component: AdminCelery, meta: { titleKey: 'routes.task_monitor' } },
          { path: '', redirect: '/admin/user-management' },
        ],
      },
    ],
  },

  // Public routes (no navbar)
  {
    path: '/',
    component: AuthLayout,
    children: [
      { path: 'login', component: Login, meta: { titleKey: 'routes.sign_in' } },
      { path: 'register', component: Register, meta: { titleKey: 'routes.register' } },
      {
        path: 'forgot-password',
        component: ForgotPassword,
        meta: { titleKey: 'routes.forgot_password' },
      },
      {
        path: 'reset-password/:token',
        component: ResetPassword,
        meta: { titleKey: 'routes.reset_password' },
      },
      {
        path: 'invitation/:token',
        component: InvitationLanding,
        meta: { titleKey: 'routes.invitation' },
      },
      {
        path: 'auth/sso/complete',
        component: SsoComplete,
        meta: { titleKey: 'routes.signing_in' },
      },
      {
        path: 'first-admin',
        component: FirstAdminSetup,
        meta: { titleKey: 'routes.first_admin_setup' },
      },
    ],
  },

  // 404 fallback
  { path: '/:pathMatch(.*)*', component: NotFound, meta: { titleKey: 'routes.not_found' } },
]

// Router creation
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth/admin/first-admin guard
router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  const firstAdminStore = useFirstAdminStore()

  // Always check first admin state before anything else
  if (!firstAdminStore.checked) {
    await firstAdminStore.checkFirstAdmin()
  }

  // If first admin is needed, only allow access to /first-admin
  if (firstAdminStore.needsFirstAdmin && to.path !== '/first-admin') {
    return '/first-admin'
  }
  // Prevent showing setup page after admin exists
  if (!firstAdminStore.needsFirstAdmin && to.path === '/first-admin') {
    return '/'
  }

  // Ensure the user profile is loaded before evaluating auth/admin guards.
  // `initialize()` is idempotent (no-op once done) and only hits the network
  // when a token exists. Without this, a hard refresh or deep-link to an
  // /admin/* route runs the guard while `user` is still null → `isAdmin` is
  // false → the admin gets bounced to '/'.
  if (!authStore.isInitialized) {
    await authStore.initialize()
  }

  // Standard auth guard
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (to.matched.some((record) => record.meta.adminOnly) && !authStore.isAdmin) {
      return '/'
    }
  }
  // Prevent logged-in users from seeing login/register pages
  if (
    authStore.isAuthenticated &&
    (to.path === '/login' ||
      to.path === '/register' ||
      to.path.startsWith('/invitation') ||
      to.path === '/forgot-password' ||
      to.path.startsWith('/reset-password/'))
  ) {
    return '/projects'
  }
  return true
})

// Per-route document titles from `meta.titleKey` (child meta wins over
// parent), resolved through the global i18n instance at navigation time.
function applyDocumentTitle(): void {
  const key = router.currentRoute.value.meta.titleKey
  const title = typeof key === 'string' ? i18n.global.t(key) : ''
  document.title = title ? `${title} · LLMAIx` : 'LLMAIx'
}

router.afterEach(applyDocumentTitle)

// Re-title the current page when the user switches language (the locale is a
// ref on the composition-mode global i18n, so it's cheaply watchable).
watch(i18n.global.locale, applyDocumentTitle)

export default router
