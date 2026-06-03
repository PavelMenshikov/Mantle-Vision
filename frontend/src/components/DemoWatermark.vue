<script setup>
</script>

<template>
  <div class="fixed inset-0 pointer-events-none z-50 flex items-center justify-center select-none">
    <div
      class="text-[12vw] font-display font-black text-transparent"
      style="
        -webkit-text-stroke: 1px rgba(0, 255, 170, 0.04);
        text-stroke: 1px rgba(0, 255, 170, 0.04);
        transform: rotate(-30deg) scale(1.5);
        letter-spacing: 0.2em;
      "
    >
      DEMO MODE
    </div>
  </div>
  <div class="fixed top-2 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
    <span class="px-4 py-1 rounded-full bg-cyber-accent/10 border border-cyber-accent/20 text-xs font-mono text-cyber-accent">
      DEMO MODE - Paper Trading
    </span>
  </div>
</template>
