import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTelegramStore = defineStore('telegram', () => {
  const connected = ref(false)
  const username = ref('')
  const code = ref('')
  const sessionToken = ref('')
  const loading = ref(false)
  const error = ref('')

  const botUsername = ref('')
  const instructions = computed(() => {
    if (!code.value) return ''
    return `Send /connect ${code.value} to @${botUsername} in Telegram`
  })

  let pollTimer = null
  let pollAbort = null

  async function initConnection() {
    loading.value = true
    error.value = ''
    try {
      const res = await fetch('/api/auth/telegram/init')
      const data = await res.json()
      code.value = data.code
      sessionToken.value = data.session_token
      botUsername.value = data.bot_username || 'MantleVisionBot'
      startPolling()
    } catch (e) {
      error.value = 'Failed to generate code'
    } finally {
      loading.value = false
    }
  }

  function startPolling() {
    stopPolling()
    pollAbort = new AbortController()
    pollTimer = setInterval(async () => {
      try {
        const url = `/api/auth/telegram/status?session_token=${encodeURIComponent(sessionToken.value)}`
        const res = await fetch(url, { signal: pollAbort.signal })
        const data = await res.json()
        if (data.connected) {
          connected.value = true
          username.value = data.username || 'Telegram User'
          stopPolling()
        }
      } catch {
      }
    }, 2000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (pollAbort) {
      pollAbort.abort()
      pollAbort = null
    }
  }

  function disconnect() {
    connected.value = false
    username.value = ''
    code.value = ''
    sessionToken.value = ''
    error.value = ''
    stopPolling()
  }

  return {
    connected, username, code, loading, error, botUsername, instructions,
    initConnection, disconnect
  }
})
