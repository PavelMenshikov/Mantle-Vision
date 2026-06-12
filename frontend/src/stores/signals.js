import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

export const useSignalsStore = defineStore('signals', () => {
  const signals = shallowRef([])
  const loading = ref(false)
  const error = ref(null)
  const ws = ref(null)
  const notifications = shallowRef([])
  let lastFetch = 0

  const signalCount = computed(() => signals.value.length)

  const highConfidenceSignals = computed(() =>
    signals.value.filter(s => s.confidence >= 0.75)
  )

  const highConfidenceCount = computed(() => highConfidenceSignals.value.length)

  const recentSignals = computed(() =>
    [...signals.value]
      .filter(s => s.direction !== 'hold' || (s.confidence || 0) >= 0.5)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10)
  )

  function addSignal(signal) {
    if (signal.direction === 'hold' && (signal.confidence || 0) < 0.5) return
    const exists = signals.value.some(s => s.id === signal.id)
    if (!exists) {
      signals.value.unshift(signal)
      if (signals.value.length > 200) {
        signals.value = signals.value.slice(0, 200)
      }
    }
  }

  function addNotification(n) {
    notifications.value.unshift({ ...n, _received: Date.now() })
    if (notifications.value.length > 50) {
      notifications.value = notifications.value.slice(0, 50)
    }
  }

  async function fetchSignals(force = false) {
    if (!force && Date.now() - lastFetch < 30000 && signals.value.length) return
    loading.value = true
    error.value = null
    try {
      const res = await fetch('/api/signals')
      if (!res.ok) throw new Error('Failed to fetch signals')
      const data = await res.json()
      const raw = data.signals || data || []
      signals.value = raw.filter(s => s.direction !== 'hold' || (s.confidence || 0) >= 0.5)
      lastFetch = Date.now()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function clearNotifications() {
    notifications.value = []
  }

  let wsConnected = false

  function connectWebSocket() {
    if (wsConnected) return
    wsConnected = true
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const instance = useWebSocket(`${protocol}//${host}/ws`, {
      onMessage(data) {
        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'heartbeat' || parsed.type === 'pong') return
          if (parsed.type === 'signal' || parsed.signal) {
            addSignal(parsed.signal || parsed)
          } else if (parsed.id && parsed.direction) {
            addSignal(parsed)
          }
          const notifTypes = ['whale_alert', 'anomaly', 'smart_money', 'insider_cluster', 'tracked_wallet']
          if (notifTypes.includes(parsed.type)) {
            addNotification(parsed)
          }
        } catch { }
      }
    })
    instance.connect()
    instance.listenVisibility()
    ws.value = instance
  }

  function disconnectWebSocket() {
    wsConnected = false
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return {
    signals, loading, error,
    notifications,
    signalCount, highConfidenceSignals, highConfidenceCount, recentSignals,
    fetchSignals, addSignal,
    addNotification, clearNotifications,
    connectWebSocket, disconnectWebSocket
  }
})
