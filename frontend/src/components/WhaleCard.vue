<script setup>
import { computed } from 'vue'
import GlassCard from './GlassCard.vue'

const props = defineProps({
  whale: { type: Object, required: true }
})

const shortAddress = computed(() => {
  return props.whale.address.slice(0, 6) + '...' + props.whale.address.slice(-4)
})

const riskColor = computed(() => {
  if (props.whale.risk >= 7) return 'text-cyber-danger'
  if (props.whale.risk >= 4) return 'text-cyber-warning'
  return 'text-cyber-accent'
})

const riskLabel = computed(() => {
  if (props.whale.risk >= 7) return 'High Risk'
  if (props.whale.risk >= 4) return 'Medium Risk'
  return 'Low Risk'
})

const accentMap = {
  High: 'red',
  Medium: 'amber',
  Low: 'green'
}

const timeAgo = computed(() => {
  if (!props.whale.lastActive) return 'Unknown'
  const diff = Date.now() - new Date(props.whale.lastActive).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
})

const formattedValue = computed(() => {
  const num = props.whale.totalValue || 0
  if (num >= 1e6) return '$' + (num / 1e6).toFixed(2) + 'M'
  if (num >= 1e3) return '$' + (num / 1e3).toFixed(1) + 'K'
  return '$' + num.toFixed(2)
})
</script>

<template>
  <GlassCard :accent="accentMap[riskLabel.split(' ')[0]]" class="animate-fade-in">
    <div class="flex items-start justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl gradient-blue flex items-center justify-center text-lg">
          🐋
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm font-medium">{{ shortAddress }}</span>
            <span v-if="whale.label" class="text-[10px] px-2 py-0.5 rounded-md badge-blue font-mono">
              {{ whale.label }}
            </span>
          </div>
          <span class="text-xs text-cyber-muted font-mono">{{ formattedValue }}</span>
        </div>
      </div>

      <div class="text-right">
        <div :class="['text-xs font-mono font-semibold', riskColor]">
          {{ riskLabel }}
        </div>
        <div class="flex gap-0.5 mt-1 justify-end">
          <div
            v-for="i in 5"
            :key="i"
            :class="[
              'w-3 h-1 rounded-full transition-all',
              i <= Math.ceil(props.whale.risk / 2)
                ? props.whale.risk >= 7 ? 'bg-cyber-danger' : props.whale.risk >= 4 ? 'bg-cyber-warning' : 'bg-cyber-accent'
                : 'bg-white/5'
            ]"
          ></div>
        </div>
      </div>
    </div>

    <div v-if="whale.lastActive" class="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-cyber-muted">
      <span class="font-mono">Last active: {{ timeAgo }}</span>
      <span class="font-mono">{{ whale.txCount || 0 }} txns</span>
    </div>
  </GlassCard>
</template>
