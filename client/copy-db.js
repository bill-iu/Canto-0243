/**
 * Copy the release lexicon into public/ and write lexicon-manifest.json
 * ADR-0032 G: optional gzip when savings >= 15%
 */

import { createHash } from 'crypto';
import { createReadStream, createWriteStream } from 'fs';
import fs from 'fs/promises';
import path from 'path';
import { pipeline } from 'stream/promises';
import { createGzip } from 'zlib';

const SOURCE_DB = path.resolve('../lyrics.db');
const LEXICON_VERSION =
  process.env.LEXICON_VERSION ||
  process.env.VITE_LEXICON_VERSION ||
  process.env.RELEASE_TAG ||
  process.argv[2] ||
  '394052';
const TARGET_DB_FILE = `lyrics.${LEXICON_VERSION}.db`;
const TARGET_DB = path.resolve(`./public/${TARGET_DB_FILE}`);
const TARGET_GZ = `${TARGET_DB}.gz`;
const SOURCE_WASM = path.resolve('./node_modules/sql.js/dist/sql-wasm-browser.wasm');
const TARGET_WASM = path.resolve('./public/sql-wasm-browser.wasm');
const TARGET_MANIFEST = path.resolve('./public/lexicon-manifest.json');

const MIN_SAVINGS_RATIO = 0.15;

async function removeOldDatabases() {
  const entries = await fs.readdir('./public', { withFileTypes: true }).catch(() => []);
  await Promise.all(
    entries
      .filter((entry) => entry.isFile() && /^lyrics(?:\..*)?\.db(?:\.gz)?$/.test(entry.name))
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

    let preferCompressed = false;
    let compressedByteSize;
    let dbFileGz;

    await pipeline(createReadStream(TARGET_DB), createGzip({ level: 6 }), createWriteStream(TARGET_GZ));
    const gzStats = await fs.stat(TARGET_GZ);
    const savings = (stats.size - gzStats.size) / stats.size;
    if (savings >= MIN_SAVINGS_RATIO) {
      preferCompressed = true;
      compressedByteSize = gzStats.size;
      dbFileGz = `${TARGET_DB_FILE}.gz`;
      console.log(
        `OK gzip ${Math.round((gzStats.size / 1024 / 1024) * 100) / 100} MB (${Math.round(savings * 100)}% smaller)`,
      );
    } else {
      await fs.unlink(TARGET_GZ);
      console.log(`OK gzip skipped (savings ${Math.round(savings * 100)}% < ${MIN_SAVINGS_RATIO * 100}%)`);
    }

    const manifest = {
      lexiconVersion: LEXICON_VERSION,
      dbFile: TARGET_DB_FILE,
      byteSize: stats.size,
      sha256: digest,
      preferCompressed,
    };
    if (preferCompressed) {
      manifest.dbFileGz = dbFileGz;
      manifest.compressedByteSize = compressedByteSize;
    }

    await fs.writeFile(TARGET_MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
    console.log('OK lexicon-manifest.json written');

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