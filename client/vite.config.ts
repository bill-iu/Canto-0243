import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Plugin } from 'vite'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const clientRoot = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(clientRoot, '..')
const readyGateCssPath = path.resolve(repoRoot, 'frontend/ready-gate.css')
const rootLyricsDb = path.resolve(repoRoot, 'lyrics.db')
const publicLyricsDb = path.resolve(clientRoot, 'public/lyrics.db')

function readyGateCssPlugin(): Plugin {
  const serve = () => {
    const css = fs.readFileSync(readyGateCssPath)
    return (_req: unknown, res: { setHeader: (k: string, v: string) => void; end: (b: Buffer) => void }) => {
      res.setHeader('Content-Type', 'text/css; charset=utf-8')
      res.end(css)
    }
  }

  return {
    name: 'ready-gate-css',
    configureServer(server) {
      server.middlewares.use('/ready-gate.css', serve())
      const base = server.config.base.replace(/\/$/, '')
      if (base) server.middlewares.use(`${base}/ready-gate.css`, serve())
    },
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'ready-gate.css',
        source: fs.readFileSync(readyGateCssPath),
      })
    },
  }
}

/** S2 詞庫開發掛載（ADR-0036）：dev 優先 stream 根 SSOT lyrics.db */
function lexiconDevMountPlugin(): Plugin {
  return {
    name: 'lexicon-dev-mount',
    configureServer(server) {
      const handler = (
        _req: unknown,
        res: {
          statusCode: number
          setHeader: (k: string, v: string) => void
          end: (b?: string | Buffer) => void
        },
        next: () => void,
      ) => {
        const src = fs.existsSync(rootLyricsDb)
          ? rootLyricsDb
          : fs.existsSync(publicLyricsDb)
            ? publicLyricsDb
            : null
        if (!src) {
          next()
          return
        }
        try {
          const stat = fs.statSync(src)
          res.setHeader('Content-Type', 'application/octet-stream')
          res.setHeader('Content-Length', String(stat.size))
          res.setHeader('Cache-Control', 'no-cache')
          fs.createReadStream(src).pipe(res as unknown as NodeJS.WritableStream)
        } catch {
          res.statusCode = 500
          res.end('lexicon dev mount failed')
        }
      }
      server.middlewares.use('/lyrics.db', handler)
      const base = server.config.base.replace(/\/$/, '')
      if (base) server.middlewares.use(`${base}/lyrics.db`, handler)
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  resolve: {
    alias: {
      '@shared/query-tabs': path.resolve(clientRoot, '../frontend/query-tabs-state.mjs'),
      '@shared/search-navigation': path.resolve(clientRoot, '../frontend/search-navigation.mjs'),
    },
  },
  // Project Pages: https://<user>.github.io/Canto-0243/
  // Serve locally at / to keep dev ergonomics.
  base: command === 'serve' ? '/' : '/Canto-0243/',
  plugins: [
    react(),
    readyGateCssPlugin(),
    lexiconDevMountPlugin(),
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
            urlPattern: /\/lexicon-manifest\.json$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'lexicon-manifest-cache',
              networkTimeoutSeconds: 3,
              expiration: {
                maxEntries: 1,
                maxAgeSeconds: 24 * 60 * 60
              }
            }
          },
          {
            urlPattern: /\/lyrics(?:\.[^/]+)?\.db(?:\.gz)?$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'database-cache',
              expiration: {
                maxEntries: 1,
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
