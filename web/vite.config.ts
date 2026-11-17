import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, `/api` vai para a api local, como o nginx faz no compose.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        rewrite: (caminho) => caminho.replace(/^\/api/, ''),
      },
    },
  },
})
