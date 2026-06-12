<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import StatsGrid from '@/components/StatsGrid.vue'
import TransactionStream from '@/components/TransactionStream.vue'
import TokenPrice from '@/components/TokenPrice.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { RefreshCw, Zap, Eye, Search, Bell, AlertTriangle, TrendingUp, Users, Activity } from 'lucide-vue-next'
import { useSignalsStore } from '@/stores/signals'

const router = useRouter()
const signals = useSignalsStore()

const scannerStatus = ref(null)
const whaleCount = ref('—')
let abortCtrl = null
let statusTimer = null
let alertTimer = null

const demoWallets = [
  { address: '0xcEf7c66AEb06265FB92FcB6C7184115428416c3f', label: 'Deployer Wallet' },
  { address: '0x77a5CeADd28E23C1fFA85ED4814Bf29C8c31F21f', label: 'AgentIdentity Contract' },
]

onMounted(() => {
  fetchScannerStatus()
  fetchWhaleCount()
  fetchAlerts()
  statusTimer = setInterval(fetchScannerStatus, 15000)
  alertTimer = setInterval(fetchAlerts, 10000)
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
  if (alertTimer) clearInterval(alertTimer)
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

async function fetchAlerts() {
  try {
    const res = await fetch('/api/alerts?limit=20')
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length) {
        const notifTypes = ['whale_alert', 'anomaly', 'smart_money', 'insider_cluster', 'tracked_wallet']
        data.forEach(a => {
          if (notifTypes.includes(a.type) && !signals.notifications.some(n => n._stored_at === a._stored_at)) {
            signals.addNotification(a)
          }
        })
      }
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
            Live Feed
            <span class="text-xs text-cyber-muted font-mono font-normal">({{ signals.notifications.length }})</span>
          </h3>
          <div v-if="signals.notifications.length" class="space-y-2">
            <div v-for="(n, i) in signals.notifications.slice(0, 20)" :key="i"
              class="flex items-start gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5 text-xs font-mono hover:bg-white/[0.04] transition-colors">
              <Activity v-if="n.type === 'whale_alert'" class="w-3 h-3 text-cyber-accent mt-0.5 flex-shrink-0" />
              <AlertTriangle v-if="n.type === 'anomaly'" class="w-3 h-3 text-cyber-danger mt-0.5 flex-shrink-0" />
              <TrendingUp v-if="n.type === 'smart_money'" class="w-3 h-3 text-cyber-electric mt-0.5 flex-shrink-0" />
              <Users v-if="n.type === 'insider_cluster'" class="w-3 h-3 text-cyber-warning mt-0.5 flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="text-cyber-text">
                  <template v-if="n.type === 'whale_alert'">
                    <span class="text-cyber-accent">Whale</span>
                    <button @click="router.push(`/wallet/${n.address}`)" class="hover:text-cyber-accent transition-colors ml-1">{{ n.wallet_type }}: {{ n.address?.slice(0,6) }}...{{ n.address?.slice(-4) }}</button>
                    <span class="text-cyber-muted ml-1">{{ n.score ? (n.score*100).toFixed(0)+'%' : '' }} | {{ Number(n.volume||0).toFixed(1) }} ETH</span>
                  </template>
                  <template v-else-if="n.type === 'anomaly'">
                    <span class="text-cyber-danger">Anomaly</span>
                    <button @click="router.push(`/wallet/${n.wallet}`)" class="hover:text-cyber-accent transition-colors ml-1">{{ n.wallet?.slice(0,6) }}...{{ n.wallet?.slice(-4) }}</button>
                    <span class="text-cyber-muted ml-1">{{ n.anomaly_score ? (n.anomaly_score*100).toFixed(0)+'%' : '' }}</span>
                  </template>
                  <template v-else-if="n.type === 'smart_money'">
                    <span class="text-cyber-electric">Smart Money</span>
                    <span v-for="(wallets, asset) in n.assets" :key="asset" class="ml-1">
                      <button v-for="w in wallets.slice(0,1)" :key="w.address" @click="router.push(`/wallet/${w.address}`)" class="hover:text-cyber-electric transition-colors">{{ w.address?.slice(0,6) }}... moved {{ Number(w.volume).toFixed(1) }} {{ asset }}</button>
                    </span>
                  </template>
                  <template v-else-if="n.type === 'insider_cluster'">
                    <span class="text-cyber-warning">Insider Cluster</span>
                    <span class="ml-1">{{ n.size }} wallets ({{ n.confidence ? (n.confidence*100).toFixed(0)+'%' : '' }})</span>
                  </template>
                  <template v-else-if="n.type === 'tracked_wallet'">
                    <span class="text-cyber-muted">Tracked</span>
                    <button @click="router.push(`/wallet/${n.address}`)" class="hover:text-cyber-accent transition-colors ml-1">{{ n.address?.slice(0,6) }}... moved {{ Number(n.value_eth||0).toFixed(1) }} MNT</button>
                  </template>
                </div>
                <div v-if="n.ai_reasoning" class="text-[10px] text-cyber-muted/60 mt-0.5 line-clamp-2">{{ n.ai_reasoning }}</div>
                <button v-if="n.type === 'whale_alert' || n.type === 'anomaly' || n.type === 'tracked_wallet'" @click="router.push(`/wallet/${n.address || n.wallet}`)" class="text-[9px] text-cyber-electric/70 hover:text-cyber-electric transition-colors underline mt-1">Deep Investigate →</button>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-8 text-cyber-muted text-sm font-mono">
            Waiting for on-chain alerts...
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

        <GlassCard accent="red">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <Bell class="w-4 h-4 text-cyber-danger" />
            Latest Alerts
            <span v-if="signals.notifications.length" class="text-xs font-mono text-cyber-muted">({{ signals.notifications.length }})</span>
          </h3>
          <div v-if="signals.notifications.length" class="space-y-1">
            <div v-for="(n, i) in signals.notifications.slice(0, 3)" :key="i"
              class="text-xs font-mono text-cyber-text truncate flex items-center gap-1 px-1 py-1 hover:bg-white/[0.03] rounded transition-colors">
              <Activity v-if="n.type === 'whale_alert'" class="w-2.5 h-2.5 text-cyber-accent flex-shrink-0" />
              <AlertTriangle v-if="n.type === 'anomaly'" class="w-2.5 h-2.5 text-cyber-danger flex-shrink-0" />
              <TrendingUp v-if="n.type === 'smart_money'" class="w-2.5 h-2.5 text-cyber-electric flex-shrink-0" />
              <Users v-if="n.type === 'insider_cluster'" class="w-2.5 h-2.5 text-cyber-warning flex-shrink-0" />
              <button @click="router.push(`/wallet/${n.address || n.wallet}`)" class="hover:text-cyber-accent transition-colors truncate min-w-0">
                {{ n.type === 'whale_alert' ? n.wallet_type : n.type }}: {{ (n.address || n.wallet || '').slice(0,6) }}
              </button>
            </div>
          </div>
          <div v-else class="text-center py-2 text-cyber-muted text-xs font-mono">
            No alerts yet
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
