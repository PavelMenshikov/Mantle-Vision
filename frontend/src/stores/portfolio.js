import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePortfolioStore = defineStore('portfolio', () => {
  const positions = ref([])
  const history = ref([])
  const pnl = ref(0)
  const loading = ref(false)

  const totalValue = computed(() => {
    const posValue = positions.value.reduce((sum, p) => sum + (p.amount * p.currentPrice), 0)
    return posValue
  })

  const totalPnl = computed(() => pnl.value)

  const pnlPercent = computed(() => {
    return pnl.value.toFixed(2)
  })

  const positionCount = computed(() => positions.value.length)

  async function fetchPortfolio() {
    loading.value = true
    try {
      const res = await fetch('/api/portfolio')
      if (res.ok) {
        const data = await res.json()
        positions.value = data.positions || data || []
      }
    } catch {
      // silently ignore — no demo data
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory() {
    try {
      const res = await fetch('/api/portfolio/history')
      if (res.ok) {
        const data = await res.json()
        history.value = data.history || data || []
      }
    } catch {
      // silently ignore — no demo data
    }
  }

  return {
    positions, history, pnl, loading,
    totalValue, totalPnl, pnlPercent, positionCount,
    fetchPortfolio, fetchHistory
  }
})
