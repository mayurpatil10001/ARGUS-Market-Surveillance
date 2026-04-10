export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0a0a0f',
        card: '#0f0f1a',
        surface: '#13131f',
        border: '#1a1a2e',
        'border-bright': '#252540',
        'green-accent': '#00ff88',
        'amber-accent': '#ffb300',
        'red-accent': '#ff3355',
        'text-primary': '#e8e8f0',
        'text-secondary': '#6b6b8a',
        'text-dim': '#3a3a55',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
