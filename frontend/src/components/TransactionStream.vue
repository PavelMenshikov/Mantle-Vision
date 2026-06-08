<script setup>
import { shallowRef, computed, ref, onMounted, onUnmounted } from 'vue'
import { ExternalLink, AlertTriangle, Check, Loader } from 'lucide-vue-next'

const props = defineProps({
  height: { type: Number, default: 240 },
  limit: { type: Number, default: 30 },
})

const txs = shallowRef([])
const loading = ref(true)
const flaggedOnly = ref(false)
const flaggedCount = ref(0)
let abortCtrl = null
let pollTimer = null

const filteredTxs = computed(() => {
  const list = txs.value
  if (!flaggedOnly.value) return list
  return list.filter(tx => tx.flagged || tx.anomaly_score > 0.5)
})

async function fetchTxs() {
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()
  try {
    const res = await fetch(`/api/txs/recent?limit=${props.limit}`, { signal: abortCtrl.signal })
    if (res.ok) {
      const data = await res.json()
      txs.value = data
      flaggedCount.value = data.filter(t => t.flagged || t.anomaly_score > 0.5).length
    }
  } catch {}
  loading.value = false
}

onMounted(async () => {
  await fetchTxs()
  pollTimer = setInterval(fetchTxs, 15000)
})

onUnmounted(() => {
  if (abortCtrl) abortCtrl.abort()
  if (pollTimer) clearInterval(pollTimer)
})

function addrShort(addr) {
  if (!addr || addr.length < 10) return addr || '—'
  return addr.slice(0, 5) + '...' + addr.slice(-3)
}

function txUrl(hash) {
  return `https://mantlescan.xyz/tx/${hash}`
}

function addrUrl(addr) {
  return `https://mantlescan.xyz/address/${addr}`
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
  if (val === null || val === undefined) return ''
  if (val === 0) return '0.000'
  if (val >= 1000) return val.toFixed(1)
  if (val >= 1) return val.toFixed(3)
  if (val >= 0.001) return val.toFixed(5)
  return '<0.001'
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-3">
        <button
          @click="flaggedOnly = false"
          :class="['px-3 py-1 text-xs font-mono rounded-lg transition-all', !flaggedOnly ? 'bg-cyber-accent/20 text-cyber-accent' : 'text-cyber-muted hover:text-cyber-text']"
        >
          All
        </button>
        <button
          @click="flaggedOnly = true"
          :class="['px-3 py-1 text-xs font-mono rounded-lg transition-all flex items-center gap-1', flaggedOnly ? 'bg-cyber-danger/20 text-cyber-danger' : 'text-cyber-muted hover:text-cyber-text']"
        >
          <AlertTriangle class="w-3 h-3" />
          Flagged
          <span v-if="flaggedCount" class="text-[10px] opacity-70">({{ flaggedCount }})</span>
        </button>
      </div>
      <div class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-pulse" />
        <span class="text-[10px] text-cyber-muted font-mono">Live</span>
      </div>
    </div>

    <div class="relative" :style="{ height: height + 'px' }">
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
        <Loader class="w-5 h-5 text-cyber-muted animate-spin" />
      </div>

      <div v-else-if="!filteredTxs.length" class="absolute inset-0 flex items-center justify-center">
        <span class="text-xs text-cyber-muted font-mono">Waiting for transactions...</span>
      </div>

      <div v-else class="h-full overflow-y-auto space-y-1 pr-1 custom-scrollbar">
        <div
          v-for="tx in filteredTxs"
          :key="tx.hash"
          v-once
          :class="[
            'flex items-center gap-2 py-1.5 px-2 rounded-lg transition-colors text-xs font-mono',
            tx.flagged || tx.anomaly_score > 0.5
              ? 'bg-cyber-danger/5 border border-cyber-danger/10'
              : 'hover:bg-white/[0.02]'
          ]"
        >
          <div v-if="tx.flagged || tx.anomaly_score > 0.5" class="flex-shrink-0">
            <AlertTriangle class="w-3 h-3 text-cyber-danger" />
          </div>
          <div v-else class="flex-shrink-0">
            <Check class="w-3 h-3 text-cyber-muted/30" />
          </div>

          <span class="text-cyber-muted w-10 flex-shrink-0">{{ formatTime(tx.timestamp) }}</span>

          <a :href="addrUrl(tx.from_)" target="_blank" class="text-cyber-text hover:text-cyber-accent transition-colors flex-shrink-0">
            {{ addrShort(tx.from_) }}
          </a>

          <span class="text-cyber-muted/30 mx-1">→</span>

          <a v-if="tx.to" :href="addrUrl(tx.to)" target="_blank" class="text-cyber-text hover:text-cyber-accent transition-colors flex-shrink-0">
            {{ addrShort(tx.to) }}
          </a>
          <span v-else class="text-cyber-muted flex-shrink-0">deploy</span>

          <span class="ml-auto text-cyber-accent font-medium flex-shrink-0">
            {{ formatEth(tx.value_eth) }} MNT
          </span>

          <a :href="txUrl(tx.hash)" target="_blank" class="text-cyber-muted/40 hover:text-cyber-accent transition-colors flex-shrink-0">
            <ExternalLink class="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.08);
  border-radius: 2px;
}
</style>
