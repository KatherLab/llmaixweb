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

import { useAuthStore } from '@/stores/auth'

// Pages always accessible (landing, login, register, invite, 404)
const publicRoutes = [
  {
    path: '/',
    component: AuthLayout,
    children: [
      { path: '', component: Landing },
      { path: 'login', component: Login },
      { path: 'register', component: Register },
      { path: 'invitation/:token', component: InvitationLanding }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    component: NotFound
  }
]

// Authenticated "app" pages (with nav, including landing)
const appRoutes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', component: Landing },
      { path: 'projects', component: ProjectOverview, meta: { requiresAuth: true } },
      { path: 'projects/:projectId', component: ProjectDetail, props: true, meta: { requiresAuth: true } },
      { path: 'admin/user-management', component: AdminUserManagement, meta: { requiresAuth: true } }
    ]
  }
]

// Use appRoutes first: logged-in users always get AppLayout and nav, even for /
const routes = [
  ...appRoutes,
  ...publicRoutes
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // If route requires auth, and not logged in, redirect to login
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
    return next()
  }

  // If logged in and navigating to /login, /register, or /invitation, show nav (AppLayout)
  if (
    authStore.isAuthenticated &&
    (to.path === '/login' || to.path === '/register' || to.path.startsWith('/invitation'))
  ) {
    return next('/')
  }

  // All others: continue
  return next()
})

export default router
