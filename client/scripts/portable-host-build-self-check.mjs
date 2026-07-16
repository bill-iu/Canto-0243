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
  // SVG fragment refs (#…) are fine; all root-absolute assets must sit under /app/
  if (url.startsWith('/') && !url.startsWith('/app/')) {
    console.error(`portable-host-build-self-check: asset not under /app/: ${url}`);
    process.exit(1);
  }
}
if (!html.includes('/app/fonts/')) {
  console.error('portable-host-build-self-check: expected /app/fonts/ links (use %BASE_URL%fonts/ in index.html)');
  process.exit(1);
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

let chromeTabsCss = false;
let draggabillyAsset = false;
for (const name of fs.readdirSync(assetsDir)) {
  const content = fs.readFileSync(path.join(assetsDir, name), 'utf8');
  if (name.endsWith('.css') && content.includes('.chrome-tabs')) chromeTabsCss = true;
  if (name.includes('draggabilly') || content.includes('Draggabilly PACKAGED')) {
    draggabillyAsset = true;
  }
}
if (!chromeTabsCss) {
  console.error('portable-host-build-self-check: missing chrome-tabs CSS in assets');
  process.exit(1);
}
if (!draggabillyAsset) {
  const all = fs.readdirSync(assetsDir).join(' ');
  if (!/draggabilly/i.test(all)) {
    console.error('portable-host-build-self-check: missing Draggabilly asset');
    process.exit(1);
  }
}

const jsBundle = fs
  .readdirSync(assetsDir)
  .filter((n) => n.endsWith('.js') && n.startsWith('index-'))
  .map((n) => fs.readFileSync(path.join(assetsDir, n), 'utf8'))
  .join('\n');
if (!jsBundle.includes('chrome-tab') && !jsBundle.includes('ChromeTabs')) {
  // chrome-tabs may live in a split chunk named chrome-tabs-bar-*.js
  const split = fs.readdirSync(assetsDir).some((n) => n.includes('chrome-tabs'));
  if (!split) {
    console.error('portable-host-build-self-check: chrome-tabs JS not found in portable bundle');
    process.exit(1);
  }
}

// PR3: maintainer API paths must ship in portable host
const allJs = fs
  .readdirSync(assetsDir)
  .filter((n) => n.endsWith('.js'))
  .map((n) => fs.readFileSync(path.join(assetsDir, n), 'utf8'))
  .join('\n');
for (const marker of ['/relations/manual', '/lexicon/corrections']) {
  if (!allJs.includes(marker)) {
    console.error(`portable-host-build-self-check: missing maintainer API path ${marker}`);
    process.exit(1);
  }
}

console.log('portable-host-build-self-check: ok');
