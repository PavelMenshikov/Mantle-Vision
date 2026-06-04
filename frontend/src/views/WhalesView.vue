<script setup>
import { ref, computed, onMounted } from 'vue'
import WhaleCard from '@/components/WhaleCard.vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'

const whales = ref([])
const loading = ref(false)
const showAddForm = ref(false)
const newAddress = ref('')
const newLabel = ref('')

const totalTracked = computed(() => whales.value.length)
const totalVolume = computed(() => {
  if (!whales.value.length) return '$0'
  const sum = whales.value.reduce((acc, w) => acc + (w.totalValue || 0), 0)
  if (sum >= 1e6) return '$' + (sum / 1e6).toFixed(2) + 'M'
  return '$' + (sum / 1e3).toFixed(1) + 'K'
})
const highRiskCount = computed(() => whales.value.filter(w => (w.riskScore || 0) >= 0.7).length)

async function fetchWhales() {
  loading.value = true
  try {
    const res = await fetch('/api/whales')
    whales.value = await res.json()
  } catch {
    whales.value = []
  } finally {
    loading.value = false
  }
}

async function addWhale() {
  if (!newAddress.value) return
  try {
    const res = await fetch(`/api/whales?address=${encodeURIComponent(newAddress.value)}&label=${encodeURIComponent(newLabel.value)}`, { method: 'POST' })
    if (res.ok) {
      const w = await res.json()
      whales.value.push(w)
    }
  } catch {}
  newAddress.value = ''
  newLabel.value = ''
  showAddForm.value = false
}

async function removeWhale(address) {
  try {
    await fetch(`/api/whales/${address}`, { method: 'DELETE' })
    whales.value = whales.value.filter(w => w.address !== address)
  } catch {}
}

onMounted(fetchWhales)
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h2 class="text-2xl font-display font-bold text-gradient">Whale Tracker</h2>
        <p class="text-sm text-cyber-muted font-mono mt-1">Monitor large wallet activity on Mantle</p>
      </div>
      <div class="flex gap-2">
        <NeonButton variant="ghost" size="sm" @click="fetchWhales">⟳ Refresh</NeonButton>
        <NeonButton variant="primary" size="sm" @click="showAddForm = !showAddForm">
          {{ showAddForm ? '✕ Cancel' : '+ Add Whale' }}
        </NeonButton>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <GlassCard accent="green">
        <div class="text-xs text-cyber-muted font-mono mb-1">Tracked Whales</div>
        <div class="text-2xl font-display font-bold text-cyber-text">{{ totalTracked }}</div>
      </GlassCard>
      <GlassCard accent="blue">
        <div class="text-xs text-cyber-muted font-mono mb-1">Total Volume</div>
        <div class="text-2xl font-display font-bold text-cyber-text">{{ totalVolume }}</div>
      </GlassCard>
      <GlassCard accent="red">
        <div class="text-xs text-cyber-muted font-mono mb-1">High Risk</div>
        <div class="text-2xl font-display font-bold text-cyber-text">{{ highRiskCount }}</div>
      </GlassCard>
    </div>

    <GlassCard v-if="showAddForm" accent="blue">
      <h3 class="text-sm font-display font-semibold text-cyber-text mb-3">Add Whale Address</h3>
      <div class="flex flex-wrap gap-3">
        <input
          v-model="newAddress"
          placeholder="0x..."
          class="flex-1 min-w-[200px] bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-cyber-text-secondary focus:outline-none focus:border-cyber-accent/50 transition-colors"
        />
        <input
          v-model="newLabel"
          placeholder="Label (optional)"
          class="flex-1 min-w-[120px] bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-cyber-text-secondary focus:outline-none focus:border-cyber-accent/50 transition-colors"
        />
        <NeonButton variant="primary" size="sm" @click="addWhale">Track Whale</NeonButton>
      </div>
    </GlassCard>

    <div v-if="loading" class="text-center py-8 text-cyber-muted text-sm font-mono">
      Loading whales...
    </div>

    <div v-else-if="!whales.length" class="text-center py-12">
      <div class="text-4xl mb-3 opacity-30">🐋</div>
      <p class="text-cyber-muted text-sm font-mono mb-4">No whales tracked yet. Add an address to start monitoring.</p>
      <NeonButton variant="primary" size="sm" @click="showAddForm = true">+ Add First Whale</NeonButton>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="whale in whales" :key="whale.address" class="relative">
        <WhaleCard :whale="whale" />
        <button
          @click="removeWhale(whale.address)"
          class="absolute top-2 right-2 text-[10px] text-cyber-danger/50 hover:text-cyber-danger font-mono transition-colors"
          title="Remove"
        >✕</button>
      </div>
    </div>
  </div>
</template>
