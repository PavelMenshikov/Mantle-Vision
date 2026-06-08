<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { AlertTriangle, ShieldCheck, Search, Users, ExternalLink, ArrowRight, Brain, Bug, DollarSign, Activity, CheckCircle, Fingerprint } from 'lucide-vue-next'
import FundingTree from '@/components/FundingTree.vue'

const route = useRoute()
const router = useRouter()

const address = ref(route.params.address || '')
const searchAddr = ref(address.value)
const analysis = ref(null)
const loading = ref(false)
const error = ref('')
const summary = ref(null)
const summaryLoading = ref(false)
const txs = ref([])
const txsLoading = ref(false)

onMounted(() => {
  if (address.value) {
    fetchAnalysis()
    fetchSummary()
    fetchTransactions()
  }
})

async function fetchAnalysis() {
  if (!address.value) return
  loading.value = true
  error.value = ''
  analysis.value = null
  try {
    const res = await fetch(`/api/wallet/${address.value}/analysis`)
    if (!res.ok) throw new Error('Wallet not found or analysis failed')
    analysis.value = await res.json()
  } catch (e) {
    error.value = e.message || 'Failed to analyze wallet'
  } finally {
    loading.value = false
  }
}

async function fetchSummary() {
  if (!address.value) return
  summaryLoading.value = true
  summary.value = null
  try {
    const res = await fetch(`/api/wallet/${address.value}/summary`)
    if (res.ok) summary.value = await res.json()
  } catch {} finally {
    summaryLoading.value = false
  }
}

async function fetchTransactions() {
  if (!address.value) return
  txsLoading.value = true
  txs.value = []
  try {
    const res = await fetch(`/api/wallet/${address.value}/transactions?limit=20`)
    if (res.ok) txs.value = await res.json()
  } catch {} finally {
    txsLoading.value = false
  }
}

function doSearch() {
  if (!searchAddr.value) return
  const a = searchAddr.value.trim()
  router.push(`/wallet/${a}`)
  address.value = a
  fetchAnalysis()
  fetchSummary()
  fetchTransactions()
}

function addrShort(a) {
  if (!a || a.length < 10) return a
  return a.slice(0, 6) + '...' + a.slice(-4)
}

function explorerUrl(a) {
  return `https://mantlescan.xyz/address/${a}`
}

const riskColor = computed(() => {
  if (!analysis.value) return 'text-cyber-muted'
  const r = analysis.value.risk_score
  if (r >= 0.7) return 'text-cyber-danger'
  if (r >= 0.4) return 'text-cyber-warning'
  return 'text-cyber-accent'
})

const riskLabel = computed(() => {
  if (!analysis.value) return ''
  const r = analysis.value.risk_score
  if (r >= 0.7) return 'HIGH RISK'
  if (r >= 0.4) return 'MEDIUM RISK'
  return 'LOW RISK'
})

const typeIcon = computed(() => {
  if (!analysis.value) return ShieldCheck
  const t = analysis.value.wallet_type
  if (t === 'insider' || t === 'anomaly') return AlertTriangle
  if (t === 'smart_money') return Brain
  if (t === 'exchange') return DollarSign
  if (t === 'fresh') return Fingerprint
  return ShieldCheck
})

const signalIconMap = {
  dollar: DollarSign,
  alert: AlertTriangle,
  users: Users,
  brain: Brain,
  shield: ShieldCheck,
  check: CheckCircle,
}

function formatTime(ts) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const now = Date.now()
  const diff = now - d.getTime()
  if (diff < 60000) return 'now'
  if (diff < 3600000) return Math.floor(diff / 60000) + 'm'
  return d.toLocaleTimeString()
}

function formatEth(val) {
  if (!val || val === 0) return ''
  if (val >= 1000) return val.toFixed(1)
  if (val >= 1) return val.toFixed(3)
  if (val >= 0.001) return val.toFixed(5)
  return '<0.001'
}

function txUrl(hash) {
  return `https://mantlescan.xyz/tx/${hash}`
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Wallet Intelligence</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Deep analysis of any Mantle address</p>
      </div>
      <a :href="explorerUrl(address)" target="_blank" class="text-xs text-cyber-electric hover:text-cyber-accent font-mono flex items-center gap-1 transition-colors">
        <ExternalLink class="w-3 h-3" />
        View on MantleScan
      </a>
    </div>

    <GlassCard accent="blue">
      <div class="flex gap-3">
        <input
          v-model="searchAddr"
          placeholder="0x... or .eth"
          class="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm font-mono text-cyber-text focus:outline-none focus:border-cyber-accent/50 transition-colors"
          @keyup.enter="doSearch"
        />
        <NeonButton variant="primary" size="sm" @click="doSearch" :disabled="loading">
          <Search class="w-4 h-4" />
        </NeonButton>
      </div>
    </GlassCard>

    <div v-if="loading" class="text-center py-12">
      <div class="inline-flex items-center gap-2 text-cyber-muted text-sm font-mono">
        <Activity class="w-4 h-4 animate-spin" />
        Analyzing wallet...
      </div>
    </div>

    <div v-else-if="error" class="text-center py-12">
      <Bug class="w-10 h-10 mx-auto mb-3 text-cyber-danger/50" />
      <p class="text-cyber-danger text-sm font-mono">{{ error }}</p>
    </div>

    <template v-else-if="analysis">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <GlassCard accent="green" class="lg:col-span-2">
          <div class="flex items-start gap-4">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center"
              :class="analysis.risk_score >= 0.7 ? 'bg-cyber-danger/10' : analysis.risk_score >= 0.4 ? 'bg-cyber-warning/10' : 'bg-cyber-accent/10'">
              <component :is="typeIcon" class="w-6 h-6"
                :class="analysis.risk_score >= 0.7 ? 'text-cyber-danger' : analysis.risk_score >= 0.4 ? 'text-cyber-warning' : 'text-cyber-accent'" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <code class="text-sm font-mono text-cyber-text break-all">{{ address }}</code>
                <a :href="explorerUrl(address)" target="_blank" class="text-cyber-muted/40 hover:text-cyber-accent flex-shrink-0">
                  <ExternalLink class="w-3.5 h-3.5" />
                </a>
              </div>
              <div class="flex flex-wrap items-center gap-2 mt-2">
                <span class="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold"
                  :class="analysis.risk_score >= 0.7 ? 'badge-red' : analysis.risk_score >= 0.4 ? 'badge-amber' : 'badge-green'">
                  {{ riskLabel }}
                </span>
                <span class="px-2.5 py-1 rounded-lg text-xs font-mono badge-blue capitalize">
                  {{ analysis.wallet_type }}
                </span>
                <span v-for="tag in analysis.tags.slice(0, 4)" :key="tag"
                  class="px-2 py-1 rounded-lg text-[10px] font-mono badge-blue">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard accent="amber">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-[10px] text-cyber-muted font-mono">Risk Score</div>
              <div :class="['text-2xl font-display font-bold', riskColor]">
                {{ (analysis.risk_score * 100).toFixed(0) }}
              </div>
            </div>
            <div>
              <div class="text-[10px] text-cyber-muted font-mono">Transactions</div>
              <div class="text-2xl font-display font-bold text-cyber-text">
                {{ analysis.tx_count || '—' }}
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      <GlassCard accent="red" v-if="analysis.signals.length">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
          <Fingerprint class="w-4 h-4 text-cyber-danger" />
          Intelligence Signals
        </h3>
        <div class="space-y-2">
          <div v-for="(sig, i) in analysis.signals" :key="i"
            class="flex items-start gap-3 p-3 rounded-xl"
            :class="sig.severity === 'danger' ? 'bg-cyber-danger/5 border border-cyber-danger/10' : sig.severity === 'warning' ? 'bg-cyber-warning/5 border border-cyber-warning/10' : 'bg-white/[0.02]'">
            <component :is="signalIconMap[sig.icon] || AlertTriangle" class="w-4 h-4 mt-0.5 flex-shrink-0"
              :class="sig.severity === 'danger' ? 'text-cyber-danger' : sig.severity === 'warning' ? 'text-cyber-warning' : sig.severity === 'clean' ? 'text-cyber-accent' : 'text-cyber-muted'" />
            <span class="text-sm text-cyber-text-secondary">{{ sig.text }}</span>
          </div>
        </div>
      </GlassCard>

      <div v-if="analysis.cluster" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard accent="electric">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <Users class="w-4 h-4 text-cyber-electric" />
            Cluster ({{ analysis.cluster.total_members }} wallets)
          </h3>
          <div class="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
            <div v-for="m in analysis.cluster.members" :key="m.address"
              class="flex items-center justify-between py-1 px-2 rounded-lg hover:bg-white/[0.02] text-xs font-mono">
              <a :href="`/wallet/${m.address}`" class="text-cyber-electric hover:text-cyber-accent transition-colors">
                {{ addrShort(m.address) }}
                <span v-if="m.role !== 'member'" class="text-[10px] text-cyber-muted ml-1">({{ m.role }})</span>
              </a>
              <span class="text-cyber-muted">{{ m.tx_count }} txns</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard accent="green">
          <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
            <DollarSign class="w-4 h-4 text-cyber-accent" />
            Cluster Volume
          </h3>
          <div class="text-3xl font-display font-bold text-cyber-accent">
            ${{ (analysis.cluster.total_volume / 1000).toFixed(1) }}K
          </div>
          <div class="text-xs text-cyber-muted font-mono mt-1">Total value moved through cluster</div>
        </GlassCard>
      </div>

      <div v-else class="text-center py-6">
        <ShieldCheck class="w-8 h-8 mx-auto text-cyber-muted/30 mb-2" />
        <p class="text-xs text-cyber-muted font-mono">No cluster data — wallet appears isolated</p>
      </div>

      <FundingTree :address="address" />

      <GlassCard accent="electric">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
          <Brain class="w-4 h-4 text-cyber-electric" />
          AI Wallet Summary
        </h3>
        <div v-if="summaryLoading" class="flex items-center gap-2 text-xs text-cyber-muted font-mono">
          <Activity class="w-4 h-4 animate-spin" />
          Generating summary...
        </div>
        <div v-else-if="summary" class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-cyber-electric/10 flex items-center justify-center flex-shrink-0">
            <Brain class="w-4 h-4 text-cyber-electric" />
          </div>
          <div>
            <p class="text-sm text-cyber-text-secondary leading-relaxed">{{ summary.summary }}</p>
            <p class="text-[10px] text-cyber-muted font-mono mt-1">Powered by {{ summary.provider === 'altllm' ? 'AltLLM' : 'deterministic fallback' }}</p>
          </div>
        </div>
        <div v-else class="text-xs text-cyber-muted font-mono">No summary available</div>
      </GlassCard>

      <GlassCard accent="green">
        <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
          <Activity class="w-4 h-4 text-cyber-accent" />
          Recent Transactions
        </h3>
        <div v-if="txsLoading" class="flex items-center gap-2 py-4 text-xs text-cyber-muted font-mono">
          <Activity class="w-4 h-4 animate-spin" />
          Loading transactions...
        </div>
        <div v-else-if="txs.length === 0" class="text-xs text-cyber-muted font-mono py-4 text-center">
          No recent transactions found
        </div>
        <div v-else class="space-y-1 max-h-64 overflow-y-auto pr-1 custom-scrollbar">
          <div v-for="tx in txs" :key="tx.hash"
            class="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-white/[0.02] text-xs font-mono transition-colors">
            <span class="text-cyber-muted w-10 flex-shrink-0">{{ formatTime(tx.timestamp) }}</span>
            <a :href="`https://mantlescan.xyz/address/${tx.from}`" target="_blank"
              class="text-cyber-text hover:text-cyber-accent transition-colors flex-shrink-0">
              {{ addrShort(tx.from) }}
            </a>
            <span class="text-cyber-muted/30 mx-1">→</span>
            <a v-if="tx.to" :href="`https://mantlescan.xyz/address/${tx.to}`" target="_blank"
              class="text-cyber-text hover:text-cyber-accent transition-colors flex-shrink-0">
              {{ addrShort(tx.to) }}
            </a>
            <span v-else class="text-cyber-muted flex-shrink-0">deploy</span>
            <span v-if="tx.value_eth > 0" class="ml-auto text-cyber-accent font-medium flex-shrink-0">
              {{ formatEth(tx.value_eth) }} MNT
            </span>
            <a :href="txUrl(tx.hash)" target="_blank" class="text-cyber-muted/40 hover:text-cyber-accent transition-colors flex-shrink-0">
              <ExternalLink class="w-3 h-3" />
            </a>
          </div>
        </div>
      </GlassCard>
    </template>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
</style>
