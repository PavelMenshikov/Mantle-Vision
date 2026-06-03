/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cyber-bg': '#0a0a0f',
        'cyber-glass': 'rgba(255, 255, 255, 0.05)',
        'cyber-glass-hover': 'rgba(255, 255, 255, 0.08)',
        'cyber-glass-border': 'rgba(255, 255, 255, 0.1)',
        'cyber-accent': '#00ffaa',
        'cyber-accent-dim': 'rgba(0, 255, 170, 0.3)',
        'cyber-electric': '#3b82f6',
        'cyber-electric-dim': 'rgba(59, 130, 246, 0.3)',
        'cyber-danger': '#ff3366',
        'cyber-danger-dim': 'rgba(255, 51, 102, 0.3)',
        'cyber-warning': '#f59e0b',
        'cyber-warning-dim': 'rgba(245, 158, 11, 0.3)',
        'cyber-surface': '#12121a',
        'cyber-muted': '#6b7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
      backdropBlur: {
        glass: '20px',
      },
      boxShadow: {
        'neon-green': '0 0 15px rgba(0, 255, 170, 0.3), 0 0 45px rgba(0, 255, 170, 0.1)',
        'neon-blue': '0 0 15px rgba(59, 130, 246, 0.3), 0 0 45px rgba(59, 130, 246, 0.1)',
        'neon-red': '0 0 15px rgba(255, 51, 102, 0.3), 0 0 45px rgba(255, 51, 102, 0.1)',
        'neon-amber': '0 0 15px rgba(245, 158, 11, 0.3), 0 0 45px rgba(245, 158, 11, 0.1)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.4)',
        'glass-sm': '0 4px 16px rgba(0, 0, 0, 0.3)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'shimmer': 'shimmer 3s ease-in-out infinite',
        'scanline': 'scanline 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'fade-in': 'fade-in 0.5s ease-out',
        'slide-up': 'slide-up 0.5s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '0.6', filter: 'brightness(1)' },
          '50%': { opacity: '1', filter: 'brightness(1.3)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'scanline': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
      backgroundImage: {
        'cyber-gradient': 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)',
        'accent-gradient': 'linear-gradient(135deg, #00ffaa 0%, #3b82f6 100%)',
        'danger-gradient': 'linear-gradient(135deg, #ff3366 0%, #ff6b3d 100%)',
        'shimmer-gradient': 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)',
      },
    },
  },
  plugins: [],
}
