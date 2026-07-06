import { createHash } from 'crypto';
import fs from 'fs/promises';
import path from 'path';

const distDir = path.resolve('dist');
const manifestPath = path.join(distDir, 'lexicon-manifest.json');

async function sha256(pathname) {
  const bytes = await fs.readFile(pathname);
  return createHash('sha256').update(bytes).digest('hex');
}

function fail(message) {
  console.error(`ERROR ${message}`);
  process.exitCode = 1;
}

async function main() {
  const entries = await fs.readdir(distDir, { withFileTypes: true });
  const dbFiles = entries
    .filter((entry) => entry.isFile() && /^lyrics(?:\..*)?\.db$/.test(entry.name))
    .map((entry) => entry.name);

  if (dbFiles.length !== 1) {
    fail(
      `Pages artifact must contain exactly one lyrics*.db file, found ${dbFiles.length}: ${
        dbFiles.join(', ') || '(none)'
      }`,
    );
    return;
  }

  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  const dbFile = dbFiles[0];
  if (manifest.dbFile !== dbFile) {
    fail(`lexicon-manifest.json points to ${manifest.dbFile}, but artifact contains ${dbFile}`);
    return;
  }

  const dbPath = path.join(distDir, dbFile);
  const stats = await fs.stat(dbPath);
  if (manifest.byteSize !== stats.size) {
    fail(`lexicon-manifest.json byteSize is ${manifest.byteSize}, but ${dbFile} is ${stats.size}`);
    return;
  }

  const digest = await sha256(dbPath);
  if (manifest.sha256 !== digest) {
    fail(`lexicon-manifest.json sha256 does not match ${dbFile}`);
    return;
  }

  console.log(`OK Pages artifact lexicon guardrail passed (${dbFile})`);
}

main().catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
