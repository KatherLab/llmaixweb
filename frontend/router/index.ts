import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

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
        meta: { requiresAuth: true, title: 'Projects' },
      },
      {
        path: 'account',
        component: AccountSettings,
        meta: { requiresAuth: true, title: 'Account Settings' },
      },
      {
        path: 'projects/:projectId',
        component: ProjectDetail,
        props: true,
        meta: { requiresAuth: true, title: 'Project' },
      },
      // Admin routes — all nested under /admin so they share the AdminDashboard
      // tab layout (single entry point: the gear "Admin" link in the navbar).
      {
        path: 'admin',
        component: AdminDashboard,
        meta: { requiresAuth: true, adminOnly: true, title: 'Admin' },
        children: [
          {
            path: 'user-management',
            component: AdminUserManagement,
            meta: { title: 'User Management' },
          },
          { path: 'settings', component: AdminSettings, meta: { title: 'Admin Settings' } },
          { path: 'sso', component: AdminSSO, meta: { title: 'SSO Providers' } },
          { path: 'audit', component: AdminAudit, meta: { title: 'Audit Log' } },
          { path: 'celery', component: AdminCelery, meta: { title: 'Task Monitor' } },
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
      { path: 'login', component: Login, meta: { title: 'Sign in' } },
      { path: 'register', component: Register, meta: { title: 'Register' } },
      { path: 'forgot-password', component: ForgotPassword, meta: { title: 'Forgot Password' } },
      {
        path: 'reset-password/:token',
        component: ResetPassword,
        meta: { title: 'Reset Password' },
      },
      { path: 'invitation/:token', component: InvitationLanding, meta: { title: 'Invitation' } },
      { path: 'auth/sso/complete', component: SsoComplete, meta: { title: 'Signing in' } },
      { path: 'first-admin', component: FirstAdminSetup, meta: { title: 'First Admin Setup' } },
    ],
  },

  // 404 fallback
  { path: '/:pathMatch(.*)*', component: NotFound, meta: { title: 'Page Not Found' } },
]

// Router creation
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth/admin/first-admin guard
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const firstAdminStore = useFirstAdminStore()

  // Always check first admin state before anything else
  if (!firstAdminStore.checked) {
    await firstAdminStore.checkFirstAdmin()
  }

  // If first admin is needed, only allow access to /first-admin
  if (firstAdminStore.needsFirstAdmin && to.path !== '/first-admin') {
    return next('/first-admin')
  }
  // Prevent showing setup page after admin exists
  if (!firstAdminStore.needsFirstAdmin && to.path === '/first-admin') {
    return next('/')
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
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
    if (to.matched.some((record) => record.meta.adminOnly) && !authStore.isAdmin) {
      return next('/')
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
    return next('/projects')
  }
  return next()
})

// Per-route document titles from `meta.title` (child meta wins over parent).
router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = title ? `${title} · LLMAIx` : 'LLMAIx'
})

export default router
