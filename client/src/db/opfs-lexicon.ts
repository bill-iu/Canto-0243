/**
 * Versioned lexicon OPFS import — ADR-0024 DB-2
 * One-time fetch per semver; subsequent ensure skips network.
 */
import {
  opfsFileSize,
  readOpfsFile,
  removeOpfsFile,
  writeOpfsFile,
} from './opfs-storage.ts';

export function lexiconOpfsFileName(version: string): string {
  const safe = version.replace(/[^a-zA-Z0-9._-]+/g, '_');
  return `lyrics-${safe}.db`;
}

export type EnsureLexiconResult = {
  fileName: string;
  byteSize: number;
  /** true when fetchBytes ran this call */
  fetched: boolean;
};

export async function ensureLexiconInOpfs(opts: {
  version: string;
  fetchBytes: () => Promise<Uint8Array>;
}): Promise<EnsureLexiconResult> {
  const fileName = lexiconOpfsFileName(opts.version);
  const existing = await opfsFileSize(fileName);
  if (existing > 0) {
    return { fileName, byteSize: existing, fetched: false };
  }

  const bytes = await opts.fetchBytes();
  if (!bytes.byteLength) {
    throw new Error(`ensureLexiconInOpfs: empty payload for ${fileName}`);
  }
  await writeOpfsFile(fileName, bytes);
  return { fileName, byteSize: bytes.byteLength, fetched: true };
}

export async function readLexiconFromOpfs(version: string): Promise<Uint8Array | null> {
  return readOpfsFile(lexiconOpfsFileName(version));
}

export async function removeLexiconFromOpfs(version: string): Promise<void> {
  await removeOpfsFile(lexiconOpfsFileName(version));
}
