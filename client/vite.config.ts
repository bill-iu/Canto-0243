import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['lyrics.db'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,db,woff2}'],
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024, // 50MB cache limit
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\.db$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'database-cache',
              expiration: {
                maxEntries: 1,
                maxAgeSeconds: 30 * 24 * 60 * 60 // 30 days
              }
            }
          }
        ]
      },
      manifest: {
        name: 'Canto-0243 PWA',
        short_name: 'Canto0243',
        description: '粵語填詞查詢工具 - 依 0243 數字碼搜尋可替換詞條',
        theme_color: '#ffffff',
        background_color: '#f5f5f5',
        display: 'standalone',
        icons: [
          {
            src: '/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  assetsInclude: ['**/*.db'],
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp'
    }
  }
})
