/**
 * Build ranking-index.json for browser PWA (prebuild).
 * ponytail: full essay corpus — ~4MB JSON; upgrade path: delta / top-N only
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildRankingData } from '../src/db/ranking-loader.node.ts';
import { buildStaticSynIndex, buildStaticAntIndex } from '../src/db/thesaurus-loader.node.ts';
import { buildRhymeLetterIndex } from '../src/db/rime-index-loader.node.ts';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const outDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public');
const outPath = path.join(outDir, 'ranking-index.json');
const synOutPath = path.join(outDir, 'static-syn-index.json');
const antOutPath = path.join(outDir, 'static-ant-index.json');
const rhymeOutPath = path.join(outDir, 'rhyme-letter-index.json');

const data = buildRankingData(repoRoot);
const synData = buildStaticSynIndex(repoRoot);
const antData = buildStaticAntIndex(repoRoot);
const rhymeData = buildRhymeLetterIndex(repoRoot);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(data));
fs.writeFileSync(synOutPath, JSON.stringify(synData));
fs.writeFileSync(antOutPath, JSON.stringify(antData));
fs.writeFileSync(rhymeOutPath, JSON.stringify(rhymeData));

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
const synKb = Math.round(fs.statSync(synOutPath).size / 1024);
const antKb = Math.round(fs.statSync(antOutPath).size / 1024);
const synChars = Object.keys(synData).length;
const antChars = Object.keys(antData).length;
console.log(`✓ ranking-index.json (${kb} KB)`);
console.log(`✓ static-syn-index.json (${synKb} KB, ${synChars} heads)`);
console.log(`✓ static-ant-index.json (${antKb} KB, ${antChars} heads)`);
console.log(
  `✓ rhyme-letter-index.json (${Math.round(fs.statSync(rhymeOutPath).size / 1024)} KB, ${Object.keys(rhymeData.finalOptions).length} fragments)`,
);
console.log('✓ data/syn_ant/*.txt');
