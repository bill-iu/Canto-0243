/**
 * Copy the release lexicon into public/ and write the tiny manifest the PWA
 * uses before deciding whether to fetch the large database.
 */

import { createHash } from 'crypto';
import fs from 'fs/promises';
import path from 'path';

const SOURCE_DB = path.resolve('../lyrics.db');
const SOURCE_WASM = path.resolve('./node_modules/sql.js/dist/sql-wasm-browser.wasm');
const LEXICON_VERSION =
  process.env.LEXICON_VERSION ||
  process.env.VITE_LEXICON_VERSION ||
  process.env.RELEASE_TAG ||
  process.argv[2] ||
  'dev';
const TARGET_DB_FILE = `lyrics.${LEXICON_VERSION}.db`;
const TARGET_DB = path.resolve(`./public/${TARGET_DB_FILE}`);
const TARGET_WASM = path.resolve('./public/sql-wasm-browser.wasm');
const TARGET_MANIFEST = path.resolve('./public/lexicon-manifest.json');

async function removeOldDatabases() {
  const entries = await fs.readdir('./public', { withFileTypes: true }).catch(() => []);
  await Promise.all(
    entries
      .filter((entry) => entry.isFile() && /^lyrics(?:\..*)?\.db$/.test(entry.name))
      .map((entry) => fs.unlink(path.resolve('./public', entry.name))),
  );
}

async function sha256(pathname) {
  const bytes = await fs.readFile(pathname);
  return createHash('sha256').update(bytes).digest('hex');
}

async function copyDatabase() {
  try {
    await fs.mkdir('./public', { recursive: true });
    await removeOldDatabases();

    await fs.copyFile(SOURCE_DB, TARGET_DB);
    console.log(`OK Database copied to public/${TARGET_DB_FILE}`);

    const stats = await fs.stat(TARGET_DB);
    const digest = await sha256(TARGET_DB);
    console.log(`  Size: ${Math.round((stats.size / 1024 / 1024) * 100) / 100} MB`);

    await fs.writeFile(
      TARGET_MANIFEST,
      `${JSON.stringify(
        {
          lexiconVersion: LEXICON_VERSION,
          dbFile: TARGET_DB_FILE,
          byteSize: stats.size,
          sha256: digest,
        },
        null,
        2,
      )}\n`,
      'utf8',
    );
    console.log('OK lexicon-manifest.json written');

    // ponytail: same-origin wasm for COEP dev server (was CDN sql.js.org)
    await fs.copyFile(SOURCE_WASM, TARGET_WASM);
    console.log('OK sql.js wasm copied to public/sql-wasm-browser.wasm');

    return true;
  } catch (error) {
    console.error('ERROR Failed to copy database:', error);
    return false;
  }
}

copyDatabase()
  .then((success) => {
    process.exit(success ? 0 : 1);
  })
  .catch(() => {
    process.exit(1);
  });
