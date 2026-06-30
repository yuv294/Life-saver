import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        cream: '#FDF8F1',
        'night-blue': '#6D8FD8',
        sage: '#7EBF95',
        amber: '#F5C96A',
        lavender: '#B8A9D4',
        teal: '#7EC8C8',
        peach: '#F5C4A0',
        coral: '#E8A090',
        // theme-aware: light in dark mode, dark in light mode (see --navy-rgb in globals.css)
        navy: 'rgb(var(--navy-rgb) / <alpha-value>)',
        'navy-light': '#2D3457',
        'star-white': '#F0EBE3',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        body: ['Spectral', 'Georgia', 'serif'],
      },
      animation: {
        'float': 'float 8s ease-in-out infinite',
        'float-delayed': 'float 10s ease-in-out infinite 2s',
        'twinkle': 'twinkle 4s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 6s ease-in-out infinite',
        'drift': 'drift 30s linear infinite',
        'fade-up': 'fade-up 0.6s ease-out',
        'shooting-star': 'shooting-star 1.5s ease-out forwards',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        twinkle: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.3)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 15px rgba(109, 143, 216, 0.2)' },
          '50%': { boxShadow: '0 0 35px rgba(109, 143, 216, 0.4)' },
        },
        drift: {
          '0%': { transform: 'translateX(-10px)' },
          '50%': { transform: 'translateX(10px)' },
          '100%': { transform: 'translateX(-10px)' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'shooting-star': {
          '0%': { transform: 'translateX(0) translateY(0)', opacity: '1' },
          '100%': { transform: 'translateX(200px) translateY(60px)', opacity: '0' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
export default config
