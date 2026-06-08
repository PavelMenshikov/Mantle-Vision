<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import GlassCard from './GlassCard.vue'
import { ExternalLink, Loader, AlertTriangle, Layers } from 'lucide-vue-next'

const props = defineProps({
  address: { type: String, required: true },
})

const router = useRouter()
const tree = ref(null)
const loading = ref(true)
const error = ref('')
let abortCtrl = null

onMounted(() => fetchTree())
onUnmounted(() => { if (abortCtrl) abortCtrl.abort() })

async function fetchTree() {
  if (abortCtrl) abortCtrl.abort()
  abortCtrl = new AbortController()
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/wallet/${props.address}/funding-tree?depth=2`, { signal: abortCtrl.signal })
    if (!res.ok) throw new Error('No funding data')
    tree.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function addrShort(a) {
  if (!a || a.length < 10) return a
  return a.slice(0, 5) + '...' + a.slice(-3)
}

const byLevel = computed(() => {
  if (!tree.value) return []
  const groups = {}
  for (const n of tree.value.nodes) {
    if (!groups[n.level]) groups[n.level] = []
    groups[n.level].push(n)
  }
  return Object.entries(groups).sort((a, b) => Number(a[0]) - Number(b[0]))
})

const explorerUrl = (a) => `https://mantlescan.xyz/address/${a}`
</script>

<template>
  <GlassCard accent="electric">
    <h3 class="text-sm font-display font-semibold text-cyber-text mb-3 flex items-center gap-2">
      <Layers class="w-4 h-4 text-cyber-electric" />
      Funding Tree
    </h3>

    <div v-if="loading" class="flex items-center justify-center py-6">
      <Loader class="w-5 h-5 text-cyber-muted animate-spin" />
    </div>

    <div v-else-if="error" class="flex items-center gap-2 py-4 text-xs text-cyber-muted font-mono">
      <AlertTriangle class="w-4 h-4 text-cyber-warning" />
      No funding links available
    </div>

    <div v-else-if="tree" class="space-y-4">
      <div class="flex items-center gap-2 text-[10px] text-cyber-muted font-mono mb-2">
        <span>{{ tree.total_nodes }} wallets</span>
        <span class="w-1 h-1 rounded-full bg-white/10"></span>
        <span>{{ tree.total_edges }} transactions</span>
      </div>

      <div v-for="[level, nodes] in byLevel" :key="level" class="relative">
        <div v-if="Number(level) > 0" class="flex justify-center mb-2">
          <svg class="w-4 h-4 text-cyber-muted/20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
        </div>
        <div class="flex flex-wrap gap-2 justify-center">
          <div
            v-for="node in nodes"
            :key="node.address"
            @click="router.push('/wallet/' + node.address)"
            :class="[
              'px-3 py-1.5 rounded-lg text-xs font-mono cursor-pointer transition-all border',
              node.is_target
                ? 'bg-cyber-accent/15 border-cyber-accent/40 text-cyber-accent shadow-neon'
                : 'bg-white/[0.03] border-white/5 text-cyber-text hover:bg-white/[0.06] hover:border-cyber-electric/30'
            ]"
          >
            <span class="flex items-center gap-1.5">
              {{ addrShort(node.address) }}
              <ExternalLink class="w-3 h-3 text-cyber-muted/40" />
            </span>
          </div>
        </div>
      </div>

      <div class="mt-3 pt-3 border-t border-white/5">
        <div class="text-[10px] text-cyber-muted font-mono">Edge transactions</div>
        <div class="mt-2 space-y-1 max-h-32 overflow-y-auto custom-scrollbar">
          <div v-for="(edge, i) in tree.edges.slice(0, 20)" :key="i"
            class="flex items-center gap-1.5 text-[10px] font-mono text-cyber-muted">
            <span class="text-cyber-text">{{ addrShort(edge.from) }}</span>
            <span class="text-cyber-muted/30">→</span>
            <span class="text-cyber-text">{{ addrShort(edge.to) }}</span>
            <span v-if="edge.value" class="text-cyber-accent ml-auto">{{ edge.value.toFixed(3) }} MNT</span>
          </div>
        </div>
      </div>
    </div>
  </GlassCard>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 2px; }
</style>
