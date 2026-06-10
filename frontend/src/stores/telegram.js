import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTelegramStore = defineStore('telegram', () => {
  const connected = ref(false)
  const username = ref('')
  const code = ref('')
  const sessionToken = ref('')
  const loading = ref(false)
  const error = ref('')

  const botUsername = ref('dorahacksmantle_bot')
  const instructions = computed(() => {
    if (!code.value) return ''
    return `Send /start ${code.value} to @${botUsername} in Telegram`
  })

  let pollTimer = null
  let pollAbort = null

  async function initConnection() {
    loading.value = true
    error.value = ''
    console.log('[Telegram] Init connection...')
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000)
      const res = await fetch('/api/auth/telegram/init', { signal: controller.signal })
      clearTimeout(timeoutId)
      if (!res.ok) {
        console.warn('[Telegram] Init API returned', res.status, '- using offline fallback')
        code.value = 'OFFLINE'
        sessionToken.value = 'offline'
        return
      }
      const data = await res.json()
      console.log('[Telegram] Init response:', { code: data.code?.slice(0, 4) + '...', session_token: data.session_token?.slice(0, 8) + '...', bot_username: data.bot_username })
      code.value = data.code
      sessionToken.value = data.session_token
      if (data.bot_username) botUsername.value = data.bot_username
      startPolling()
    } catch (e) {
      console.error('[Telegram] Init failed (backend offline?):', e)
      code.value = 'OFFLINE'
      sessionToken.value = 'offline'
      error.value = 'Backend недоступен. Попробуй Demo.'
    } finally {
      loading.value = false
    }
  }

  function startPolling() {
    stopPolling()
    console.log('[Telegram] Start polling status every 2s')
    pollAbort = new AbortController()
    pollTimer = setInterval(async () => {
      try {
        const url = `/api/auth/telegram/status?session_token=${encodeURIComponent(sessionToken.value)}`
        const res = await fetch(url, { signal: pollAbort.signal })
        if (!res.ok) return
        const data = await res.json()
        if (data.connected) {
          console.log('[Telegram] Connected! username:', data.username)
          connected.value = true
          username.value = data.username || 'Telegram User'
          stopPolling()
        }
      } catch (e) {
        if (e.name !== 'AbortError') {
          console.warn('[Telegram] Poll error:', e)
        }
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
    initConnection, startPolling, stopPolling, disconnect
  }
})
