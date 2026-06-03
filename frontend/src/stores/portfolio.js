import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePortfolioStore = defineStore('portfolio', () => {
  const positions = ref([])
  const history = ref([])
  const pnl = ref(0)
  const loading = ref(false)

  const demoBalance = ref(10000)

  const totalValue = computed(() => {
    const posValue = positions.value.reduce((sum, p) => sum + (p.amount * p.currentPrice), 0)
    return demoBalance.value + posValue
  })

  const totalPnl = computed(() => totalValue.value - 10000)

  const pnlPercent = computed(() => {
    return ((totalPnl.value / 10000) * 100).toFixed(2)
  })

  const positionCount = computed(() => positions.value.length)

  async function fetchPortfolio() {
    loading.value = true
    try {
      const res = await fetch('/api/portfolio')
      if (res.ok) {
        const data = await res.json()
        positions.value = data.positions || []
        history.value = data.history || []
        pnl.value = data.pnl || 0
      }
    } catch {
      loadDemoPositions()
    } finally {
      loading.value = false
    }
  }

  function loadDemoPositions() {
    positions.value = [
      { id: '1', asset: 'MNT', amount: 250, entryPrice: 0.82, currentPrice: 0.89, type: 'long', pnl: 17.50 },
      { id: '2', asset: 'mETH', amount: 1.5, entryPrice: 2850, currentPrice: 2912, type: 'long', pnl: 93.00 },
      { id: '3', asset: 'USDC', amount: 5000, entryPrice: 1.00, currentPrice: 1.00, type: 'stable', pnl: 0 },
    ]
  }

  function loadDemoHistory() {
    const base = Date.now()
    history.value = Array.from({ length: 30 }, (_, i) => {
      const val = 10000 + Math.sin(i * 0.3) * 500 + (i * 20) + Math.random() * 200
      return {
        date: new Date(base - (29 - i) * 86400000).toISOString(),
        value: Math.round(val * 100) / 100
      }
    })
  }

  async function fetchHistory() {
    try {
      const res = await fetch('/api/portfolio/history')
      if (res.ok) {
        const data = await res.json()
        history.value = data.history || data || []
      }
    } catch {
      loadDemoHistory()
    }
  }

  function executeTrade(trade) {
    const { type, asset, amount, price } = trade
    const cost = amount * price

    if (type === 'buy') {
      if (cost > demoBalance.value) return { success: false, error: 'Insufficient balance' }
      demoBalance.value -= cost
      const existing = positions.value.find(p => p.asset === asset)
      if (existing) {
        const totalCost = existing.amount * existing.entryPrice + cost
        existing.amount += amount
        existing.entryPrice = totalCost / existing.amount
        existing.currentPrice = price
      } else {
        positions.value.push({
          id: 'pos_' + Date.now(),
          asset,
          amount,
          entryPrice: price,
          currentPrice: price,
          type: 'long',
          pnl: 0
        })
      }
    } else {
      const pos = positions.value.find(p => p.asset === asset)
      if (!pos || pos.amount < amount) return { success: false, error: 'Insufficient position' }
      const proceeds = amount * price
      const costBasis = amount * pos.entryPrice
      const tradePnl = proceeds - costBasis
      demoBalance.value += proceeds
      pnl.value += tradePnl
      pos.amount -= amount
      if (pos.amount <= 0) {
        positions.value = positions.value.filter(p => p.id !== pos.id)
      } else {
        pos.currentPrice = price
      }
    }

    history.value.push({
      date: new Date().toISOString(),
      value: totalValue.value
    })

    return { success: true }
  }

  return {
    positions, history, pnl, loading, demoBalance,
    totalValue, totalPnl, pnlPercent, positionCount,
    fetchPortfolio, fetchHistory, executeTrade
  }
})
