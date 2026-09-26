import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages serves under /Mirror-Lake/; Vercel serves from domain root.
const base = process.env.VERCEL ? '/' : '/Mirror-Lake/'

export default defineConfig({
  plugins: [react()],
  base,
  build: {
    outDir: 'docs',
  },
})
