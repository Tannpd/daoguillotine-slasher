import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-v6-[hash].js`,
        chunkFileNames: `assets/[name]-v6-[hash].js`,
        assetFileNames: `assets/[name]-v6-[hash].[ext]`
      }
    }
  }
})
