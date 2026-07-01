import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** Route requires authentication; unauthenticated users redirect to /login. */
    requiresAuth?: boolean
    /** Route requires admin role; non-admins redirect to /. */
    adminOnly?: boolean
  }
}
