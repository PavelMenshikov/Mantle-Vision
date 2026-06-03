<script setup>
import { computed, onMounted } from 'vue'
import StatsGrid from '@/components/StatsGrid.vue'
import SignalCard from '@/components/SignalCard.vue'
import PortfolioChart from '@/components/PortfolioChart.vue'
import TokenPrice from '@/components/TokenPrice.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import WhaleCard from '@/components/WhaleCard.vue'
import { useSignalsStore } from '@/stores/signals'
import { usePortfolioStore } from '@/stores/portfolio'

const signals = useSignalsStore()
const portfolio = usePortfolioStore()

onMounted(() => {
  portfolio.fetchPortfolio()
  portfolio.fetchHistory()
})

const stats = computed(() => [
  { label: 'Total Signals', value: signals.signalCount, icon: 'signals', accent: 'green', change: 12 },
  { label: 'Active Whales', value: 8, icon: 'whales', accent: 'blue', change: -3 },
  { label: 'Demo P&L', value: '$' + portfolio.totalPnl.toFixed(2), icon: 'pnl', accent: portfolio.totalPnl >= 0 ? 'green' : 'red', change: portfolio.pnlPercent },
  { label: 'Network', value: 'Mantle', icon: 'network', accent: 'amber', change: 99.9 },
])

const demoWhales = [
  { address: '0x8f3B...d1b3', label: 'DeFi Whale', totalValue: 2450000, lastActive: new Date(Date.now() - 3600000).toISOString(), risk: 8, txCount: 342 },
  { address: '0x7a1E...9f42', label: 'LP Provider', totalValue: 890000, lastActive: new Date(Date.now() - 7200000).toISOString(), risk: 3, txCount: 156 },
  { address: '0x2b4F...c7a1', label: 'Trader', totalValue: 1250000, lastActive: new Date(Date.now() - 1800000).toISOString(), risk: 6, txCount: 891 },
]
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Dashboard</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Real-time on-chain intelligence overview</p>
      </div>
      <NeonButton variant="primary" size="sm" @click="signals.fetchSignals()">
        ⟳ Refresh
      </NeonButton>
    </div>

    <StatsGrid :stats="stats" />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-4">
        <GlassCard accent="green">
          <PortfolioChart :data="portfolio.history" :height="250" />
        </GlassCard>

        <div>
          <h3 class="text-sm font-display font-semibold text-white mb-3 flex items-center gap-2">
            ⚡ Recent Signals
            <span class="text-xs text-cyber-muted font-mono font-normal">({{ signals.recentSignals.length }})</span>
          </h3>
          <div class="space-y-3">
            <SignalCard v-for="signal in signals.recentSignals.slice(0, 4)" :key="signal.id" :signal="signal" />
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <TokenPrice />

        <div>
          <h3 class="text-sm font-display font-semibold text-white mb-3 flex items-center gap-2">
            🐋 Whale Activity
          </h3>
          <div class="space-y-3">
            <WhaleCard v-for="whale in demoWhales" :key="whale.address" :whale="whale" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
