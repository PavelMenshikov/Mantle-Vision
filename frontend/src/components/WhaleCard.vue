<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import GlassCard from './GlassCard.vue'
import { Users, ExternalLink, Search } from 'lucide-vue-next'

const props = defineProps({
  whale: { type: Object, required: true }
})
const router = useRouter()

const shortAddress = computed(() => {
  const a = props.whale.address || ''
  if (a.length < 10) return a
  return a.slice(0, 6) + '...' + a.slice(-4)
})

const riskScore = computed(() => {
  const r = props.whale.risk ?? props.whale.riskScore ?? 0.5
  return r > 1 ? r : r * 10
})
const riskColor = computed(() => {
  const r = riskScore.value
  if (r >= 7) return 'text-cyber-danger'
  if (r >= 4) return 'text-cyber-warning'
  return 'text-cyber-accent'
})

const riskLabel = computed(() => {
  const r = riskScore.value
  if (r >= 7) return 'High Risk'
  if (r >= 4) return 'Medium Risk'
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
        <div class="w-10 h-10 rounded-xl gradient-blue flex items-center justify-center">
          <Users class="w-5 h-5 text-cyber-electric" />
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

      <div class="text-right flex flex-col items-end gap-2">
        <div :class="['text-xs font-mono font-semibold', riskColor]">
          {{ riskLabel }}
        </div>
        <button @click="router.push('/wallet/' + props.whale.address)"
          class="flex items-center gap-1 text-[10px] font-mono text-cyber-electric hover:text-cyber-accent transition-colors">
          <Search class="w-3 h-3" />
          Analyze
        </button>
        <div class="flex gap-0.5 justify-end">
          <div
            v-for="i in 5"
            :key="i"
            :class="[
              'w-3 h-1 rounded-full transition-all',
              i <= Math.ceil(riskScore.value / 2)
                ? riskScore.value >= 7 ? 'bg-cyber-danger' : riskScore.value >= 4 ? 'bg-cyber-warning' : 'bg-cyber-accent'
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
