<script setup>
import { ref, computed, onMounted } from 'vue'
import SignalCard from '@/components/SignalCard.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import { useSignalsStore } from '@/stores/signals'

const signals = useSignalsStore()

const filterType = ref('all')
const filterDirection = ref('all')
const filterConfidence = ref(0)

const filteredSignals = computed(() => {
  return signals.signals.filter(s => {
    if (filterType.value !== 'all' && s.type !== filterType.value) return false
    if (filterDirection.value !== 'all' && s.direction !== filterDirection.value) return false
    if (s.confidence < filterConfidence.value) return false
    return true
  })
})

const hasFilters = computed(() =>
  filterType.value !== 'all' || filterDirection.value !== 'all' || filterConfidence.value > 0
)

function clearFilters() {
  filterType.value = 'all'
  filterDirection.value = 'all'
  filterConfidence.value = 0
}

const typeOptions = [
  { value: 'all', label: 'All Types' },
  { value: 'price_breakout', label: '📊 Price Breakout' },
  { value: 'whale_move', label: '🐋 Whale Move' },
  { value: 'liquidation', label: '💥 Liquidation' },
  { value: 'sentiment', label: '🧠 Sentiment' },
]

onMounted(() => {
  if (!signals.signals.length) {
    signals.fetchSignals()
  }
})
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Signals</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">
          AI-generated trading signals from on-chain data
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div class="glass !p-1.5 rounded-xl flex items-center gap-2">
          <span class="text-xs font-mono text-cyber-muted px-2">Total: {{ signals.signalCount }}</span>
          <span class="w-px h-4 bg-white/5"></span>
          <span class="text-xs font-mono text-cyber-accent px-2">🔥 {{ signals.highConfidenceCount }} high confidence</span>
        </div>
        <NeonButton variant="primary" size="sm" @click="signals.generateSignal()">
          + Generate
        </NeonButton>
        <NeonButton variant="secondary" size="sm" @click="signals.fetchSignals()">
          ⟳ Refresh
        </NeonButton>
      </div>
    </div>

    <GlassCard>
      <div class="flex flex-wrap items-center gap-3">
        <select
          v-model="filterType"
          class="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
        >
          <option v-for="opt in typeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>

        <div class="flex glass !p-1 rounded-xl gap-1">
          <button
            v-for="dir in ['all', 'bullish', 'bearish']"
            :key="dir"
            @click="filterDirection = dir"
            :class="[
              'px-3 py-1.5 text-xs font-mono rounded-lg transition-all duration-200',
              filterDirection === dir
                ? dir === 'all' ? 'bg-white/10 text-white' : dir === 'bullish' ? 'bg-cyber-accent/20 text-cyber-accent' : 'bg-cyber-danger/20 text-cyber-danger'
                : 'text-cyber-muted hover:text-white'
            ]"
          >
            {{ dir === 'all' ? 'All' : dir === 'bullish' ? '🚀 Bullish' : '📉 Bearish' }}
          </button>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-xs text-cyber-muted font-mono">Min: {{ filterConfidence }}%</span>
          <input
            type="range"
            v-model.number="filterConfidence"
            min="0"
            max="100"
            step="5"
            class="w-24 accent-cyber-accent"
          />
        </div>

        <button
          v-if="hasFilters"
          @click="clearFilters"
          class="text-xs text-cyber-muted hover:text-white transition-colors font-mono"
        >
          ✕ Clear
        </button>
      </div>
    </GlassCard>

    <div v-if="signals.loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-28 shimmer-loading"></div>
    </div>

    <div v-else-if="filteredSignals.length === 0" class="text-center py-12">
      <span class="text-4xl block mb-3">🔍</span>
      <p class="text-cyber-muted text-sm font-mono">No signals match your filters</p>
      <NeonButton variant="primary" size="sm" class="mt-3" @click="clearFilters">
        Clear Filters
      </NeonButton>
    </div>

    <div v-else class="space-y-3">
      <SignalCard v-for="signal in filteredSignals" :key="signal.id" :signal="signal" />
    </div>
  </div>
</template>
