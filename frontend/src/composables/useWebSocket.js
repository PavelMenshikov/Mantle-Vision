import { ref } from 'vue'

export function useWebSocket(url, { onMessage, onOpen, onClose, onError } = {}) {
  const ws = ref(null)
  const connected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 50
  let reconnectTimer = null
  let visibilityHandler = null

  function connect() {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) return

    try {
      ws.value = new WebSocket(url)

      ws.value.onopen = () => {
        connected.value = true
        reconnectAttempts.value = 0
        if (onOpen) onOpen()
      }

      ws.value.onmessage = (event) => {
        if (onMessage) onMessage(event.data)
      }

      ws.value.onclose = () => {
        connected.value = false
        if (onClose) onClose()
        scheduleReconnect()
      }

      ws.value.onerror = (err) => {
        if (onError) onError(err)
      }
    } catch {
      scheduleReconnect()
    }
  }

  function scheduleReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) return
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000)
    reconnectTimer = setTimeout(() => {
      reconnectAttempts.value++
      connect()
    }, delay)
  }

  function reconnectNow() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      try { ws.value.close() } catch {}
      ws.value = null
    }
    connected.value = false
    reconnectAttempts.value = 0
    connect()
  }

  function send(data) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  function close() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    reconnectAttempts.value = maxReconnectAttempts
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler)
      visibilityHandler = null
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
  }

  function listenVisibility() {
    if (visibilityHandler) return
    visibilityHandler = () => {
      if (document.visibilityState === 'visible' && !connected.value) {
        reconnectNow()
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)
  }

  return { ws, connected, connect, send, close, reconnectNow, listenVisibility }
}
