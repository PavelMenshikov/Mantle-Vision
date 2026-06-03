import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

export const useSignalsStore = defineStore('signals', () => {
  const signals = ref([])
  const loading = ref(false)
  const error = ref(null)
  const ws = ref(null)

  const signalCount = computed(() => signals.value.length)

  const highConfidenceSignals = computed(() =>
    signals.value.filter(s => s.confidence >= 75)
  )

  const highConfidenceCount = computed(() => highConfidenceSignals.value.length)

  const recentSignals = computed(() =>
    [...signals.value].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10)
  )

  function addSignal(signal) {
    const exists = signals.value.some(s => s.id === signal.id)
    if (!exists) {
      signals.value.unshift(signal)
      if (signals.value.length > 200) {
        signals.value = signals.value.slice(0, 200)
      }
    }
  }

  async function fetchSignals() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch('/api/signals')
      if (!res.ok) throw new Error('Failed to fetch signals')
      const data = await res.json()
      signals.value = data.signals || data || []
    } catch (e) {
      error.value = e.message
      loadDemoSignals()
    } finally {
      loading.value = false
    }
  }

  function loadDemoSignals() {
    signals.value = [
      { id: '1', type: 'price_breakout', direction: 'bullish', confidence: 87, asset: 'MNT', reasoning: 'MNT breaking above resistance with strong volume. On-chain accumulation detected across top 100 wallets.', timestamp: new Date(Date.now() - 300000).toISOString(), source: 'ai_agent' },
      { id: '2', type: 'whale_move', direction: 'bearish', confidence: 72, asset: 'mETH', reasoning: 'Whale wallet 0x8f...b3 moved 15,000 mETH to exchange. Potential sell pressure incoming.', timestamp: new Date(Date.now() - 900000).toISOString(), source: 'whale_tracker' },
      { id: '3', type: 'liquidation', direction: 'bullish', confidence: 93, asset: 'USDC', reasoning: 'Large short positions liquidated on Mantle. $4.2M in buy pressure expected to cascade.', timestamp: new Date(Date.now() - 1800000).toISOString(), source: 'liquidation_monitor' },
      { id: '4', type: 'price_breakout', direction: 'bullish', confidence: 68, asset: 'USDY', reasoning: 'USDY showing consistent buy pressure. Accumulation phase likely underway.', timestamp: new Date(Date.now() - 3600000).toISOString(), source: 'ai_agent' },
      { id: '5', type: 'whale_move', direction: 'bullish', confidence: 81, asset: 'MNT', reasoning: 'New whale accumulated 500K MNT over past 48 hours. Average entry $0.85.', timestamp: new Date(Date.now() - 7200000).toISOString(), source: 'whale_tracker' },
    ]
  }

  async function generateSignal() {
    try {
      const res = await fetch('/api/signals/generate', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        if (data.signal) addSignal(data.signal)
      }
    } catch {
      const demoSignal = {
        id: 'demo_' + Date.now(),
        type: ['price_breakout', 'whale_move', 'liquidation'][Math.floor(Math.random() * 3)],
        direction: Math.random() > 0.5 ? 'bullish' : 'bearish',
        confidence: Math.floor(Math.random() * 40) + 55,
        asset: ['MNT', 'mETH', 'USDC', 'USDY'][Math.floor(Math.random() * 4)],
        reasoning: 'AI-generated signal based on on-chain data analysis.',
        timestamp: new Date().toISOString(),
        source: 'ai_agent'
      }
      addSignal(demoSignal)
    }
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    ws.value = useWebSocket(`${protocol}//${host}/ws`, {
      onMessage(data) {
        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'heartbeat' || parsed.type === 'pong') return
          if (parsed.type === 'signal' || parsed.signal) {
            addSignal(parsed.signal || parsed)
          } else if (parsed.id && parsed.direction) {
            addSignal(parsed)
          }
        } catch { }
      }
    })
  }

  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return {
    signals, loading, error,
    signalCount, highConfidenceSignals, highConfidenceCount, recentSignals,
    fetchSignals, generateSignal, addSignal,
    connectWebSocket, disconnectWebSocket
  }
})
