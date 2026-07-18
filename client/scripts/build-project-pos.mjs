/** Build project-pos-index.json into public/ (ADR-0058). Run from client/. */
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const py = process.env.PYTHON || 'python';
const r = spawnSync(py, ['-m', 'ingest.project_pos', 'build'], {
  cwd: repoRoot,
  stdio: 'inherit',
  shell: process.platform === 'win32',
});
if ((r.status ?? 1) !== 0) process.exit(r.status ?? 1);
