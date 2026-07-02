import path from 'node:path';
import { fileURLToPath } from 'node:url';
import basicSsl from '@vitejs/plugin-basic-ssl';
import { defineConfig } from 'vite';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const fixtureDb = path.join(repoRoot, 'tests/fixtures/lyrics.db');
const devDb = path.join(repoRoot, 'client/public/lyrics.dev.db');

/** ponytail: serve fixture (fast) or release db without copying into poc */
function serveDbPlugin() {
  return {
    name: 'serve-lyrics-db',
    configureServer(server: import('vite').ViteDevServer) {
      server.middlewares.use('/lyrics.fixture.db', async (_req, res) => {
        const fs = await import('node:fs/promises');
        const buf = await fs.readFile(fixtureDb);
        res.setHeader('Content-Type', 'application/octet-stream');
        res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
        res.end(buf);
      });
      server.middlewares.use('/lyrics.dev.db', async (_req, res) => {
        const fs = await import('node:fs/promises');
        const buf = await fs.readFile(devDb);
        res.setHeader('Content-Type', 'application/octet-stream');
        res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
        res.end(buf);
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const iosHttps = mode === 'ios';

  return {
    plugins: [serveDbPlugin(), ...(iosHttps ? [basicSsl()] : [])],
    resolve: {
      alias: {
        '@canto/db': path.join(repoRoot, 'client/src/db'),
      },
    },
    server: {
      host: iosHttps,
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
      },
    },
    worker: {
      format: 'es',
    },
    optimizeDeps: {
      exclude: ['@journeyapps/wa-sqlite'],
    },
  };
});
