<script setup>
import { ref } from 'vue'
import GlassCard from './GlassCard.vue'
import { Gem, Hexagon, DollarSign, Landmark } from 'lucide-vue-next'

const tokenIcons = { MNT: Gem, mETH: Hexagon, USDC: DollarSign, USDY: Landmark }

const tokens = ref([
  { symbol: 'MNT', price: 0.89, change24h: 4.27 },
  { symbol: 'mETH', price: 2912.45, change24h: -1.34 },
  { symbol: 'USDC', price: 1.0002, change24h: 0.01 },
  { symbol: 'USDY', price: 1.084, change24h: 0.12 },
])

function formatPrice(val) {
  if (val >= 1000) return '$' + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (val >= 1) return '$' + val.toFixed(4)
  return '$' + val.toFixed(6)
}
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <GlassCard v-for="token in tokens" :key="token.symbol" :accent="token.change24h >= 0 ? 'green' : 'red'" class="!p-3 animate-fade-in">
        <div class="flex items-center gap-2">
          <component :is="tokenIcons[token.symbol] || DollarSign" class="w-5 h-5 text-cyber-muted flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-semibold text-cyber-text">{{ token.symbol }}</span>
            <span :class="[
              'text-[10px] font-mono font-medium px-1.5 py-0.5 rounded',
              token.change24h >= 0 ? 'text-cyber-accent bg-cyber-accent/10' : 'text-cyber-danger bg-cyber-danger/10'
            ]">
              {{ token.change24h >= 0 ? '+' : '' }}{{ token.change24h }}%
            </span>
          </div>
          <div class="text-sm font-mono font-semibold text-gray-200 mt-0.5">
            {{ formatPrice(token.price) }}
          </div>
        </div>
      </div>
    </GlassCard>
  </div>
</template>

