<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTelegramStore } from '@/stores/telegram'
import GlassCard from '@/components/GlassCard.vue'

const router = useRouter()
const auth = useAuthStore()
const tg = useTelegramStore()

const connecting = ref('')
const error = ref('')

onMounted(() => {
  if (auth.isAuthenticated) router.push('/')
})

async function connectMetaMask() {
  connecting.value = 'metamask'
  error.value = ''
  const result = await auth.loginMetaMask()
  if (result === 'ok') {
    router.push('/')
  } else if (result === 'no_ethereum') {
    error.value = 'MetaMask not detected. Install MetaMask or use Telegram.'
  } else {
    error.value = 'Authentication failed. Try again.'
  }
  connecting.value = ''
}

async function connectTelegram() {
  connecting.value = 'telegram'
  error.value = ''
  tg.stopPolling()
  await tg.initConnection()
  connecting.value = ''
}

import { watch } from 'vue'
watch(() => tg.connected, (val) => {
  if (val) {
    auth.setTelegramAuth(tg.username)
    router.push('/')
  }
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6">
    <div class="w-full max-w-md space-y-6 animate-fade-in">
      <div class="text-center space-y-2">
        <h1 class="text-4xl font-display font-bold text-gradient">Mantle Vision</h1>
        <p class="text-sm text-cyber-muted font-mono">On-Chain Wallet Intelligence</p>
      </div>

      <GlassCard accent="green">
        <h2 class="text-lg font-display font-semibold text-cyber-text mb-6 text-center">Sign In</h2>

        <div class="space-y-4">
          <button
            @click="connectMetaMask"
            :disabled="!!connecting"
            class="w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-xl bg-accent-gradient text-black font-semibold text-sm hover:shadow-neon-green transition-all duration-200 active:scale-95 disabled:opacity-50"
          >
            <svg class="w-5 h-5" viewBox="0 0 35 33" fill="none"><path d="M32.9582 1L19.8241 10.7183L22.2452 5.61852L32.9582 1Z" fill="#E17726" stroke="#E17726" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M2.04201 1L15.0857 10.7927L12.7549 5.61852L2.04201 1Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M28.1563 23.5346L24.8153 28.555L31.9754 30.555L34.0953 23.6218L28.1563 23.5346Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M0.913086 23.6218L3.0248 30.555L10.1757 28.555L6.84389 23.5346L0.913086 23.6218Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.79535 14.4644L7.82959 17.503L14.8852 17.7576L14.6704 10.1505L9.79535 14.4644Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M25.2047 14.4644L20.2833 10.0728L20.1509 17.7576L27.2065 17.503L25.2047 14.4644Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M10.1757 28.555L14.5571 26.3455L10.7696 23.4663L10.1757 28.555Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.4429 26.3455L24.8153 28.555L24.2304 23.4663L20.4429 26.3455Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M24.8153 28.555L20.4429 26.3455L20.8073 29.1266L20.7711 30.1846L24.8153 28.555Z" fill="#D7BFEF" stroke="#D7BFEF" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M10.1757 28.555L14.229 30.1846L14.2019 29.1266L14.5571 26.3455L10.1757 28.555Z" fill="#D7BFEF" stroke="#D7BFEF" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M14.4662 21.9406L10.8242 20.8603L13.4751 19.5781L14.4662 21.9406Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.5339 21.9406L21.525 19.5781L24.1849 20.8603L20.5339 21.9406Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M10.7696 23.4663L14.2019 29.1266L14.4662 21.9406L10.7696 23.4663Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.5339 21.9406L20.8073 29.1266L24.2304 23.4663L20.5339 21.9406Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M24.1849 20.8603L20.5339 21.9406L24.2304 23.4663L24.1849 20.8603Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/><path d="M10.8242 20.8603L10.7696 23.4663L14.4662 21.9406L10.8242 20.8603Z" fill="#E27625" stroke="#E27625" stroke-width="0.25" stroke-linecap="round" stroke-linejoin="round"/></svg>
            {{ connecting === 'metamask' ? 'Connecting...' : 'MetaMask' }}
          </button>

          <div class="relative">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-white/10"></div>
            </div>
            <div class="relative flex justify-center text-xs">
              <span class="bg-cyber-bg px-3 text-cyber-muted font-mono">or</span>
            </div>
          </div>

          <button
            @click="connectTelegram"
            :disabled="!!connecting"
            class="w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-xl border border-cyber-electric/30 text-cyber-electric font-semibold text-sm hover:bg-cyber-electric/10 hover:border-cyber-electric/50 transition-all duration-200 active:scale-95 disabled:opacity-50"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
            {{ connecting === 'telegram' ? 'Connecting...' : 'Telegram' }}
          </button>
        </div>

        <div v-if="error" class="mt-4 text-xs text-cyber-danger font-mono text-center">{{ error }}</div>

        <div v-if="tg.code && !tg.connected" class="mt-6 p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
          <div class="text-xs text-cyber-muted font-mono text-center">Send this code to the bot:</div>
          <div class="text-center">
            <code class="text-lg font-mono text-cyber-accent bg-cyber-accent/10 px-4 py-2 rounded-lg tracking-widest">{{ tg.code }}</code>
          </div>
          <a :href="`https://t.me/${tg.botUsername}?start=${tg.code}`" target="_blank"
            class="block text-center text-xs text-cyber-electric hover:text-cyber-accent font-mono transition-colors">
            @{{ tg.botUsername }}
          </a>
          <div class="text-[10px] text-cyber-muted font-mono text-center animate-pulse">Waiting for confirmation...</div>
        </div>
      </GlassCard>
    </div>
  </div>
</template>
