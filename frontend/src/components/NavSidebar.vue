<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Zap, List, Users, Settings } from 'lucide-vue-next'
import faviconUrl from '@/assets/favicon.png'

const route = useRoute()
const router = useRouter()

const iconMap = {
  Dashboard: LayoutDashboard,
  Signals: Zap,
  Transactions: List,
  Whales: Users,
  Settings,
}

const navItems = [
  { name: 'Dashboard', path: '/', icon: 'Dashboard' },
  { name: 'Signals', path: '/signals', icon: 'Signals' },
  { name: 'Transactions', path: '/transactions', icon: 'Transactions' },
  { name: 'Whales', path: '/whales', icon: 'Whales' },
  { name: 'Settings', path: '/settings', icon: 'Settings' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function navigate(path) {
  router.push(path)
}
</script>

<template>
  <aside class="w-16 glass rounded-none border-y-0 border-l-0 flex flex-col items-center py-4 gap-2 z-50 flex-shrink-0">
    <div class="w-10 h-10 rounded-xl bg-accent-gradient flex items-center justify-center shadow-neon-green mb-4 overflow-hidden">
      <img :src="faviconUrl" alt="Mantle Vision" class="w-full h-full object-contain p-1.5" />
    </div>

    <nav class="flex flex-col items-center gap-1 flex-1">
      <button
        v-for="item in navItems"
        :key="item.name"
        @click="navigate(item.path)"
        :title="item.name"
        :class="[
          'w-10 h-10 rounded-xl flex items-center justify-center text-sm transition-all duration-200 relative group',
          isActive(item.path)
            ? 'text-cyber-accent bg-cyber-accent/10 shadow-neon-green'
            : 'text-cyber-muted hover:text-cyber-text hover:bg-white/5'
        ]"
      >
        <component :is="iconMap[item.icon]" class="relative z-10 w-4 h-4" />
        <div
          v-if="isActive(item.path)"
          class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-cyber-accent rounded-r-full shadow-neon-green"
        ></div>
        <div class="absolute left-full ml-3 px-2 py-1 rounded-lg glass text-xs whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
          {{ item.name }}
        </div>
      </button>
    </nav>

    <div class="w-8 h-px bg-white/5 my-2"></div>

    <div class="text-[10px] text-cyber-muted font-mono text-center leading-tight">
      <div>AI</div>
      <div>v1.0</div>
    </div>
  </aside>
</template>
