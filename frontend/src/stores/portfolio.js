import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

let lastFetch = 0
const CACHE_TTL = 30000

export const usePortfolioStore = defineStore('portfolio', () => {
  const positions = ref([])
  const history = ref([])
  const pnl = ref(0)
  const loading = ref(false)

  const totalValue = computed(() => {
    return positions.value.reduce((sum, p) => sum + (p.amount * p.currentPrice), 0)
  })

  const totalPnl = computed(() => {
    if (pnl.value) return pnl.value
    if (!positions.value.length) return 0
    return positions.value.reduce((sum, p) => sum + ((p.currentPrice - p.entryPrice) * p.amount), 0)
  })

  const pnlPercent = computed(() => totalPnl.value.toFixed(2))

  const positionCount = computed(() => positions.value.length)

  async function fetchPortfolio() {
    if (Date.now() - lastFetch < CACHE_TTL && positions.value.length) return
    loading.value = true
    try {
      const res = await fetch('/api/portfolio')
      if (res.ok) {
        positions.value = await res.json()
        lastFetch = Date.now()
      }
    } catch {
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory() {
    if (Date.now() - lastFetch < CACHE_TTL && history.value.length) return
    try {
      const res = await fetch('/api/portfolio/history')
      if (res.ok) {
        const data = await res.json()
        history.value = data.history || data || []
      }
    } catch {
    }
  }

  return {
    positions, history, pnl, loading,
    totalValue, totalPnl, pnlPercent, positionCount,
    fetchPortfolio, fetchHistory
  }
})
