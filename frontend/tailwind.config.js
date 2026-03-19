/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0b1020',
        panel: '#121a2b',
        panelAlt: '#172238',
        line: '#24324d',
        accent: '#f97316',
        accentSoft: '#fdba74',
        up: '#22c55e',
        down: '#ef4444',
      },
      boxShadow: {
        panel: '0 18px 60px rgba(5, 8, 18, 0.28)',
      },
      fontFamily: {
        sans: ['"Space Grotesk"', '"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      backgroundImage: {
        grid: 'linear-gradient(rgba(126, 154, 204, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(126, 154, 204, 0.08) 1px, transparent 1px)',
      },
    },
  },
  plugins: [],
}
