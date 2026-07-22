/** Shared content-stamp helpers for client prebuild skip (C5). */
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export function hashFiles(filePaths) {
  const h = createHash('sha256');
  for (const p of [...filePaths].map((x) => path.resolve(x)).sort()) {
    h.update(p);
    h.update('\0');
    if (fs.existsSync(p) && fs.statSync(p).isFile()) {
      h.update(fs.readFileSync(p));
    } else {
      h.update('MISSING');
    }
    h.update('\0');
  }
  return h.digest('hex');
}

export function hashText(text) {
  return createHash('sha256').update(String(text)).digest('hex');
}

/** Fast fingerprint for large binaries (lyrics.db): size + mtime + version. */
export function hashStatVersion(filePath, version) {
  const h = createHash('sha256');
  h.update(String(version || ''));
  h.update('\0');
  const p = path.resolve(filePath);
  h.update(p);
  h.update('\0');
  if (fs.existsSync(p)) {
    const st = fs.statSync(p);
    h.update(String(st.size));
    h.update('\0');
    h.update(String(st.mtimeMs));
  } else {
    h.update('MISSING');
  }
  return h.digest('hex');
}

export function forceRebuild() {
  return process.env.PREBUILD_FORCE === '1' || process.argv.includes('--force');
}

export function shouldSkip(cacheDir, step, fingerprint, outputPaths) {
  if (forceRebuild()) return false;
  const stamp = path.join(cacheDir, `${step}.stamp`);
  if (!fs.existsSync(stamp)) return false;
  if (fs.readFileSync(stamp, 'utf8').trim() !== fingerprint) return false;
  return outputPaths.every((p) => fs.existsSync(p));
}

export function writeStamp(cacheDir, step, fingerprint) {
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.writeFileSync(path.join(cacheDir, `${step}.stamp`), `${fingerprint}\n`);
}
