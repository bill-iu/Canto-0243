/**
 * Build fonts for browser PWA (prebuild) - self-host for offline.
 * Downloads only the woff2 for weights used in the Google Fonts link.
 * Outputs to public/fonts/ so they are included in dist and precached by workbox (glob has woff2).
 *
 * The display slogans have a separate critical subset so offline cold starts do
 * not depend on whichever CJK unicode-range chunk Google Fonts returns last.
 */

import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'node:url';

const outDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/fonts');
const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const criticalDisplayText = '·搵韻即使離線亦完全可用呢一次拎返你嘅創作主導權關於，。';
const criticalCssUrl = `https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@500;600;700&display=block&text=${encodeURIComponent(criticalDisplayText)}`;
const logoText = '粵CANTO';
const logoCssUrl = `https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700&display=block&text=${encodeURIComponent(logoText)}`;

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

  console.log('Fetching Google Fonts CSS...');
  const css = await fetchText(cssUrl, { 'User-Agent': ua });
  const criticalCss = await fetchText(criticalCssUrl, { 'User-Agent': ua });
  const logoCss = await fetchText(logoCssUrl, { 'User-Agent': ua });

  // Parse @font-face for woff2
  const faceRegex = /@font-face\s*\{([^}]+)\}/g;
  const faces: Array<{ family: string; weight: string; style: string; url: string }> = [];
  const seenUrls = new Set<string>();
  let m;
  while ((m = faceRegex.exec(css)) !== null) {
    const block = m[1];
    const family = (block.match(/font-family:\s*['"]?([^'";]+)['"]?/) || [])[1]?.trim();
    const weight = (block.match(/font-weight:\s*(\d+)/) || [])[1];
    const style = (block.match(/font-style:\s*(\w+)/) || [])[1] || 'normal';
    const src = (block.match(/src:\s*url\((https:[^)]+)\)\s*format\(['"]woff2['"]\)/) || [])[1];
    if (family && weight && src && !seenUrls.has(src)) {
      seenUrls.add(src);
      faces.push({ family, weight, style, url: src });
    }
  }

  const criticalFaces: Array<{ weight: string; url: string; block: string }> = [];
  faceRegex.lastIndex = 0;
  while ((m = faceRegex.exec(criticalCss)) !== null) {
    const block = m[1];
    const weight = (block.match(/font-weight:\s*(\d+)/) || [])[1];
    const src = (block.match(/src:\s*url\((https:[^)]+)\)\s*format\(['"]woff2['"]\)/) || [])[1];
    if (weight && src) {
      criticalFaces.push({ weight, url: src, block });
    }
  }

  const logoFaces: Array<{ weight: string; url: string; block: string }> = [];
  faceRegex.lastIndex = 0;
  while ((m = faceRegex.exec(logoCss)) !== null) {
    const block = m[1];
    const weight = (block.match(/font-weight:\s*(\d+)/) || [])[1];
    const src = (block.match(/src:\s*url\((https:[^)]+)\)\s*format\(['"]woff2['"]\)/) || [])[1];
    if (weight && src) {
      logoFaces.push({ weight, url: src, block });
    }
  }

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  for (const face of criticalFaces) {
    const fileName = `CantoCriticalSerif-${face.weight}.woff2`;
    const dest = path.join(outDir, fileName);
    console.log(`Downloading Canto Critical Serif ${face.weight} -> ${fileName}`);
    await download(face.url, dest);
  }

  for (const face of logoFaces) {
    const fileName = `CantoLogoSerif-${face.weight}.woff2`;
    const dest = path.join(outDir, fileName);
    console.log(`Downloading Canto Logo Serif ${face.weight} -> ${fileName}`);
    await download(face.url, dest);
  }

  for (const face of faces) {
    const ext = face.style === 'italic' ? '-italic' : '';
    const safeFamily = face.family.replace(/\s+/g, '');
    const fileName = `${safeFamily}-${face.weight}${ext}.woff2`;
    const dest = path.join(outDir, fileName);
    console.log(`Downloading ${face.family} ${face.weight} ${face.style} → ${fileName}`);
    await download(face.url, dest);
  }

  // Rewrite the original CSS to use local font files, preserving all @font-face details (unicode-range etc for CJK)
  let localCss = css;
  for (const face of faces) {
    const ext = face.style === 'italic' ? '-italic' : '';
    const safeFamily = face.family.replace(/\s+/g, '');
    const fileName = `${safeFamily}-${face.weight}${ext}.woff2`;
    // Replace the original remote url with local relative
    localCss = localCss.replaceAll(face.url, `./${fileName}`);
  }
  const criticalLocalCss = criticalFaces.map((face) => {
    const fileName = `CantoCriticalSerif-${face.weight}.woff2`;
    const localBlock = face.block
      .replace(/font-family:\s*['"][^'"]+['"];/, "font-family: 'Canto Critical Serif';")
      .replace(/src:\s*url\((https:[^)]+)\)\s*format\(['"]woff2['"]\);/, `src: url(./${fileName}) format('woff2');`)
      .replace(/font-display:\s*[^;]+;/, 'font-display: block;');
    return `@font-face {${localBlock}}`;
  }).join('\n\n');

  const logoLocalCss = logoFaces.map((face) => {
    const fileName = `CantoLogoSerif-${face.weight}.woff2`;
    const localBlock = face.block
      .replace(/font-family:\s*['"][^'"]+['"];/, "font-family: 'Canto Logo Serif';")
      .replace(/src:\s*url\((https:[^)]+)\)\s*format\(['"]woff2['"]\);/, `src: url(./${fileName}) format('woff2');`)
      .replace(/font-display:\s*[^;]+;/, 'font-display: block;');
    return `@font-face {${localBlock}}`;
  }).join('\n\n');

  const completeCss = [criticalLocalCss, logoLocalCss, localCss].filter(Boolean).join('\n\n');
  if (completeCss.includes('fonts.gstatic.com')) {
    throw new Error('fonts.css still contains remote Google font URLs');
  }

  fs.writeFileSync(path.join(outDir, 'fonts.css'), completeCss);
  console.log('✓ fonts.css generated (with local src urls)');

  console.log(`✓ ${faces.length + criticalFaces.length + logoFaces.length} unique font files (woff2) to public/fonts/`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
