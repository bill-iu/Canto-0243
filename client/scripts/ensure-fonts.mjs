/** Ensure public/fonts exists before portable/PWA build (skip if already built). */
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const clientRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const fontsCss = join(clientRoot, 'public/fonts/fonts.css');
if (existsSync(fontsCss)) {
  console.log('ensure-fonts: public/fonts/fonts.css present');
  process.exit(0);
}

console.log('ensure-fonts: missing fonts.css — running build-fonts…');
const r = spawnSync('npx', ['tsx', 'scripts/build-fonts.ts'], {
  cwd: clientRoot,
  stdio: 'inherit',
  shell: true,
});
if (r.status !== 0 || !existsSync(fontsCss)) {
  // ponytail: CI may lack network to fonts.googleapis; local checkout usually has fonts cached
  console.warn('ensure-fonts: build-fonts failed or incomplete — continuing without local fonts');
}
process.exit(0);
