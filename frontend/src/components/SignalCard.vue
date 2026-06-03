<script setup>
import { computed } from 'vue'
import GlassCard from './GlassCard.vue'

const props = defineProps({
  signal: { type: Object, required: true }
})

const isBullish = computed(() => props.signal.direction === 'bullish')
const emoji = computed(() => isBullish.value ? '🚀' : '📉')
const accentColor = computed(() => isBullish.value ? 'green' : 'red')

const typeLabels = {
  price_breakout: 'Price Breakout',
  whale_move: 'Whale Move',
  liquidation: 'Liquidation',
  sentiment: 'Sentiment'
}

const typeIcon = {
  price_breakout: '📊',
  whale_move: '🐋',
  liquidation: '💥',
  sentiment: '🧠'
}

const timeAgo = computed(() => {
  const diff = Date.now() - new Date(props.signal.timestamp).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
})

const confidenceColor = computed(() => {
  if (props.signal.confidence >= 85) return 'text-cyber-accent'
  if (props.signal.confidence >= 70) return 'text-cyber-electric'
  if (props.signal.confidence >= 55) return 'text-cyber-warning'
  return 'text-cyber-muted'
})
</script>

<template>
  <GlassCard :accent="accentColor" class="animate-fade-in">
    <div class="flex items-start gap-4">
      <div :class="[
        'w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0',
        isBullish ? 'gradient-green' : 'gradient-red'
      ]">
        {{ emoji }}
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-mono font-bold uppercase">{{ signal.asset }}</span>
          <span :class="[
            'px-2 py-0.5 rounded-md text-[10px] font-mono font-medium',
            isBullish ? 'badge-green' : 'badge-red'
          ]">
            {{ isBullish ? 'BULLISH' : 'BEARISH' }}
          </span>
          <span class="px-2 py-0.5 rounded-md text-[10px] font-mono badge-blue">
            {{ typeIcon[signal.type] }} {{ typeLabels[signal.type] || signal.type }}
          </span>
        </div>

        <p class="text-sm text-gray-300 leading-relaxed mb-2">
          {{ signal.reasoning }}
        </p>

        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span :class="['text-xs font-mono font-semibold', confidenceColor]">
              {{ signal.confidence }}% confidence
            </span>
            <span class="text-xs text-cyber-muted font-mono">{{ timeAgo }}</span>
          </div>
          <div v-if="signal.confidence >= 80" class="flex items-center gap-1 text-[10px] text-cyber-accent font-mono">
            <span class="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-pulse-glow"></span>
            HIGH CONFIDENCE
          </div>
        </div>
      </div>
    </div>
  </GlassCard>
</template>
