<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import StatsGrid from '@/components/StatsGrid.vue'
import SignalCard from '@/components/SignalCard.vue'
import TransactionStream from '@/components/TransactionStream.vue'
import TokenPrice from '@/components/TokenPrice.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { RefreshCw, Zap, Eye, Search } from 'lucide-vue-next'
import { useSignalsStore } from '@/stores/signals'

const router = useRouter()
const signals = useSignalsStore()

const scannerStatus = ref(null)
const whaleCount = ref('—')
let abortCtrl = null

const demoWallets = [
  { address: '0xcEf7c66AEb06265FB92FcB6C7184115428416c3f', label: 'Deployer Wallet' },
  { address: '0x77a5CeADd28E23C1fFA85ED4814Bf29C8c31F21f', label: 'AgentIdentity Contract' },
]

onMounted(() => {
  fetchScannerStatus()
  fetchWhaleCount()
})

onUnmounted(() => {
  if (abortCtrl) abortCtrl.abort()
})

async function fetchScannerStatus() {
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()
  try {
    const res = await fetch('/api/scanner/status', { signal: abortCtrl.signal })
    scannerStatus.value = await res.json()
  } catch {}
}

async function fetchWhaleCount() {
  try {
    const res = await fetch('/api/whales')
    if (res.ok) {
      const data = await res.json()
      whaleCount.value = data.length
    }
  } catch {}
}

const stats = computed(() => [
  { label: 'Total Signals', value: signals.signalCount, icon: 'signals', accent: 'green', change: 12 },
  { label: 'Active Whales', value: whaleCount.value, icon: 'whales', accent: 'blue', change: 0 },
  { label: 'Network Uptime', value: '99.9%', icon: 'network', accent: 'amber', change: 0 },
  { label: 'Scanner Status', value: scannerStatus.value?.scanner_active ? 'Active' : '—', icon: 'signals', accent: scannerStatus.value?.scanner_active ? 'green' : 'red', change: 0 },
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
        <p class="text-sm text-cyber-muted font-mono mt-1">Wallet intelligence, anomaly detection, and transaction monitoring</p>
      </div>
      <NeonButton variant="primary" size="sm" @click="signals.fetchSignals(); fetchScannerStatus()">
        <RefreshCw class="w-4 h-4" />
      </NeonButton>
    </div>

    <StatsGrid :stats="stats" />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-4">
        <GlassCard accent="green">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-display font-semibold text-cyber-text flex items-center gap-2">
              <Zap class="w-4 h-4 text-cyber-accent" />
              Transaction Stream
            </h3>
            <span class="text-xs text-cyber-muted font-mono">Live</span>
          </div>
          <TransactionStream :height="250" />
        </GlassCard>

        <div>
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <Zap class="w-4 h-4 text-cyber-accent" />
            Recent Signals
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
        <GlassCard accent="electric">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <Search class="w-4 h-4 text-cyber-electric" />
            Try These Wallets
          </h3>
          <div class="space-y-2">
            <button
              v-for="w in demoWallets"
              :key="w.address"
              @click="router.push(`/wallet/${w.address}`)"
              class="w-full text-left px-3 py-2 rounded-lg border border-white/5 hover:border-cyber-electric/30 hover:bg-cyber-electric/5 transition-all text-xs font-mono group"
            >
              <div class="text-cyber-text group-hover:text-cyber-electric transition-colors">{{ w.label }}</div>
              <div class="text-cyber-muted truncate mt-0.5">{{ w.address.slice(0, 10) }}...{{ w.address.slice(-6) }}</div>
            </button>
          </div>
        </GlassCard>

        <TokenPrice />

        <GlassCard accent="blue">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <Eye class="w-4 h-4 text-cyber-electric" />
            Scanner Status
          </h3>
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
