<script setup>
import { h } from 'vue'
import GlassCard from './GlassCard.vue'
import { Zap, Users, DollarSign, Globe } from 'lucide-vue-next'

const props = defineProps({
  stats: { type: Array, required: true }
})

const iconMap = {
  signals: Zap,
  whales: Users,
  pnl: DollarSign,
  network: Globe,
}
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <GlassCard
      v-for="stat in stats"
      :key="stat.label"
      :accent="stat.accent || 'green'"
      class="animate-fade-in"
    >
      <div class="flex items-center gap-3">
        <div :class="[
          'w-10 h-10 rounded-xl flex items-center justify-center text-lg',
          stat.accent === 'green' ? 'gradient-green' : '',
          stat.accent === 'blue' ? 'gradient-blue' : '',
          stat.accent === 'red' ? 'gradient-red' : '',
          stat.accent === 'amber' ? 'gradient-amber' : ''
        ]">
          <component :is="iconMap[stat.icon] || Globe" class="w-5 h-5" />
        </div>
        <div>
          <div class="text-lg font-display font-bold">{{ stat.value }}</div>
          <div class="text-xs text-cyber-muted font-mono">{{ stat.label }}</div>
        </div>
      </div>
      <div v-if="stat.change !== undefined" :class="[
        'text-[10px] font-mono mt-2',
        stat.change >= 0 ? 'text-cyber-accent' : 'text-cyber-danger'
      ]">
        {{ stat.change >= 0 ? '+' : '' }}{{ stat.change }}% vs yesterday
      </div>
    </GlassCard>
  </div>
</template>
