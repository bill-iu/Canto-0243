/** Versioned OPFS import; both backends share the same per-file import lock. */
import {
  opfsAvailable, opfsFileSize, opfsFileExists, readOpfsFile,
  removeOpfsFile, writeOpfsFile, markOpfsImport,
} from './opfs-storage.ts';

export function lexiconOpfsFileName(version: string): string {
  return `lyrics-${version.replace(/[^a-zA-Z0-9._-]+/g, '_')}.db`;
}

const imports = new Map<string, Promise<unknown>>();
export async function withLexiconImportLock<T>(fileName: string, work: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && typeof navigator.locks?.request === 'function') {
    return navigator.locks.request(`lexicon-ensure-${fileName}`, work);
  }
  // ponytail: per-realm fallback; OPFS exclusive handles reject other realms' writers.
  const previous = imports.get(fileName) ?? Promise.resolve();
  const next = previous.catch(() => {}).then(work);
  imports.set(fileName, next);
  try { return await next; }
  finally { if (imports.get(fileName) === next) imports.delete(fileName); }
}

export type EnsureLexiconResult = { fileName: string; byteSize: number; fetched: boolean };

async function removeLexiconFiles(fileName: string): Promise<void> {
  for (const suffix of ['', '-journal', '-wal', '.importing']) await removeOpfsFile(fileName + suffix);
}

export async function ensureLexiconInOpfs(opts: {
  version: string;
  fetchBytes: () => Promise<Uint8Array>;
  expectedByteSize?: number;
}): Promise<EnsureLexiconResult> {
  if (!(await opfsAvailable())) throw new DOMException('OPFS unavailable', 'NotSupportedError');
  const fileName = lexiconOpfsFileName(opts.version);
  return withLexiconImportLock(fileName, async () => {
    const incomplete = await opfsFileExists(`${fileName}.importing`);
    const existing = await opfsFileSize(fileName);
    if (!incomplete && existing > 0 && (opts.expectedByteSize == null || existing === opts.expectedByteSize)) {
      return { fileName, byteSize: existing, fetched: false };
    }
    const bytes = await opts.fetchBytes();
    if (!bytes.byteLength || (opts.expectedByteSize != null && bytes.byteLength !== opts.expectedByteSize)) {
      throw new Error(`Invalid lexicon payload size for ${fileName}`);
    }
    // The old valid identity is untouched. A failed write leaves this identity marked incomplete.
    if (existing || incomplete) await removeLexiconFiles(fileName);
    await markOpfsImport(fileName);
    await writeOpfsFile(fileName, bytes);
    await removeOpfsFile(`${fileName}.importing`);
    return { fileName, byteSize: bytes.byteLength, fetched: true };
  });
}

export async function readLexiconFromOpfs(version: string): Promise<Uint8Array | null> {
  const fileName = lexiconOpfsFileName(version);
  if (await opfsFileExists(`${fileName}.importing`)) return null;
  return readOpfsFile(fileName);
}

export async function removeLexiconFromOpfs(version: string): Promise<void> {
  const fileName = lexiconOpfsFileName(version);
  return withLexiconImportLock(fileName, () => removeLexiconFiles(fileName));
}
