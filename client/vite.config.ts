import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  // Project Pages: https://<user>.github.io/Canto-0243/
  // Serve locally at / to keep dev ergonomics.
  base: command === 'serve' ? '/' : '/Canto-0243/',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [],
      workbox: {
        globPatterns: ['**/*.{js,css,html,woff2}'],
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024, // 50MB cache limit
        runtimeCaching: [
          {
            urlPattern: /\/lyrics\.(?:v?\d+\.\d+\.\d+)\.db$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'database-cache',
              expiration: {
                maxEntries: 2,
                maxAgeSeconds: 90 * 24 * 60 * 60 // 90 days
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
            src: 'icons.svg',
            sizes: 'any',
            type: 'image/svg+xml'
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
}))
