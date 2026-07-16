/** Portable host build artifact contract — node client/scripts/portable-host-build-self-check.mjs */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const clientRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const distDir = path.join(clientRoot, 'dist-portable');
const indexHtml = path.join(distDir, 'index.html');

if (!fs.existsSync(indexHtml)) {
  console.error('portable-host-build-self-check: missing dist-portable/index.html');
  process.exit(1);
}

const html = fs.readFileSync(indexHtml, 'utf8');
for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
  const url = match[1];
  if (url.startsWith('/') && !url.startsWith('/app/')) {
    console.error(`portable-host-build-self-check: asset not under /app/: ${url}`);
    process.exit(1);
  }
}

const assetsDir = path.join(distDir, 'assets');
if (!fs.existsSync(assetsDir)) {
  console.error('portable-host-build-self-check: missing dist-portable/assets');
  process.exit(1);
}

for (const name of fs.readdirSync(assetsDir)) {
  if (!name.endsWith('.js')) continue;
  const content = fs.readFileSync(path.join(assetsDir, name), 'utf8');
  if (content.includes('virtual:pwa-register')) {
    console.error(`portable-host-build-self-check: ${name} contains virtual:pwa-register`);
    process.exit(1);
  }
  for (const marker of ['__WB_MANIFEST', 'workbox-precaching', 'workbox-routing', 'workbox-strategies']) {
    if (content.includes(marker)) {
      console.error(`portable-host-build-self-check: ${name} contains vite-plugin-pwa marker ${marker}`);
      process.exit(1);
    }
  }
}

for (const name of fs.readdirSync(distDir)) {
  if (name === 'sw.js' || /^workbox-.*\.js$/.test(name)) {
    console.error(`portable-host-build-self-check: unexpected PWA artifact ${name}`);
    process.exit(1);
  }
}

console.log('portable-host-build-self-check: ok');
