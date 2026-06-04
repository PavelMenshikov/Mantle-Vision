import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/signals',
    name: 'Signals',
    component: () => import('@/views/SignalsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/transactions',
    name: 'Transactions',
    component: () => import('@/views/PortfolioView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/whales',
    name: 'Whales',
    component: () => import('@/views/WhalesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/wallet/:address',
    name: 'Wallet',
    component: () => import('@/views/WalletView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('mv_token')
  const tgUser = localStorage.getItem('mv_tg_username')
  const isAuthed = !!token || !!tgUser

  if (to.meta.requiresAuth && !isAuthed) {
    next('/login')
  } else if (to.path === '/login' && isAuthed) {
    next('/')
  } else {
    next()
  }
})

export default router
