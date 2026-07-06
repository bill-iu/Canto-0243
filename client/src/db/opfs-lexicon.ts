/**
 * Versioned lexicon OPFS import — ADR-0024 DB-2
 * One-time fetch per semver; subsequent ensure skips network.
 * Web Locks guard the download path: only one tab fetches per version at a time.
 * Other tabs wait for the lock, then find the file in OPFS and return immediately.
 */
import {
  opfsAvailable,
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
  if (!(await opfsAvailable())) {
    throw new Error('ensureLexiconInOpfs: OPFS unavailable');
  }

  const fileName = lexiconOpfsFileName(opts.version);

  // Fast path: already in OPFS — skip lock and network entirely
  const existing = await opfsFileSize(fileName);
  if (existing > 0) {
    return { fileName, byteSize: existing, fetched: false };
  }

  // Slow path: acquire a cross-tab lock to serialise downloads.
  // A tab that wins the lock downloads once; all waiting tabs re-check OPFS
  // after the lock is released and find the file already written.
  const doDownload = async (): Promise<EnsureLexiconResult> => {
    const existingNow = await opfsFileSize(fileName);
    if (existingNow > 0) {
      return { fileName, byteSize: existingNow, fetched: false };
    }
    const bytes = await opts.fetchBytes();
    if (!bytes.byteLength) {
      throw new Error(`ensureLexiconInOpfs: empty payload for ${fileName}`);
    }
    await writeOpfsFile(fileName, bytes);
    return { fileName, byteSize: bytes.byteLength, fetched: true };
  };

  if (typeof navigator !== 'undefined' && 'locks' in navigator) {
    return (navigator as Navigator & { locks: LockManager }).locks.request(
      `lexicon-ensure-${fileName}`,
      doDownload,
    );
  }
  return doDownload();
}

export async function readLexiconFromOpfs(version: string): Promise<Uint8Array | null> {
  return readOpfsFile(lexiconOpfsFileName(version));
}

export async function removeLexiconFromOpfs(version: string): Promise<void> {
  await removeOpfsFile(lexiconOpfsFileName(version));
}
