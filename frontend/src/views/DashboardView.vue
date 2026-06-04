<script setup>
import { computed, ref, onMounted } from 'vue'
import StatsGrid from '@/components/StatsGrid.vue'
import SignalCard from '@/components/SignalCard.vue'
import PortfolioChart from '@/components/PortfolioChart.vue'
import TokenPrice from '@/components/TokenPrice.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { useSignalsStore } from '@/stores/signals'
import { usePortfolioStore } from '@/stores/portfolio'

const signals = useSignalsStore()
const portfolio = usePortfolioStore()

const scannerStatus = ref(null)

onMounted(() => {
  portfolio.fetchPortfolio()
  portfolio.fetchHistory()
  fetchScannerStatus()
})

async function fetchScannerStatus() {
  try {
    const res = await fetch('/api/scanner/status')
    scannerStatus.value = await res.json()
  } catch {}
}

const stats = computed(() => [
  { label: 'Total Signals', value: signals.signalCount, icon: 'signals', accent: 'green', change: 12 },
  { label: 'Active Whales', value: '—', icon: 'whales', accent: 'blue', change: 0 },
  { label: 'Portfolio P&L', value: portfolio.totalPnl === 0 ? '—' : '$' + portfolio.totalPnl.toFixed(2), icon: 'pnl', accent: portfolio.totalPnl >= 0 ? 'green' : 'red', change: portfolio.pnlPercent },
  { label: 'Network', value: 'Mantle', icon: 'network', accent: 'amber', change: 99.9 },
])

function formatTime(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleTimeString()
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Dashboard</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Real-time on-chain intelligence overview</p>
      </div>
      <NeonButton variant="primary" size="sm" @click="signals.fetchSignals(); fetchScannerStatus()">
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
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            ⚡ Recent Signals
            <span class="text-xs text-cyber-muted font-mono font-normal">({{ signals.recentSignals.length }})</span>
          </h3>
          <div v-if="signals.recentSignals.length" class="space-y-3">
            <SignalCard v-for="signal in signals.recentSignals.slice(0, 4)" :key="signal.id" :signal="signal" />
          </div>
          <div v-else class="text-center py-8 text-cyber-muted text-sm font-mono">
            No signals yet. Waiting for on-chain activity...
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <TokenPrice />

        <GlassCard accent="blue">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3">🔍 Scanner Status</h3>
          <div v-if="scannerStatus" class="space-y-2 text-xs font-mono">
            <div class="flex justify-between">
              <span class="text-cyber-muted">Block</span>
              <span class="text-cyber-text">#{{ scannerStatus.latest_block }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Chain</span>
              <span class="text-cyber-text capitalize">{{ scannerStatus.chain }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Mode</span>
              <span class="text-cyber-text uppercase">{{ scannerStatus.mode }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Interval</span>
              <span class="text-cyber-text">{{ scannerStatus.scanner_interval_s }}s</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Signals</span>
              <span class="text-cyber-text">{{ scannerStatus.total_signals }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Last Signal</span>
              <span class="text-cyber-text">{{ formatTime(scannerStatus.last_signal_at) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-cyber-muted">Prices</span>
              <span class="text-cyber-text">{{ scannerStatus.prices_cached.join(', ') || 'none' }}</span>
            </div>
            <div class="flex justify-between pt-2 border-t border-white/5">
              <span class="text-cyber-muted">Status</span>
              <span v-if="scannerStatus.scanner_active" class="text-cyber-accent">● Active</span>
              <span v-else class="text-cyber-danger">● Inactive</span>
            </div>
          </div>
          <div v-else class="text-center py-4 text-cyber-muted text-xs font-mono">
            Scanner offline
          </div>
        </GlassCard>
      </div>
    </div>
  </div>
</template>
