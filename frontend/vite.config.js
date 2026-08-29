import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/scan': 'http://localhost:8000',
      '/channels': 'http://localhost:8000',
      '/videos': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
