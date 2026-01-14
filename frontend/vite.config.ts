import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Use relative paths for Electron file:// protocol
  base: './',
  build: {
    // Output to dist folder
    outDir: 'dist',
    // Empty output directory before build
    emptyOutDir: true,
    // Generate source maps for debugging
    sourcemap: true,
  },
  server: {
    port: 3000,
    // Proxy is only used in development mode
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:5000',
        ws: true,
      },
    },
  },
})
