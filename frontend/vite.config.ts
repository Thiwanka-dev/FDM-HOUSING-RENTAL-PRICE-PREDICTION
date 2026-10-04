import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Requests to /api go to the Python backend, so the browser needs no CORS setup.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
