/**
 * Build fonts for browser PWA (prebuild) - self-host for offline.
 * Downloads only the woff2 for weights used in the Google Fonts link.
 * Outputs to public/fonts/ so they are included in dist and precached by workbox (glob has woff2).
 */

import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'node:url';

const outDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/fonts');

async function fetchText(url: string, headers: Record<string, string> = {}): Promise<string> {
  return new Promise((resolve, reject) => {
    https.get(url, { headers }, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode} for ${url}`));
        return;
      }
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

async function download(url: string, dest: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    https.get(url, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode} for ${url}`));
        return;
      }
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

async function main() {
  // The exact CSS url from client/index.html (with display=swap)
  const cssUrl = 'https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@500;600;700&family=Playfair+Display:ital,wght@0,500;0,600;1,500&display=swap';

  // Use a browser UA to get woff2 (not ttf)
  const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

  console.log('Fetching Google Fonts CSS...');
  const css = await fetchText(cssUrl, { 'User-Agent': ua });

  // Parse @font-face for woff2
  const faceRegex = /@font-face\s*\{([^}]+)\}/g;
  const faces: Array<{ family: string; weight: string; style: string; url: string }> = [];
  let m;
  while ((m = faceRegex.exec(css)) !== null) {
    const block = m[1];
    const family = (block.match(/font-family:\s*['"]?([^'";]+)['"]?/) || [])[1]?.trim();
    const weight = (block.match(/font-weight:\s*(\d+)/) || [])[1];
    const style = (block.match(/font-style:\s*(\w+)/) || [])[1] || 'normal';
    const src = (block.match(/src:\s*url\((https:[^)]+\.woff2)\)/) || [])[1];
    if (family && weight && src) {
      faces.push({ family, weight, style, url: src });
    }
  }

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  for (const face of faces) {
    const ext = face.style === 'italic' ? '-italic' : '';
    const safeFamily = face.family.replace(/\s+/g, '');
    const fileName = `${safeFamily}-${face.weight}${ext}.woff2`;
    const dest = path.join(outDir, fileName);
    console.log(`Downloading ${face.family} ${face.weight} ${face.style} → ${fileName}`);
    await download(face.url, dest);
  }

  // Generate fonts.css with @font-face pointing to local files (relative urls work regardless of base)
  let cssContent = '';
  for (const face of faces) {
    const ext = face.style === 'italic' ? '-italic' : '';
    const safeFamily = face.family.replace(/\s+/g, '');
    const fileName = `${safeFamily}-${face.weight}${ext}.woff2`;
    cssContent += `@font-face {
  font-family: '${face.family}';
  font-style: ${face.style};
  font-weight: ${face.weight};
  src: url('./${fileName}') format('woff2');
  font-display: swap;
}
`;
  }
  fs.writeFileSync(path.join(outDir, 'fonts.css'), cssContent);
  console.log('✓ fonts.css generated');

  console.log(`✓ ${faces.length} font files downloaded to public/fonts/`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
