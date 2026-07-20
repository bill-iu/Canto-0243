/**
 * Client prebuild with per-step content stamps (C5).
 * Steps: project-pos → ranking → fonts → copy-db.
 * Force: PREBUILD_FORCE=1 or --force
 */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  hashFiles,
  hashStatVersion,
  hashText,
  shouldSkip,
  writeStamp,
} from './prebuild-stamp.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const clientRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(clientRoot, '..');
const cacheDir = path.join(repoRoot, '.cache', 'client-prebuild');
const publicDir = path.join(clientRoot, 'public');

function run(cmd, args, env = {}) {
  const r = spawnSync(cmd, args, {
    cwd: clientRoot,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: { ...process.env, ...env },
  });
  if ((r.status ?? 1) !== 0) process.exit(r.status ?? 1);
}

function step(name, fingerprint, outputs, runFn) {
  if (shouldSkip(cacheDir, name, fingerprint, outputs)) {
    console.log(`prebuild: skip ${name} (stamp hit)`);
    return;
  }
  console.log(`prebuild: run ${name}`);
  runFn();
  writeStamp(cacheDir, name, fingerprint);
}

step(
  'project-pos',
  hashFiles([
    path.join(repoRoot, 'data/pos/project_pos.tsv'),
    path.join(repoRoot, 'data/pos/project_pos.meta.json'),
    path.join(repoRoot, 'ingest/project_pos.py'),
  ]),
  [path.join(publicDir, 'project-pos-index.json')],
  () => run('node', ['scripts/build-project-pos.mjs']),
);

step(
  'ranking',
  hashFiles([
    path.join(repoRoot, 'data/rime/char.csv'),
    path.join(repoRoot, 'data/essay/essay-cantonese.txt'),
    path.join(repoRoot, 'data/lexicon/curated_common.txt'),
    path.join(repoRoot, 'data/cilin/new_cilin.txt'),
    path.join(repoRoot, 'data/thesaurus/dict_synonym.txt'),
    path.join(repoRoot, 'data/thesaurus/dict_antonym.txt'),
    path.join(repoRoot, 'data/syn_ant/compound_synonyms.txt'),
    path.join(repoRoot, 'data/syn_ant/compound_antonyms.txt'),
    path.join(clientRoot, 'scripts/build-ranking-index.ts'),
    path.join(clientRoot, 'src/db/ranking-loader.node.ts'),
    path.join(clientRoot, 'src/db/thesaurus-loader.node.ts'),
    path.join(clientRoot, 'src/db/rime-index-loader.node.ts'),
  ]),
  [
    path.join(publicDir, 'ranking-index.json'),
    path.join(publicDir, 'static-syn-index.json'),
    path.join(publicDir, 'static-ant-index.json'),
    path.join(publicDir, 'static-cilin-syn-index.json'),
    path.join(publicDir, 'rhyme-letter-index.json'),
  ],
  () => run('npx', ['tsx', 'scripts/build-ranking-index.ts']),
);

// ponytail: fonts stamp = script body (URLs/subset text live there); network fetch only on miss
step(
  'fonts',
  hashFiles([path.join(clientRoot, 'scripts/build-fonts.ts')]),
  [path.join(publicDir, 'fonts/fonts.css')],
  () => run('npx', ['tsx', 'scripts/build-fonts.ts']),
);

const lexiconVersion =
  process.env.LEXICON_VERSION ||
  process.env.VITE_LEXICON_VERSION ||
  process.env.RELEASE_TAG ||
  'v1.0.7';

step(
  'copy-db',
  hashText(
    [
      hashStatVersion(path.join(repoRoot, 'lyrics.db'), lexiconVersion),
      hashFiles([
        path.join(clientRoot, 'copy-db.js'),
        path.join(clientRoot, 'node_modules/sql.js/dist/sql-wasm-browser.wasm'),
      ]),
    ].join(':'),
  ),
  [
    path.join(publicDir, 'lyrics.db'),
    path.join(publicDir, 'lexicon-manifest.json'),
    path.join(publicDir, 'sql-wasm-browser.wasm'),
  ],
  () => run('node', ['copy-db.js'], { LEXICON_VERSION: lexiconVersion }),
);

console.log('prebuild: done');
