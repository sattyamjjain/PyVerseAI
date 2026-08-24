import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '@/lib/firebase'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('@/views/LandingView.vue'),
      meta: { title: 'Genesis', guestOnly: true },
    },
    {
      path: '/sign-in',
      name: 'sign-in',
      component: () => import('@/views/SignInView.vue'),
      meta: { title: 'Sign in - Genesis', guestOnly: true },
    },
    {
      path: '/sign-up',
      name: 'sign-up',
      component: () => import('@/views/SignUpView.vue'),
      meta: { title: 'Create account - Genesis', guestOnly: true },
    },
    {
      path: '/projects',
      name: 'projects',
      component: () => import('@/views/ProjectsView.vue'),
      meta: { title: 'Projects - Genesis', requiresAuth: true },
    },
    {
      path: '/project/:id',
      name: 'workspace',
      component: () => import('@/views/WorkspaceView.vue'),
      meta: { title: 'Workspace - Genesis', requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: 'Not found - Genesis' },
    },
  ],
})

router.beforeEach(async (to) => {
  // Resolves instantly after the initial auth state settles.
  await auth.authStateReady()
  const user = auth.currentUser
  if (to.meta.requiresAuth && !user) {
    return { name: 'sign-in', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && user) {
    return { name: 'projects' }
  }
  return true
})

router.afterEach((to) => {
  if (typeof to.meta.title === 'string') document.title = to.meta.title
})

export default router
