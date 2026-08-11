import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v4-[hash].js`,
        chunkFileNames: `assets/[name]-v4-[hash].js`,
        assetFileNames: `assets/[name]-v4-[hash].[ext]`
      }
    }
  }
})
