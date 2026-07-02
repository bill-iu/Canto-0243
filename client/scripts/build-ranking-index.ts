/**
 * Build ranking-index.json for browser PWA (prebuild).
 * ponytail: full essay corpus — ~4MB JSON; upgrade path: delta / top-N only
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildRankingData } from '../src/db/ranking-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public');
const outPath = path.join(outDir, 'ranking-index.json');

const data = buildRankingData(repoRoot);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(data));

const synAntSrc = path.join(repoRoot, 'data/syn_ant');
const synAntDst = path.join(outDir, 'data/syn_ant');
fs.mkdirSync(synAntDst, { recursive: true });
for (const name of ['compound_synonyms.txt', 'compound_antonyms.txt']) {
  const src = path.join(synAntSrc, name);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, path.join(synAntDst, name));
  }
}

const kb = Math.round(fs.statSync(outPath).size / 1024);
console.log(`✓ ranking-index.json (${kb} KB)`);
console.log('✓ data/syn_ant/*.txt');
