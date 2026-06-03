<script setup>
import { ref } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { useWalletStore } from '@/stores/wallet'

const wallet = useWalletStore()

const apiKeys = ref([
  { name: 'Mantle RPC', status: 'connected', key: 'https://rpc.mantle.xyz' },
  { name: 'WebSocket', status: 'connected', key: 'wss://ws.mantle.xyz' },
  { name: 'Etherscan API', status: 'disconnected', key: '••••••••' },
])

const agentInfo = {
  name: 'Mantle Vision Agent',
  version: '1.0.0',
  model: 'AI-Orchestrator v3',
  uptime: '99.97%',
  lastTraining: '2026-06-01',
}

const networkInfo = {
  chain: 'Mantle',
  chainId: 5000,
  rpc: 'https://rpc.mantle.xyz',
  blockTime: '1.2s',
  gasPrice: '0.015 Gwei',
}

function toggleConnection(index) {
  const key = apiKeys.value[index]
  key.status = key.status === 'connected' ? 'disconnected' : 'connected'
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div>
      <h2 class="text-2xl font-display font-bold text-gradient">Settings</h2>
      <p class="text-sm text-cyber-muted font-mono mt-1">System configuration and information</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <GlassCard accent="blue">
        <h3 class="text-sm font-display font-semibold text-white mb-4">🔌 API Connections</h3>
        <div class="space-y-3">
          <div v-for="(key, index) in apiKeys" :key="key.name" class="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
            <div>
              <div class="text-sm font-medium text-white">{{ key.name }}</div>
              <div class="text-xs font-mono text-cyber-muted mt-0.5">{{ key.key }}</div>
            </div>
            <div class="flex items-center gap-2">
              <span :class="[
                'text-[10px] font-mono px-2 py-0.5 rounded-full',
                key.status === 'connected' ? 'bg-cyber-accent/10 text-cyber-accent' : 'bg-cyber-danger/10 text-cyber-danger'
              ]">
                {{ key.status === 'connected' ? '● Connected' : '○ Disconnected' }}
              </span>
              <NeonButton
                :variant="key.status === 'connected' ? 'danger' : 'primary'"
                size="sm"
                @click="toggleConnection(index)"
              >
                {{ key.status === 'connected' ? 'Disconnect' : 'Connect' }}
              </NeonButton>
            </div>
          </div>
        </div>
      </GlassCard>

      <GlassCard accent="green">
        <h3 class="text-sm font-display font-semibold text-white mb-4">🤖 Agent Identity</h3>
        <div class="space-y-3">
          <div v-for="(value, key) in agentInfo" :key="key" class="flex items-center justify-between py-1.5">
            <span class="text-xs text-cyber-muted font-mono capitalize">{{ key.replace(/([A-Z])/g, ' $1') }}</span>
            <span class="text-xs font-mono text-white">{{ value }}</span>
          </div>
        </div>
      </GlassCard>

      <GlassCard accent="amber">
        <h3 class="text-sm font-display font-semibold text-white mb-4">🌐 Network</h3>
        <div class="space-y-3">
          <div v-for="(value, key) in networkInfo" :key="key" class="flex items-center justify-between py-1.5">
            <span class="text-xs text-cyber-muted font-mono capitalize">{{ key.replace(/([A-Z])/g, ' $1') }}</span>
            <span class="text-xs font-mono text-white">{{ value }}</span>
          </div>
        </div>
      </GlassCard>

      <GlassCard accent="red">
        <h3 class="text-sm font-display font-semibold text-white mb-4">⚙️ Preferences</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-white">Demo Mode</div>
              <div class="text-xs text-cyber-muted font-mono">Paper trading with $10K balance</div>
            </div>
            <button
              @click="wallet.toggleMode()"
              :class="[
                'w-12 h-6 rounded-full transition-all duration-300 relative',
                wallet.isDemo ? 'bg-cyber-accent/30' : 'bg-white/10'
              ]"
            >
              <div :class="[
                'w-5 h-5 rounded-full absolute top-0.5 transition-all duration-300',
                wallet.isDemo ? 'bg-cyber-accent left-6' : 'bg-white/50 left-0.5'
              ]"></div>
            </button>
          </div>

          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-white">Real-Time Updates</div>
              <div class="text-xs text-cyber-muted font-mono">WebSocket live streaming</div>
            </div>
            <div class="w-12 h-6 rounded-full bg-cyber-accent/30 relative">
              <div class="w-5 h-5 rounded-full bg-cyber-accent absolute top-0.5 left-6"></div>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-white">Theme</div>
              <div class="text-xs text-cyber-muted font-mono">Cyberpunk Dark (only option)</div>
            </div>
            <span class="text-xs font-mono text-cyber-accent">✦ Dark</span>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>
