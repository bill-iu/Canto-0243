/** ADR-0036 S2+S3 source contract — node client/scripts/lexicon-mount-self-check.mjs */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const vite = readFileSync(join(root, 'client/vite.config.ts'), 'utf8');
const cli = readFileSync(join(root, 'ingest/cli.py'), 'utf8');
const restore = readFileSync(join(root, 'client/src/db/lexicon-restore.ts'), 'utf8');
const adr = readFileSync(join(root, 'docs/adr/0036-dual-channel-lexicon-mount.md'), 'utf8');
const ctx = readFileSync(join(root, 'CONTEXT.md'), 'utf8');

if (!vite.includes('lexiconDevMountPlugin') || !vite.includes('lyrics.db')) {
  throw new Error('vite: missing S2 lexiconDevMountPlugin');
}
if (!vite.includes('rootLyricsDb')) throw new Error('vite: root SSOT path');
if (!cli.includes('no_copy_public') && !cli.includes('no-copy-public')) {
  throw new Error('cli: missing --no-copy-public');
}
if (!cli.includes('copy-db')) throw new Error('cli: copy-db sync');
if (!restore.includes('purgeSwLexiconCache') || !restore.includes('purgeStaleLexiconCaches')) {
  throw new Error('restore: C1 SW purge helpers');
}
for (const term of ['詞庫掛載', '詞庫渠道同步', '詞庫開發掛載']) {
  if (!ctx.includes(term)) throw new Error(`CONTEXT missing ${term}`);
}
if (!adr.includes('Combo C') && !adr.includes('詞庫渠道同步')) {
  throw new Error('ADR-0036 incomplete');
}

console.log('lexicon-mount-self-check: ok');
