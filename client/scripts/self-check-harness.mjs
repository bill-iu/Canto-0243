#!/usr/bin/env node
/**
 * C9: deep self-check harness — manifest → run(tag).
 * Files stay as one-check scripts; interface is this runner.
 *
 *   node scripts/self-check-harness.mjs --list
 *   node scripts/self-check-harness.mjs --tag ci
 *   node scripts/self-check-harness.mjs --tag grammar
 *   node scripts/self-check-harness.mjs --id parser
 */
import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPTS = dirname(fileURLToPath(import.meta.url));
const CLIENT = join(SCRIPTS, '..');
const MANIFEST_PATH = join(SCRIPTS, 'self-check-manifest.json');
const HARNESS_NAME = 'self-check-harness.mjs';

/** @typedef {{ id: string, script: string, args?: string[], tags: string[] }} Check */

function loadManifest() {
  const raw = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'));
  /** @type {Check[]} */
  const checks = [];
  const seen = new Set();
  for (const c of raw.checks ?? []) {
    if (!c?.id || !c?.script) continue;
    checks.push({
      id: String(c.id),
      script: String(c.script),
      args: Array.isArray(c.args) ? c.args.map(String) : [],
      tags: Array.isArray(c.tags) ? c.tags.map(String) : ['local'],
    });
    seen.add(c.script);
  }
  if (raw.autoDiscover) {
    const autoTags = Array.isArray(raw.autoTags) ? raw.autoTags.map(String) : ['local'];
    for (const name of readdirSync(SCRIPTS)) {
      if (name === HARNESS_NAME) continue;
      if (!/self-check\.(ts|mjs|js)$/.test(name)) continue;
      if (seen.has(name)) continue;
      const id = name.replace(/-self-check\.(ts|mjs|js)$/, '');
      checks.push({ id, script: name, args: [], tags: [...autoTags] });
    }
  }
  return checks;
}

function parseArgs(argv) {
  /** @type {{ list: boolean, tags: string[], ids: string[] }} */
  const out = { list: false, tags: [], ids: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--list') out.list = true;
    else if (a === '--tag' && argv[i + 1]) out.tags.push(argv[++i]);
    else if (a === '--id' && argv[i + 1]) out.ids.push(argv[++i]);
    else if (a === '--help' || a === '-h') {
      console.log(`Usage: node scripts/self-check-harness.mjs [--list] [--tag TAG]... [--id ID]...`);
      process.exit(0);
    }
  }
  return out;
}

/** @param {Check} check */
function runCheck(check) {
  const scriptPath = join(SCRIPTS, check.script);
  if (!existsSync(scriptPath)) {
    console.error(`missing script: ${check.script}`);
    return 1;
  }
  const isTs = check.script.endsWith('.ts');
  const cmd = isTs ? 'npx' : process.execPath;
  const args = isTs
    ? ['tsx', join('scripts', check.script), ...check.args]
    : [scriptPath, ...check.args];
  console.log(`→ ${check.id} (${check.script})`);
  const r = spawnSync(cmd, args, {
    cwd: CLIENT,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: process.env,
  });
  if (r.error) {
    console.error(r.error);
    return 1;
  }
  return r.status ?? 1;
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  const all = loadManifest();
  let selected = all;
  if (opts.ids.length) {
    const want = new Set(opts.ids);
    selected = all.filter((c) => want.has(c.id));
  } else if (opts.tags.length) {
    const want = new Set(opts.tags);
    selected = all.filter((c) => c.tags.some((t) => want.has(t)));
  } else if (!opts.list) {
    console.error('Specify --tag, --id, or --list');
    process.exit(2);
  }

  if (opts.list) {
    const rows = (opts.tags.length || opts.ids.length ? selected : all).slice().sort((a, b) =>
      a.id.localeCompare(b.id),
    );
    for (const c of rows) {
      console.log(`${c.id}\t${c.tags.join(',')}\t${c.script}`);
    }
    console.log(`# ${rows.length} checks`);
    return;
  }

  if (!selected.length) {
    console.error('no checks matched');
    process.exit(1);
  }

  let failed = 0;
  for (const c of selected) {
    const code = runCheck(c);
    if (code !== 0) failed += 1;
  }
  if (failed) {
    console.error(`self-check-harness: ${failed}/${selected.length} failed`);
    process.exit(1);
  }
  console.log(`self-check-harness: ${selected.length} ok`);
}

main();
