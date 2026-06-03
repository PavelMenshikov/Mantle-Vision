<script setup>
import { useWalletStore } from '@/stores/wallet'

const wallet = useWalletStore()

function handleToggle() {
  wallet.toggleMode()
}
</script>

<template>
  <div class="flex items-center gap-4">
    <div class="flex glass !p-1 rounded-xl gap-1">
      <button
        @click="wallet.mode = 'demo'"
        :class="[
          'px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200',
          wallet.isDemo ? 'bg-cyber-accent/20 text-cyber-accent shadow-neon-green' : 'text-cyber-muted hover:text-white'
        ]"
      >
        DEMO
      </button>
      <button
        @click="wallet.mode = 'real'"
        :class="[
          'px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200',
          wallet.isReal ? 'bg-cyber-electric/20 text-cyber-electric shadow-neon-blue' : 'text-cyber-muted hover:text-white'
        ]"
      >
        REAL
      </button>
    </div>

    <template v-if="wallet.connected">
      <div v-if="wallet.isDemo" class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyber-accent/10 border border-cyber-accent/20">
        <span class="w-2 h-2 rounded-full bg-cyber-accent animate-pulse-glow"></span>
        <span class="text-xs font-mono text-cyber-accent">{{ wallet.shortAddress }}</span>
      </div>
      <div v-else class="flex items-center gap-3 px-3 py-1.5 rounded-xl bg-cyber-electric/10 border border-cyber-electric/20">
        <span class="w-2 h-2 rounded-full bg-cyber-electric"></span>
        <span class="text-xs font-mono text-cyber-electric">{{ wallet.shortAddress }}</span>
        <span class="text-xs text-cyber-muted">|</span>
        <span class="text-xs font-mono text-cyber-electric">{{ wallet.formattedBalance }}</span>
      </div>
      <button
        @click="wallet.disconnect()"
        class="text-xs text-cyber-muted hover:text-cyber-danger transition-colors"
      >
        Disconnect
      </button>
    </template>

    <template v-else>
      <button
        @click="wallet.connect('real')"
        class="relative px-5 py-2 text-sm font-medium rounded-xl bg-accent-gradient text-black hover:shadow-neon-green transition-all duration-200 active:scale-95"
      >
        Connect
      </button>
    </template>
  </div>
</template>
