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
    signals.value.filter(s => s.confidence >= 0.75)
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
    } finally {
      loading.value = false
    }
  }

  async function generateSignal() {
    try {
      const res = await fetch('/api/signals/generate', { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        if (data.signal) addSignal(data.signal)
      }
    } catch {
      // silently ignore — only real signals from backend
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
