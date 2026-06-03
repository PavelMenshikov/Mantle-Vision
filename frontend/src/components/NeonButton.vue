<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'primary' },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' }
})

const emit = defineEmits(['click'])

const classes = computed(() => [
  'btn-neon relative inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-200 cursor-pointer select-none',
  'active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100',
  props.variant === 'primary' ? 'bg-cyber-accent/10 text-cyber-accent border border-cyber-accent/30 hover:bg-cyber-accent/20 hover:shadow-neon-green' : '',
  props.variant === 'secondary' ? 'bg-cyber-electric/10 text-cyber-electric border border-cyber-electric/30 hover:bg-cyber-electric/20 hover:shadow-neon-blue' : '',
  props.variant === 'danger' ? 'bg-cyber-danger/10 text-cyber-danger border border-cyber-danger/30 hover:bg-cyber-danger/20 hover:shadow-neon-red' : '',
  props.size === 'sm' ? 'px-3 py-1.5 text-xs' : '',
  props.size === 'md' ? 'px-4 py-2 text-sm' : '',
  props.size === 'lg' ? 'px-6 py-3 text-base' : ''
].filter(Boolean).join(' '))

function handleClick(e) {
  if (!props.disabled) {
    emit('click', e)
  }
}
</script>

<template>
  <button :class="classes" :disabled="disabled" @click="handleClick">
    <slot />
  </button>
</template>
