/** Delegates to TS self-check — node client/scripts/portable-api-search-self-check.mjs */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const clientRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = spawnSync('npx', ['tsx', 'scripts/portable-api-search-self-check.ts'], {
  cwd: clientRoot,
  encoding: 'utf8',
  shell: true,
  stdio: 'inherit',
});
process.exit(result.status ?? 1);
