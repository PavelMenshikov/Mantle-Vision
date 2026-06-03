<script setup>
import { computed } from 'vue'

const props = defineProps({
  glowing: { type: Boolean, default: false },
  accent: { type: String, default: '' },
  padded: { type: Boolean, default: true },
  class: { type: String, default: '' }
})

const classes = computed(() => [
  'glass relative overflow-hidden transition-all duration-300',
  props.glowing ? 'glass-accent' : '',
  props.accent === 'green' ? 'border-cyber-accent/20 hover:border-cyber-accent/40' : '',
  props.accent === 'blue' ? 'border-cyber-electric/20 hover:border-cyber-electric/40' : '',
  props.accent === 'red' ? 'border-cyber-danger/20 hover:border-cyber-danger/40' : '',
  props.accent === 'amber' ? 'border-cyber-warning/20 hover:border-cyber-warning/40' : '',
  props.padded ? 'p-5' : '',
  props.class
].filter(Boolean).join(' '))
</script>

<template>
  <div :class="classes">
    <div class="glass-header"></div>
    <slot />
  </div>
</template>
