// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Views
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Landing from '../views/Landing.vue'
import AdminUserManagement from '../views/AdminUserManagement.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'login',
      component: Login
    },
    {
      path: '/register',
      name: 'register',
      component: Register
    },
    // Student routes
    {
      path: '/landing',
      name: 'landing',
      component: Landing,
      meta: { requiresAuth: true }
    },
    {
    // New route for User Management
    path: '/admin/user-management',
    name: 'AdminUserManagement',
    component: AdminUserManagement,
    meta: { requiresAdmin: true }
  },

  ]
})

router.beforeEach(async (to, from, next) => {
  console.log('beforeEach hook triggered')
  console.log('Navigating from:', from.path)
  console.log('Navigating to:', to.path)

  const authStore = useAuthStore()
  console.log('Auth store state:', authStore.$state)

  // Fetch user data before checking role-based access control
  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchUser()
  }

  const navigationFlag = authStore.navigationFlag
  console.log('Navigation flag:', navigationFlag)

  if (navigationFlag) {
    console.log('Navigation flag is set, preventing recursive navigation')
    next(false)
    return
  }

  try {
    console.log('Checking authentication...')
    // Handle authentication
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      console.log('Authentication required, but user is not authenticated. Redirecting to login.')
      authStore.navigationFlag = true
      next('/login')
      return
    }

    // If user is authenticated and tries to access login/register
    console.log('Checking if user is authenticated and trying to access login/register...')
    if (authStore.isAuthenticated && (to.path === '/login' || to.path === '/register')) {
      console.log('User is authenticated, redirecting to dashboard.')
      if (authStore.isAdmin) {
        console.log('User is admin, redirecting to admin dashboard.')
        authStore.navigationFlag = true
        next('/landing')
      } else {
        console.log('User is not admin, redirecting to student dashboard.')
        authStore.navigationFlag = true
        next('/landing')
      }
      return
    }

    // Handle role-based access
    console.log('Checking role-based access...')
    if (to.meta.role) {
      const userRole = authStore.user?.role
      console.log('User role:', userRole)
      console.log('Required role:', to.meta.role)
      if (to.meta.role === 'admin' && userRole !== 'admin') {
        console.log('User is not admin, redirecting to user dashboard.')
        authStore.navigationFlag = true
        next('/landing')
        return
      }
      if (to.meta.role === 'user' && userRole !== 'user') {
        console.log('User is not user, redirecting to admin dashboard.')
        authStore.navigationFlag = true
        next('/landing')
        return
      }
    }

    console.log('No redirects needed, proceeding with navigation.')
    next()
  } catch (error) {
    console.error('Navigation error:', error)
    next(false)
  } finally {
    console.log('Resetting navigation flag.')
    authStore.navigationFlag = false
  }
})

export default router