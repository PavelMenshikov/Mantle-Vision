import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const THEMES = ['dark', 'silver', 'light']

export const useThemeStore = defineStore('theme', () => {
  const saved = localStorage.getItem('mv-theme')
  const current = ref(THEMES.includes(saved) ? saved : 'dark')

  watch(current, (val) => {
    document.documentElement.setAttribute('data-theme', val)
    localStorage.setItem('mv-theme', val)
  }, { immediate: true })

  function setTheme(t) {
    current.value = t
  }

  return { current, setTheme, THEMES }
})
