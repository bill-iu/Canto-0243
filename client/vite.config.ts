import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const repoRoot = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  resolve: {
    alias: {
      '@shared/query-tabs': path.resolve(repoRoot, '../frontend/query-tabs-state.mjs'),
      '@shared/search-navigation': path.resolve(repoRoot, '../frontend/search-navigation.mjs'),
    },
  },
  // Project Pages: https://<user>.github.io/Canto-0243/
  // Serve locally at / to keep dev ergonomics.
  base: command === 'serve' ? '/' : '/Canto-0243/',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'icon-32.png',
        'icon-180.png',
        'icon-192.png',
        'icon-512.png',
        'sql-wasm-browser.wasm',
        'fonts/fonts.css',
        'fonts/*.woff2',
      ],
      workbox: {
        globPatterns: ['**/*.{js,css,html,woff2,wasm}'],
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/_/, /\/[^/?]+\.[^/]+$/],
        skipWaiting: true,
        clientsClaim: true,
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024, // 50MB precache limit (lyrics.db uses runtimeCaching)
        runtimeCaching: [
          {
            urlPattern: /\/lyrics\.(?:dev|v[\d.]+(?:-[\w.]+)?)\.db$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'database-cache',
              expiration: {
                maxEntries: 2,
                maxAgeSeconds: 90 * 24 * 60 * 60 // 90 days
              }
            }
          },
          {
            urlPattern: /\/sql-wasm-browser\.wasm$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'sqljs-wasm-cache',
              expiration: {
                maxEntries: 1,
                maxAgeSeconds: 90 * 24 * 60 * 60
              }
            }
          }
        ]
      },
      manifest: {
        name: 'Canto-0243 PWA',
        short_name: 'Canto0243',
        description: '粵語填詞查詢工具 - 依 0243 數字碼搜尋可替換詞條',
        theme_color: '#EBDFD0',
        background_color: '#EBDFD0',
        display: 'standalone',
        start_url: '/Canto-0243/',
        scope: '/Canto-0243/',
        icons: [
          {
            src: 'icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
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
