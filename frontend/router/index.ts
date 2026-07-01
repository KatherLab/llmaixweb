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

const FirstAdminSetup = () => import('@/views/FirstAdminSetup.vue')

import { useAuthStore } from '@/stores/auth'
import { useFirstAdminStore } from '@/stores/firstAdmin'

const routes: RouteRecordRaw[] = [
  // Authenticated app routes (navbar visible!)
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', component: Landing },
      { path: 'projects', component: ProjectOverview, meta: { requiresAuth: true } },
      {
        path: 'account',
        component: AccountSettings,
        meta: { requiresAuth: true },
      },
      {
        path: 'projects/:projectId',
        component: ProjectDetail,
        props: true,
        meta: { requiresAuth: true },
      },
      // Admin routes
      {
        path: 'admin/user-management',
        component: AdminUserManagement,
        meta: { requiresAuth: true, adminOnly: true },
      },
      {
        path: 'admin',
        component: AdminDashboard,
        meta: { requiresAuth: true, adminOnly: true },
        children: [
          { path: 'settings', component: AdminSettings },
          { path: 'sso', component: AdminSSO },
          { path: 'celery', component: AdminCelery },
          { path: '', redirect: '/admin/settings' },
        ],
      },
    ],
  },

  // Public routes (no navbar)
  {
    path: '/',
    component: AuthLayout,
    children: [
      { path: 'login', component: Login },
      { path: 'register', component: Register },
      { path: 'forgot-password', component: ForgotPassword },
      { path: 'reset-password/:token', component: ResetPassword },
      { path: 'invitation/:token', component: InvitationLanding },
      { path: 'auth/sso/complete', component: SsoComplete },
      { path: 'first-admin', component: FirstAdminSetup },
    ],
  },

  // 404 fallback
  { path: '/:pathMatch(.*)*', component: NotFound },
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
    return next('/')
  }
  return next()
})

export default router
