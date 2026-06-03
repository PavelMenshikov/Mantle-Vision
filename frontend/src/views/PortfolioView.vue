<script setup>
import { ref, computed, onMounted } from 'vue'
import GlassCard from '@/components/GlassCard.vue'
import NeonButton from '@/components/NeonButton.vue'
import PortfolioChart from '@/components/PortfolioChart.vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { useWalletStore } from '@/stores/wallet'

const portfolio = usePortfolioStore()
const wallet = useWalletStore()

const tradeType = ref('buy')
const tradeAsset = ref('MNT')
const tradeAmount = ref('')
const tradePrice = ref('')

const assets = ['MNT', 'mETH', 'USDC', 'USDY']

const currentPrices = {
  MNT: 0.89,
  mETH: 2912,
  USDC: 1.00,
  USDY: 1.084
}

const totalValueFormatted = computed(() => {
  return '$' + portfolio.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const pnlColor = computed(() => portfolio.totalPnl >= 0 ? 'text-cyber-accent' : 'text-cyber-danger')
const pnlSign = computed(() => portfolio.totalPnl >= 0 ? '+' : '')

const recentTrades = computed(() =>
  portfolio.history.slice(-10).reverse()
)

onMounted(() => {
  portfolio.fetchPortfolio()
  portfolio.fetchHistory()
})

function handleTrade() {
  const amount = parseFloat(tradeAmount.value)
  const price = parseFloat(tradePrice.value) || currentPrices[tradeAsset.value]
  if (!amount || amount <= 0) return

  const result = portfolio.executeTrade({
    type: tradeType.value,
    asset: tradeAsset.value,
    amount,
    price
  })

  if (result.success) {
    tradeAmount.value = ''
    tradePrice.value = ''
  }
}

function fillPrice() {
  tradePrice.value = currentPrices[tradeAsset.value]?.toString() || ''
}
</script>

<template>
  <div class="space-y-6 animate-fade-in">
    <div>
      <h2 class="text-2xl font-display font-bold text-gradient">Portfolio</h2>
      <p class="text-sm text-cyber-muted font-mono mt-1">
        {{ wallet.isDemo ? 'Paper trading portfolio' : 'Real portfolio' }}
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <GlassCard accent="green" class="lg:col-span-2">
        <div class="text-xs text-cyber-muted font-mono mb-1">Total Value</div>
        <div class="text-3xl font-display font-bold text-white">{{ totalValueFormatted }}</div>
        <div :class="['text-sm font-mono mt-1', pnlColor]">
          {{ pnlSign }}{{ portfolio.totalPnl.toFixed(2) }} ({{ pnlSign }}{{ portfolio.pnlPercent }}%)
        </div>
      </GlassCard>

      <GlassCard accent="blue">
        <div class="text-xs text-cyber-muted font-mono mb-1">Available Balance</div>
        <div class="text-2xl font-display font-bold text-white">
          ${{ portfolio.demoBalance.toFixed(2) }}
        </div>
        <div class="text-xs text-cyber-muted font-mono mt-1">{{ wallet.isDemo ? 'Demo' : 'Real' }} funds</div>
      </GlassCard>

      <GlassCard accent="amber">
        <div class="text-xs text-cyber-muted font-mono mb-1">Open Positions</div>
        <div class="text-2xl font-display font-bold text-white">{{ portfolio.positionCount }}</div>
        <div class="text-xs text-cyber-muted font-mono mt-1">Active trades</div>
      </GlassCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-4">
        <GlassCard accent="green">
          <PortfolioChart :data="portfolio.history" :height="300" />
        </GlassCard>

        <GlassCard>
          <h3 class="text-sm font-display font-semibold text-white mb-3">Positions</h3>
          <div v-if="portfolio.positions.length" class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-xs text-cyber-muted font-mono border-b border-white/5">
                  <th class="text-left pb-2 font-medium">Asset</th>
                  <th class="text-right pb-2 font-medium">Amount</th>
                  <th class="text-right pb-2 font-medium">Entry</th>
                  <th class="text-right pb-2 font-medium">Current</th>
                  <th class="text-right pb-2 font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in portfolio.positions" :key="pos.id" class="border-b border-white/5">
                  <td class="py-3 font-mono font-semibold">{{ pos.asset }}</td>
                  <td class="py-3 text-right font-mono">{{ pos.amount }}</td>
                  <td class="py-3 text-right font-mono">${{ pos.entryPrice.toFixed(4) }}</td>
                  <td class="py-3 text-right font-mono">${{ pos.currentPrice.toFixed(4) }}</td>
                  <td :class="['py-3 text-right font-mono', pos.pnl >= 0 ? 'text-cyber-accent' : 'text-cyber-danger']">
                    {{ pos.pnl >= 0 ? '+' : '' }}{{ pos.pnl.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center py-6 text-cyber-muted text-sm font-mono">
            No open positions
          </div>
        </GlassCard>

        <GlassCard v-if="recentTrades.length">
          <h3 class="text-sm font-display font-semibold text-white mb-3">Trade History</h3>
          <div class="space-y-2">
            <div v-for="(trade, i) in recentTrades" :key="i" class="flex items-center justify-between text-xs font-mono py-1.5 border-b border-white/5 last:border-0">
              <span class="text-cyber-muted">{{ new Date(trade.date).toLocaleDateString() }}</span>
              <span class="text-white">${{ trade.value.toFixed(2) }}</span>
            </div>
          </div>
        </GlassCard>
      </div>

      <div>
        <GlassCard accent="green">
          <h3 class="text-sm font-display font-semibold text-white mb-4">Trade</h3>

          <div class="flex glass !p-1 rounded-xl mb-4 gap-1">
            <button
              v-for="t in ['buy', 'sell']"
              :key="t"
              @click="tradeType = t"
              :class="[
                'flex-1 px-3 py-1.5 text-xs font-mono font-medium rounded-lg transition-all duration-200 uppercase',
                tradeType === t
                  ? t === 'buy' ? 'bg-cyber-accent/20 text-cyber-accent' : 'bg-cyber-danger/20 text-cyber-danger'
                  : 'text-cyber-muted hover:text-white'
              ]"
            >
              {{ t }}
            </button>
          </div>

          <div class="space-y-3">
            <div>
              <label class="text-xs text-cyber-muted font-mono block mb-1">Asset</label>
              <select
                v-model="tradeAsset"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
              >
                <option v-for="a in assets" :key="a" :value="a">{{ a }}</option>
              </select>
            </div>

            <div>
              <label class="text-xs text-cyber-muted font-mono block mb-1">Price</label>
              <div class="flex gap-2">
                <input
                  v-model="tradePrice"
                  type="number"
                  step="0.0001"
                  placeholder="0.00"
                  class="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
                />
                <button @click="fillPrice" class="px-2 py-1 rounded-lg bg-white/5 text-[10px] text-cyber-muted hover:text-white font-mono">
                  Market
                </button>
              </div>
            </div>

            <div>
              <label class="text-xs text-cyber-muted font-mono block mb-1">Amount</label>
              <input
                v-model="tradeAmount"
                type="number"
                step="0.01"
                placeholder="0.00"
                class="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-gray-300 focus:outline-none focus:border-cyber-accent/50 transition-colors"
              />
            </div>

            <div v-if="tradeAmount && tradePrice" class="glass !p-3 rounded-xl text-xs font-mono">
              <div class="flex justify-between text-cyber-muted">
                <span>Total</span>
                <span class="text-white">${{ (parseFloat(tradeAmount || 0) * parseFloat(tradePrice || 0)).toFixed(2) }}</span>
              </div>
            </div>

            <NeonButton
              :variant="tradeType === 'buy' ? 'primary' : 'danger'"
              class="w-full"
              @click="handleTrade"
            >
              {{ tradeType === 'buy' ? 'Buy' : 'Sell' }} {{ tradeAsset }}
            </NeonButton>
          </div>
        </GlassCard>
      </div>
    </div>
  </div>
</template>
