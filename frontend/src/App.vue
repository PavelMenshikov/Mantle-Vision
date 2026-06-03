<script setup>
import NavSidebar from '@/components/NavSidebar.vue'
import WalletConnect from '@/components/WalletConnect.vue'
import DemoWatermark from '@/components/DemoWatermark.vue'
import { useWalletStore } from '@/stores/wallet'
import { useSignalsStore } from '@/stores/signals'
import { onMounted } from 'vue'

const wallet = useWalletStore()
const signals = useSignalsStore()

onMounted(() => {
  if (!wallet.connected) {
    wallet.connect('demo')
  }
  signals.fetchSignals()
  signals.connectWebSocket()
})
</script>

<template>
  <div class="flex h-screen bg-cyber-bg overflow-hidden">
    <NavSidebar />

    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-16 glass rounded-none border-x-0 border-t-0 flex items-center justify-between px-6 z-40">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-display font-semibold text-gradient">Mantle Vision</h1>
          <span class="text-xs text-cyber-muted font-mono">v1.0.0</span>
        </div>
        <WalletConnect />
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
</template>
