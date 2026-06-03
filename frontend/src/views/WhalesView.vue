<script setup>
import { ref, computed } from 'vue'
import WhaleCard from '@/components/WhaleCard.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'

const whales = ref([
  { address: '0x8f3Bf4c5d6e7a8b9c0d1e2f3a4b5c6d7e8f1b3', label: 'DeFi Whale', totalValue: 2450000, lastActive: new Date(Date.now() - 3600000).toISOString(), risk: 8, txCount: 342 },
  { address: '0x7a1E2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e9f42', label: 'LP Provider', totalValue: 890000, lastActive: new Date(Date.now() - 7200000).toISOString(), risk: 3, txCount: 156 },
  { address: '0x2b4F5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d7a1', label: 'Trader', totalValue: 1250000, lastActive: new Date(Date.now() - 1800000).toISOString(), risk: 6, txCount: 891 },
  { address: '0x9c8D7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0', label: 'NFT Collector', totalValue: 3200000, lastActive: new Date(Date.now() - 86400000).toISOString(), risk: 5, txCount: 45 },
  { address: '0x3d4E5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2', label: 'Bridge Operator', totalValue: 5100000, lastActive: new Date(Date.now() - 43200000).toISOString(), risk: 2, txCount: 1023 },
  { address: '0x6f7A8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5', label: 'MEV Searcher', totalValue: 780000, lastActive: new Date(Date.now() - 600000).toISOString(), risk: 9, txCount: 2341 },
])

const showAddForm = ref(false)
const newAddress = ref('')
const newLabel = ref('')

const totalTracked = computed(() => whales.value.length)
const totalVolume = computed(() => {
  const sum = whales.value.reduce((acc, w) => acc + w.totalValue, 0)
  if (sum >= 1e6) return '$' + (sum / 1e6).toFixed(2) + 'M'
  return '$' + (sum / 1e3).toFixed(1) + 'K'
})
const highRiskCount = computed(() => whales.value.filter(w => w.risk >= 7).length)

function addWhale() {
  if (!newAddress.value) return
  whales.value.push({
    address: newAddress.value,
    label: newLabel.value || 'Unlabeled',
    totalValue: 0,
    lastActive: new Date().toISOString(),
    risk: 5,
    txCount: 0
  })
  newAddress.value = ''
  newLabel.value = ''
  showAddForm.value = false
}

function removeWhale(index) {
  whales.value.splice(index, 1)
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Whale Tracker</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Monitor large wallet activity on Mantle</p>
      </div>
      <NeonButton variant="primary" size="sm" @click="showAddForm = !showAddForm">
        {{ showAddForm ? '✕ Cancel' : '+ Add Whale' }}
      </NeonButton>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <GlassCard accent="green">
        <div class="text-xs text-cyber-muted font-mono mb-1">Tracked Whales</div>
        <div class="text-2xl font-display font-bold text-white">{{ totalTracked }}</div>
      </GlassCard>
      <GlassCard accent="blue">
        <div class="text-xs text-cyber-muted font-mono mb-1">Total Volume</div>
        <div class="text-2xl font-display font-bold text-white">{{ totalVolume }}</div>
      </GlassCard>
      <GlassCard accent="red">
        <div class="text-xs text-cyber-muted font-mono mb-1">High Risk</div>
        <div class="text-2xl font-display font-bold text-white">{{ highRiskCount }}</div>
      </GlassCard>
    </div>

    <GlassCard v-if="showAddForm" accent="blue">
      <h3 class="text-sm font-display font-semibold text-white mb-3">Add Whale Address</h3>
      <div class="flex flex-wrap gap-3">
        <input
          v-model="newAddress"
          placeholder="0x..."
          class="flex-1 min-w-[200px] bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
        />
        <input
          v-model="newLabel"
          placeholder="Label (optional)"
          class="flex-1 min-w-[120px] bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
        />
        <NeonButton variant="primary" size="sm" @click="addWhale">Track Whale</NeonButton>
      </div>
    </GlassCard>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <WhaleCard
        v-for="(whale, index) in whales"
        :key="whale.address"
        :whale="whale"
      />
    </div>
  </div>
</template>
