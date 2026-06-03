<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps({
  data: { type: Array, default: () => [] },
  height: { type: Number, default: 250 }
})

const range = ref('1M')

const filteredData = computed(() => {
  if (!props.data.length) return []
  if (range.value === '1W') return props.data.slice(-7)
  if (range.value === '1M') return props.data
  if (range.value === '3M') return props.data
  return props.data
})

const chartData = computed(() => ({
  labels: filteredData.value.map(d => {
    const date = new Date(d.date)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }),
  datasets: [
    {
      label: 'Portfolio Value',
      data: filteredData.value.map(d => d.value),
      borderColor: '#00ffaa',
      backgroundColor: (ctx) => {
        if (!ctx.chart.chartArea) return 'rgba(0, 255, 170, 0.1)'
        const gradient = ctx.chart.ctx.createLinearGradient(0, ctx.chart.chartArea.top, 0, ctx.chart.chartArea.bottom)
        gradient.addColorStop(0, 'rgba(0, 255, 170, 0.3)')
        gradient.addColorStop(1, 'rgba(0, 255, 170, 0)')
        return gradient
      },
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHitRadius: 10,
      borderWidth: 2,
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(10, 10, 15, 0.9)',
      titleColor: '#00ffaa',
      bodyColor: '#f3f4f6',
      borderColor: 'rgba(0, 255, 170, 0.2)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 12,
      displayColors: false,
      callbacks: {
        label: (ctx) => '$' + ctx.parsed.y.toFixed(2)
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        color: '#6b7280',
        font: { family: 'JetBrains Mono', size: 10 },
        maxTicksLimit: 8
      }
    },
    y: {
      grid: {
        color: 'rgba(255, 255, 255, 0.03)',
        drawBorder: false
      },
      ticks: {
        color: '#6b7280',
        font: { family: 'JetBrains Mono', size: 10 },
        callback: (v) => '$' + v.toLocaleString()
      }
    }
  },
  interaction: {
    intersect: false,
    mode: 'index'
  }
}

const ranges = ['1W', '1M', '3M', 'ALL']
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-display font-semibold text-white">Portfolio P&L</h3>
      <div class="flex glass !p-0.5 rounded-lg gap-0.5">
        <button
          v-for="r in ranges"
          :key="r"
          @click="range = r"
          :class="[
            'px-2.5 py-1 text-[10px] font-mono rounded-md transition-all duration-200',
            range === r ? 'bg-cyber-accent/20 text-cyber-accent' : 'text-cyber-muted hover:text-white'
          ]"
        >
          {{ r }}
        </button>
      </div>
    </div>
    <div class="relative" :style="{ height: height + 'px' }">
      <Line v-if="filteredData.length" :data="chartData" :options="chartOptions" />
      <div v-else class="flex items-center justify-center h-full text-cyber-muted text-sm">
        No chart data available
      </div>
    </div>
  </div>
</template>
