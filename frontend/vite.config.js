import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v3-[hash].js`,
        chunkFileNames: `assets/[name]-v3-[hash].js`,
        assetFileNames: `assets/[name]-v3-[hash].[ext]`
      }
    }
  }
})
