<script setup>
import { computed } from 'vue'
import GlassCard from './GlassCard.vue'
import { TrendingUp, TrendingDown, Minus, BarChart3, Users, AlertTriangle, Brain, Settings, Bot, ExternalLink } from 'lucide-vue-next'

const props = defineProps({
  signal: { type: Object, required: true }
})

const isBullish = computed(() => {
  const d = props.signal.direction
  return d === 'bullish' || d === 'buy'
})
const isBearish = computed(() => {
  const d = props.signal.direction
  return d === 'bearish' || d === 'sell'
})
const directionIcon = computed(() => isBullish.value ? TrendingUp : isBearish.value ? TrendingDown : Minus)
const accentColor = computed(() => isBullish.value ? 'green' : isBearish.value ? 'red' : 'amber')

const typeLabels = {
  price_breakout: 'Price Breakout',
  whale_move: 'Whale Move',
  liquidation: 'Liquidation',
  sentiment: 'Sentiment',
  arbiter_decision: 'Strategy',
  combined_signal: 'AI Signal'
}

const typeIconMap = {
  price_breakout: BarChart3,
  whale_move: Users,
  liquidation: AlertTriangle,
  sentiment: Brain,
  arbiter_decision: Settings,
  combined_signal: Bot,
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
  if (props.signal.confidence >= 0.85) return 'text-cyber-accent'
  if (props.signal.confidence >= 0.70) return 'text-cyber-electric'
  if (props.signal.confidence >= 0.55) return 'text-cyber-warning'
  return 'text-cyber-muted'
})

const explorerUrl = 'https://mantlescan.xyz'

const reasoningHtml = computed(() => {
  let text = props.signal.reasoning || ''
  return text.replace(
    /(0x[a-fA-F0-9]{6,})/g,
    (match) => `<a href="${explorerUrl}/address/${match}" target="_blank" class="text-cyber-electric hover:text-cyber-accent underline transition-colors">${match.slice(0, 6)}...${match.slice(-4)}</a>`
  )
})
</script>

<template>
  <GlassCard :accent="accentColor" class="animate-fade-in">
    <div class="flex items-start gap-4">
      <div :class="[
        'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
        isBullish ? 'gradient-green' : 'gradient-red'
      ]">
        <component :is="directionIcon" class="w-5 h-5" :class="isBullish ? 'text-cyber-accent' : isBearish ? 'text-cyber-danger' : 'text-cyber-warning'" />
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-mono font-bold uppercase">{{ signal.asset }}</span>
          <span :class="[
            'px-2 py-0.5 rounded-md text-[10px] font-mono font-medium',
            isBullish ? 'badge-green' : isBearish ? 'badge-red' : 'badge-amber'
          ]">
            {{ isBullish ? 'BULLISH' : isBearish ? 'BEARISH' : 'HOLD' }}
          </span>
          <span class="px-2 py-0.5 rounded-md text-[10px] font-mono badge-blue inline-flex items-center gap-1">
            <component :is="typeIconMap[signal.type] || Bot" class="w-3 h-3" />
            {{ typeLabels[signal.type] || signal.type }}
          </span>
        </div>

        <p class="text-sm text-cyber-text-secondary leading-relaxed mb-2" v-html="reasoningHtml"></p>

        <div class="flex items-center flex-wrap gap-2">
          <div class="flex items-center gap-3">
            <span :class="['text-xs font-mono font-semibold', confidenceColor]">
              {{ (signal.confidence * 100).toFixed(0) }}% confidence
            </span>
            <span class="text-xs text-cyber-muted font-mono">{{ timeAgo }}</span>
          </div>

          <a
            v-if="signal.txHash"
            :href="`${explorerUrl}/tx/${signal.txHash}`"
            target="_blank"
            class="text-[10px] font-mono px-2 py-0.5 rounded-md badge-blue hover:bg-cyber-electric/20 transition-colors"
          >
            <ExternalLink class="w-3 h-3" /> Tx
          </a>

          <div v-if="signal.confidence >= 0.80" class="flex items-center gap-1 text-[10px] text-cyber-accent font-mono ml-auto">
            <span class="w-1.5 h-1.5 rounded-full bg-cyber-accent animate-pulse-glow"></span>
            HIGH CONFIDENCE
          </div>
        </div>
      </div>
    </div>
  </GlassCard>
</template>
