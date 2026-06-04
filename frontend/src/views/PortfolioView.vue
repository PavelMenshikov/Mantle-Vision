<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import TransactionStream from '@/components/TransactionStream.vue'
import { RefreshCw, Globe, Cpu, Activity, AlertTriangle, ExternalLink } from 'lucide-vue-next'

const txs = ref([])
const loading = ref(true)
const flaggedCount = ref(0)
const flaggedOnly = ref(false)
let abortCtrl = null
let pollTimer = null

async function fetchTxs() {
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()
  try {
    const res = await fetch('/api/txs/recent?limit=50', { signal: abortCtrl.signal })
    if (res.ok) {
      const data = await res.json()
      txs.value = data
      flaggedCount.value = data.filter(t => t.flagged || t.anomaly_score > 0.5).length
    }
  } catch {}
  loading.value = false
}

const displayTxs = computed(() => {
  if (!flaggedOnly.value) return txs.value
  return txs.value.filter(t => t.flagged || t.anomaly_score > 0.5)
})

onMounted(async () => {
  await fetchTxs()
  pollTimer = setInterval(fetchTxs, 20000)
})

onUnmounted(() => {
  if (abortCtrl) abortCtrl.abort()
  if (pollTimer) clearInterval(pollTimer)
})

function addrShort(addr) {
  if (!addr || addr.length < 10) return addr || '—'
  return addr.slice(0, 6) + '...' + addr.slice(-4)
}

function txUrl(hash) {
  return `https://mantlescan.info/tx/${hash}`
}

function addrUrl(addr) {
  return `https://mantlescan.info/address/${addr}`
}

function formatTime(ts) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString()
}

function formatEth(val) {
  if (val >= 1000) return val.toFixed(1)
  if (val >= 1) return val.toFixed(3)
  if (val >= 0.001) return val.toFixed(5)
  return '<0.001'
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Transaction Stream</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Real-time Mantle blockchain activity with AI anomaly detection</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex glass !p-1 rounded-xl gap-1">
          <button
            @click="flaggedOnly = false"
            :class="['px-3 py-1.5 text-xs font-mono rounded-lg transition-all', !flaggedOnly ? 'bg-cyber-accent/20 text-cyber-accent' : 'text-cyber-muted hover:text-cyber-text']"
          >
            All
          </button>
          <button
            @click="flaggedOnly = true"
            :class="['px-3 py-1.5 text-xs font-mono rounded-lg transition-all flex items-center gap-1', flaggedOnly ? 'bg-cyber-danger/20 text-cyber-danger' : 'text-cyber-muted hover:text-cyber-text']"
          >
            <AlertTriangle class="w-3 h-3" />
            Flagged
            <span v-if="flaggedCount" class="text-[10px]">({{ flaggedCount }})</span>
          </button>
        </div>
        <NeonButton variant="secondary" size="sm" @click="fetchTxs">
          <RefreshCw class="w-4 h-4" />
        </NeonButton>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <GlassCard accent="green">
        <div class="flex items-center gap-2 mb-1">
          <Globe class="w-4 h-4 text-cyber-accent" />
          <div class="text-xs text-cyber-muted font-mono">Chain</div>
        </div>
        <div class="text-2xl font-display font-bold text-cyber-text">Mantle</div>
        <div class="text-xs text-cyber-muted font-mono mt-1">Mainnet</div>
      </GlassCard>
      <GlassCard accent="blue">
        <div class="flex items-center gap-2 mb-1">
          <Cpu class="w-4 h-4 text-cyber-electric" />
          <div class="text-xs text-cyber-muted font-mono">Block</div>
        </div>
        <div class="text-2xl font-display font-bold text-cyber-text" v-if="txs.length">#{{ txs[0].block }}</div>
        <div class="text-2xl font-display font-bold text-cyber-text" v-else>—</div>
        <div class="text-xs text-cyber-muted font-mono mt-1">Latest</div>
      </GlassCard>
      <GlassCard accent="amber">
        <div class="flex items-center gap-2 mb-1">
          <Activity class="w-4 h-4 text-cyber-warning" />
          <div class="text-xs text-cyber-muted font-mono">Streaming</div>
        </div>
        <div class="text-2xl font-display font-bold text-cyber-text">{{ txs.length }}</div>
        <div class="text-xs text-cyber-muted font-mono mt-1">Recent transactions</div>
      </GlassCard>
      <GlassCard accent="red">
        <div class="flex items-center gap-2 mb-1">
          <AlertTriangle class="w-4 h-4 text-cyber-danger" />
          <div class="text-xs text-cyber-muted font-mono">Anomalies</div>
        </div>
        <div class="text-2xl font-display font-bold text-cyber-danger">{{ flaggedCount }}</div>
        <div class="text-xs text-cyber-muted font-mono mt-1">AI-flagged</div>
      </GlassCard>
    </div>

    <GlassCard>
      <div class="overflow-x-auto">
        <table class="w-full text-xs font-mono">
          <thead>
            <tr class="text-cyber-muted border-b border-white/5">
              <th class="text-left pb-2 font-medium w-6"></th>
              <th class="text-left pb-2 font-medium">Time</th>
              <th class="text-left pb-2 font-medium">Block</th>
              <th class="text-left pb-2 font-medium">From</th>
              <th class="text-left pb-2 font-medium"></th>
              <th class="text-left pb-2 font-medium">To</th>
              <th class="text-right pb-2 font-medium">Value (MNT)</th>
              <th class="text-right pb-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in displayTxs" :key="tx.hash"
              :class="[
                'border-b border-white/5 transition-colors',
                tx.flagged || tx.anomaly_score > 0.5 ? 'bg-cyber-danger/[0.02]' : 'hover:bg-white/[0.02]'
              ]">
              <td class="py-2">
                <AlertTriangle v-if="tx.flagged || tx.anomaly_score > 0.5" class="w-3 h-3 text-cyber-danger" />
              </td>
              <td class="py-2 text-cyber-muted whitespace-nowrap">{{ formatTime(tx.timestamp) }}</td>
              <td class="py-2 text-cyber-muted font-mono">{{ tx.block }}</td>
              <td class="py-2">
                <a :href="addrUrl(tx.from_)" target="_blank"
                  class="text-cyber-text hover:text-cyber-accent transition-colors">
                  {{ addrShort(tx.from_) }}
                </a>
              </td>
              <td class="py-2 text-cyber-muted/30">→</td>
              <td class="py-2">
                <a v-if="tx.to" :href="addrUrl(tx.to)" target="_blank"
                  class="text-cyber-text hover:text-cyber-accent transition-colors">
                  {{ addrShort(tx.to) }}
                </a>
                <span v-else class="text-cyber-muted">deploy</span>
              </td>
              <td class="py-2 text-right">
                <span v-if="tx.value_eth > 0" class="text-cyber-accent font-semibold">
                  {{ formatEth(tx.value_eth) }}
                </span>
                <span v-else class="text-cyber-muted">—</span>
              </td>
              <td class="py-2 text-right">
                <a :href="txUrl(tx.hash)" target="_blank" class="text-cyber-muted/40 hover:text-cyber-accent transition-colors">
                  <ExternalLink class="w-3 h-3" />
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!displayTxs.length && !loading" class="text-center py-8 text-cyber-muted text-sm font-mono">
        <span v-if="flaggedOnly">No flagged transactions</span>
        <span v-else>Waiting for transactions...</span>
      </div>
    </GlassCard>
  </div>
</template>
