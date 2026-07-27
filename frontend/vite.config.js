// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // If you need any specific Vite configurations for Bootstrap
  css: {
    preprocessorOptions: {
      scss: {
        // If you want to use SCSS version of Bootstrap
        additionalData: `@import "bootstrap/scss/bootstrap";`
      }
    }
  },
  esbuild: {
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
  }
})