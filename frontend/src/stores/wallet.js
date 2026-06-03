import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWalletStore = defineStore('wallet', () => {
  const connected = ref(false)
  const address = ref('')
  const balance = ref('0')
  const chainId = ref(5000)
  const mode = ref('demo')
  const demoAddress = '0xDEMO...M4NTl3'
  const demoBalance = '10000.00'

  const shortAddress = computed(() => {
    if (!address.value) return ''
    return address.value.slice(0, 6) + '...' + address.value.slice(-4)
  })

  const formattedBalance = computed(() => {
    const num = parseFloat(balance.value)
    return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  })

  const isDemo = computed(() => mode.value === 'demo')
  const isReal = computed(() => mode.value === 'real')

  async function connect(modeType = 'demo') {
    mode.value = modeType
    if (modeType === 'demo') {
      connected.value = true
      address.value = demoAddress
      balance.value = demoBalance
      chainId.value = 5000
      return
    }
    try {
      if (window.ethereum) {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
        const chain = await window.ethereum.request({ method: 'eth_chainId' })
        connected.value = true
        address.value = accounts[0]
        chainId.value = parseInt(chain, 16)
        const bal = await window.ethereum.request({
          method: 'eth_getBalance',
          params: [accounts[0], 'latest']
        })
        balance.value = (parseInt(bal, 16) / 1e18).toFixed(4)
      } else {
        connected.value = true
        address.value = demoAddress
        balance.value = demoBalance
        chainId.value = 5000
        mode.value = 'demo'
      }
    } catch {
      connected.value = true
      address.value = demoAddress
      balance.value = demoBalance
      mode.value = 'demo'
    }
  }

  function disconnect() {
    connected.value = false
    address.value = ''
    balance.value = '0'
    chainId.value = 5000
  }

  function toggleMode() {
    if (mode.value === 'demo') {
      connect('real')
    } else {
      connect('demo')
    }
  }

  return {
    connected, address, balance, chainId, mode,
    shortAddress, formattedBalance, isDemo, isReal,
    connect, disconnect, toggleMode
  }
})
