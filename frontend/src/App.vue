<script setup>
import { ref, watch } from 'vue'
import NavSidebar from '@/components/NavSidebar.vue'
import WalletConnect from '@/components/WalletConnect.vue'
import DemoWatermark from '@/components/DemoWatermark.vue'
import { Search } from 'lucide-vue-next'
import { useWalletStore } from '@/stores/wallet'
import { useSignalsStore } from '@/stores/signals'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const wallet = useWalletStore()
const signals = useSignalsStore()
const auth = useAuthStore()
const router = useRouter()
useThemeStore()

const searchQuery = ref('')
function searchWallet() {
  const q = searchQuery.value.trim()
  if (q) {
    router.push(`/wallet/${q}`)
    searchQuery.value = ''
  }
}

onMounted(() => {
  if (auth.isAuthenticated) {
    signals.fetchSignals()
    signals.connectWebSocket()
  }
})

watch(() => auth.isAuthenticated, (val) => {
  if (val) {
    signals.fetchSignals()
    signals.connectWebSocket()
  }
})
</script>

<template>
  <div v-if="auth.isAuthenticated" class="flex h-screen bg-cyber-bg overflow-hidden">
    <NavSidebar />

    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-16 glass rounded-none border-x-0 border-t-0 flex items-center justify-between px-6 z-40">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-display font-semibold text-gradient">Mantle Vision</h1>
          <span class="text-[10px] font-mono text-cyber-accent/40 bg-cyber-accent/5 px-2 py-0.5 rounded-full hidden sm:inline">Wallet Intelligence</span>
          <span class="text-xs text-cyber-muted font-mono">v1.0.0</span>
          <span class="text-[10px] font-mono text-cyber-accent/60 bg-cyber-accent/5 px-2 py-0.5 rounded-full">
            {{ auth.displayName }}
          </span>
        </div>
        <div class="flex items-center gap-3">
          <div class="relative">
            <input
              v-model="searchQuery"
              placeholder="Search wallet..."
              class="w-44 bg-white/5 border border-white/10 rounded-xl pl-3 pr-8 py-1.5 text-xs font-mono text-cyber-text placeholder:text-cyber-muted/40 focus:outline-none focus:border-cyber-accent/30 transition-colors"
              @keyup.enter="searchWallet"
            />
            <Search class="w-3.5 h-3.5 absolute right-2.5 top-1/2 -translate-y-1/2 text-cyber-muted/30 pointer-events-none" />
          </div>
          <WalletConnect />
          <button @click="auth.logout(); router.push('/login')"
            class="text-xs text-cyber-muted hover:text-cyber-danger transition-colors font-mono">
            Logout
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-6">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <div class="scanlines"></div>
    <DemoWatermark v-if="wallet.isDemo" />
  </div>
  <div v-else>
    <router-view />
  </div>
</template>
