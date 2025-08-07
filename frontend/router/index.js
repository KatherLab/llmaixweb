import { createRouter, createWebHistory } from 'vue-router'

import Landing from '@/views/Landing.vue'
import AppLayout from '@/views/AppLayout.vue'
import AuthLayout from '@/views/AuthLayout.vue'

import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import InvitationLanding from '@/views/InvitationLandingPage.vue'
import NotFound from '@/views/NotFound.vue'

import ProjectOverview from '@/views/ProjectOverview.vue'
import ProjectDetail from '@/views/ProjectDetail.vue'
import AdminUserManagement from '@/views/AdminUserManagement.vue'
import AdminDashboard from '@/views/AdminDashboard.vue'
import AdminSettings from '@/views/AdminSettings.vue'
import AdminCelery from '@/views/AdminCelery.vue'

import FirstAdminSetup from '@/views/FirstAdminSetup.vue'

import { useAuthStore } from '@/stores/auth'
import { useFirstAdminStore } from '@/stores/firstAdmin'

const routes = [
  // Authenticated app routes (navbar visible!)
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', component: Landing },
      { path: 'projects', component: ProjectOverview, meta: { requiresAuth: true } },
      { path: 'projects/:projectId', component: ProjectDetail, props: true, meta: { requiresAuth: true } },
      // Admin routes
      { path: 'admin/user-management', component: AdminUserManagement, meta: { requiresAuth: true, adminOnly: true } },
      {
        path: 'admin',
        component: AdminDashboard,
        meta: { requiresAuth: true, adminOnly: true },
        children: [
          { path: 'settings', component: AdminSettings },
          { path: 'celery', component: AdminCelery },
          { path: '', redirect: '/admin/settings' }
        ]
      }
    ]
  },

  // Public routes (no navbar)
  {
    path: '/',
    component: AuthLayout,
    children: [
      { path: 'login', component: Login },
      { path: 'register', component: Register },
      { path: 'invitation/:token', component: InvitationLanding },
      { path: 'first-admin', component: FirstAdminSetup }
    ]
  },

  // 404 fallback
  { path: '/:pathMatch(.*)*', component: NotFound }
]

// Router creation
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Auth/admin/first-admin guard
router.beforeEach(async (to, from, next) => {
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
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
    if (to.matched.some(record => record.meta.adminOnly) && !authStore.isAdmin) {
      return next('/')
    }
  }
  // Prevent logged-in users from seeing login/register pages
  if (
    authStore.isAuthenticated &&
    (to.path === '/login' || to.path === '/register' || to.path.startsWith('/invitation'))
  ) {
    return next('/')
  }
  return next()
})

export default router
