import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Ra gold — used for accents throughout
        ra: {
          gold: '#c9a84c',
          light: '#e2c46e',
          dark: '#9b7c30',
          muted: 'rgba(201,168,76,0.15)',
        },
      },
    },
  },
  plugins: [],
}

export default config
