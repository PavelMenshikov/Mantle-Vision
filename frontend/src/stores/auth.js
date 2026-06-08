import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('mv_token') || '')
  const address = ref(localStorage.getItem('mv_address') || '')
  const method = ref(localStorage.getItem('mv_method') || '')
  const tgUsername = ref(localStorage.getItem('mv_tg_username') || '')

  const isAuthenticated = computed(() => !!token.value || !!tgUsername.value)

  const displayName = computed(() => {
    if (tgUsername.value) return '@' + tgUsername.value
    if (address.value) return address.value.slice(0, 6) + '...' + address.value.slice(-4)
    return ''
  })

  async function loginMetaMask() {
    if (!window.ethereum) { console.warn('[Auth] No MetaMask detected'); return 'no_ethereum' }
    try {
      console.log('[Auth] Requesting MetaMask accounts...')
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
      const addr = accounts[0]
      console.log('[Auth] Account:', addr)

      console.log('[Auth] Fetching nonce...')
      const nonceRes = await fetch(`/api/auth/nonce/${addr}`)
      if (!nonceRes.ok) { console.error('[Auth] Nonce failed:', nonceRes.status); return 'nonce_failed' }
      const nonceData = await nonceRes.json()
      console.log('[Auth] Nonce received')

      console.log('[Auth] Requesting MetaMask signature...')
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [nonceData.message, addr]
      })
      console.log('[Auth] Signature received, length:', signature.length)

      console.log('[Auth] Verifying signature...')
      const verifyRes = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr, signature, message: nonceData.message })
      })
      if (!verifyRes.ok) {
        const errText = await verifyRes.text().catch(() => '')
        console.error('[Auth] Verify failed:', verifyRes.status, errText)
        return 'verify_failed'
      }
      const data = await verifyRes.json()
      console.log('[Auth] Login success, token:', data.token?.slice(0, 16) + '...')

      token.value = data.token
      address.value = data.address
      method.value = 'metamask'

      localStorage.setItem('mv_token', data.token)
      localStorage.setItem('mv_address', data.address)
      localStorage.setItem('mv_method', 'metamask')
      return 'ok'
    } catch (e) {
      console.error('[Auth] Login error:', e)
      return 'error'
    }
  }

  function setTelegramAuth(username) {
    tgUsername.value = username
    method.value = 'telegram'
    localStorage.setItem('mv_tg_username', username)
    localStorage.setItem('mv_method', 'telegram')
  }

  function logout() {
    token.value = ''
    address.value = ''
    method.value = ''
    tgUsername.value = ''
    localStorage.removeItem('mv_token')
    localStorage.removeItem('mv_address')
    localStorage.removeItem('mv_method')
    localStorage.removeItem('mv_tg_username')
  }

  return {
    token, address, method, tgUsername, isAuthenticated, displayName,
    loginMetaMask, setTelegramAuth, logout
  }
})
