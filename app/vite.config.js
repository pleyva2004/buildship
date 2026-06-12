import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /assets/* is served from the repo's asset tree (the A↔B filename contract).
// In dev we proxy via fs.allow + a symlink made by `make app`; /api proxies to
// the agent backend (design 04 §5) once it exists.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8001',
    },
  },
})
