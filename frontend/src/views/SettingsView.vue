<script setup>
import { computed } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import TelegramConnect from '@/components/TelegramConnect.vue'
import { Globe, Satellite, Settings } from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

const themeOptions = [
  { id: 'dark', label: 'Dark', accent: 'text-cyber-accent' },
  { id: 'silver', label: 'Silver', accent: 'text-cyber-electric' },
  { id: 'light', label: 'Light', accent: 'text-cyber-warning' },
]

const networkInfo = {
  chain: 'Mantle Sepolia',
  chainId: 5003,
  rpc: 'https://rpc.sepolia.mantle.xyz',
  blockTime: '1.2s',
  gasPrice: '0.015 Gwei',
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div>
      <h2 class="text-2xl font-display font-bold text-gradient">Settings</h2>
      <p class="text-sm text-cyber-muted font-mono mt-1">System configuration and information</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <GlassCard accent="amber">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-4 flex items-center gap-2">
          <Globe class="w-4 h-4 text-cyber-warning" />
          Network
        </h3>
        <div class="space-y-3">
          <div v-for="(value, key) in networkInfo" :key="key" class="flex items-center justify-between py-1.5">
            <span class="text-xs text-cyber-muted font-mono capitalize">{{ key.replace(/([A-Z])/g, ' $1') }}</span>
            <span class="text-xs font-mono text-cyber-text">{{ value }}</span>
          </div>
        </div>
      </GlassCard>

      <GlassCard accent="electric">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-4 flex items-center gap-2">
          <Satellite class="w-4 h-4 text-cyber-electric" />
          Telegram
        </h3>
        <p class="text-xs text-cyber-muted font-mono mb-4">
          Get real-time alerts on Telegram when anomalies, insider clusters, or risks are detected.
        </p>
        <TelegramConnect />
      </GlassCard>

      <GlassCard accent="red">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-4 flex items-center gap-2">
          <Settings class="w-4 h-4 text-cyber-danger" />
          Preferences
        </h3>
        <div class="space-y-4">
          <div>
            <div class="text-sm text-cyber-text mb-2">Theme</div>
            <div class="flex glass !p-1 rounded-xl gap-1">
              <button
                v-for="t in themeOptions"
                :key="t.id"
                @click="theme.setTheme(t.id)"
                :class="[
                  'flex-1 px-3 py-1.5 text-xs font-mono font-medium rounded-lg transition-all duration-200',
                  theme.current === t.id
                    ? 'bg-white/10 ' + t.accent
                    : 'text-cyber-muted hover:text-cyber-text'
                ]"
              >
                {{ t.label }}
              </button>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>
