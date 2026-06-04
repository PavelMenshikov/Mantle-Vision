<script setup>
import { useTelegramStore } from '@/stores/telegram'
import NeonButton from '@/components/NeonButton.vue'

const tg = useTelegramStore()
</script>

<template>
  <div>
    <template v-if="!tg.connected">
      <button
        @click="tg.initConnection()"
        :disabled="tg.loading"
        class="relative px-5 py-2 text-sm font-medium rounded-xl bg-accent-gradient text-black hover:shadow-neon-green transition-all duration-200 active:scale-95 disabled:opacity-50"
      >
        {{ tg.loading ? 'Generating...' : 'Connect Telegram' }}
      </button>

      <div v-if="tg.code" class="mt-3 p-3 rounded-xl bg-white/5 border border-white/10">
        <div class="text-xs text-cyber-muted font-mono mb-2">Send this code to the bot:</div>
        <div class="flex items-center gap-2">
          <code class="text-sm font-mono text-cyber-accent bg-cyber-accent/10 px-3 py-1.5 rounded-lg">{{ tg.code }}</code>
          <span class="text-xs text-cyber-muted font-mono">or click:</span>
        </div>
        <a
          :href="`https://t.me/${tg.botUsername}?start=${tg.code}`"
          target="_blank"
          class="inline-flex items-center gap-2 mt-2 text-xs font-mono text-cyber-electric hover:text-cyber-accent transition-colors"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-cyber-electric animate-pulse-glow"></span>
          t.me/{{ tg.botUsername }}?start={{ tg.code }}
        </a>
        <div class="text-[10px] text-cyber-muted font-mono mt-2">Waiting for confirmation...</div>
      </div>

      <div v-if="tg.error" class="text-xs text-cyber-danger font-mono mt-2">{{ tg.error }}</div>
    </template>

    <template v-else>
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyber-electric/10 border border-cyber-electric/20">
        <span class="w-2 h-2 rounded-full bg-cyber-electric"></span>
        <span class="text-xs font-mono text-cyber-electric">@{{ tg.username }}</span>
      </div>
      <button
        @click="tg.disconnect()"
        class="text-xs text-cyber-muted hover:text-cyber-danger transition-colors mt-2"
      >
        Disconnect
      </button>
    </template>
  </div>
</template>
