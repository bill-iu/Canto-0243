/** OPFS primitives. Safari <26 writes through a dedicated sync-access Worker. */
import { isMissingFile, storageError } from './storage-error.ts';
import type { WriteRequest } from './opfs-write-worker.ts';

let opfsRoot: FileSystemDirectoryHandle | null = null;
let opfsProbe: Promise<FileSystemDirectoryHandle> | null = null;

export function resetOpfsProbe(): void {
  opfsRoot = null;
  opfsProbe = null;
}

async function rootDir(): Promise<FileSystemDirectoryHandle> {
  if (opfsRoot) return opfsRoot;
  if (typeof navigator === 'undefined' || typeof navigator.storage?.getDirectory !== 'function') {
    throw new DOMException('OPFS unavailable', 'NotSupportedError');
  }
  opfsProbe ??= navigator.storage.getDirectory()
    .then(root => (opfsRoot = root))
    .finally(() => { opfsProbe = null; });
  return opfsProbe;
}

export async function opfsAvailable(): Promise<boolean> {
  if (typeof navigator === 'undefined' || typeof navigator.storage?.getDirectory !== 'function') return false;
  try { await rootDir(); return true; }
  catch (error) { throw storageError(error, 'directory'); }
}

export async function opfsFileExists(name: string): Promise<boolean> {
  if (!(await opfsAvailable())) return false;
  try { await (await rootDir()).getFileHandle(name); return true; }
  catch (error) {
    if (isMissingFile(error)) return false;
    throw storageError(error, 'stat', name);
  }
}

export async function opfsFileSize(name: string): Promise<number> {
  if (!(await opfsAvailable())) return 0;
  try { return (await (await (await rootDir()).getFileHandle(name)).getFile()).size; }
  catch (error) {
    if (isMissingFile(error)) return 0;
    throw storageError(error, 'stat', name);
  }
}

export async function readOpfsFile(name: string): Promise<Uint8Array | null> {
  if (!(await opfsAvailable())) return null;
  try {
    const file = await (await (await rootDir()).getFileHandle(name)).getFile();
    return file.size ? new Uint8Array(await file.arrayBuffer()) : null;
  } catch (error) {
    if (isMissingFile(error)) return null;
    throw storageError(error, 'read', name);
  }
}

export async function markOpfsImport(name: string): Promise<void> {
  await (await rootDir()).getFileHandle(`${name}.importing`, { create: true });
}

async function writeWithWorker(name: string, bytes: Uint8Array): Promise<void> {
  const worker = new Worker(new URL('./opfs-write-worker.ts', import.meta.url), { type: 'module' });
  try {
    const ask = (request: WriteRequest, transfer: Transferable[] = []) => new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        worker.removeEventListener('message', message);
        worker.removeEventListener('error', failed);
        worker.removeEventListener('messageerror', failed);
      };
      const message = (event: MessageEvent<{ ok: boolean; name?: string; message?: string }>) => {
        cleanup();
        if (event.data.ok) resolve();
        else reject(storageError(event.data, 'persist', name));
      };
      const failed = () => { cleanup(); reject(storageError(new Error('OPFS writer failed'), 'persist', name)); };
      worker.addEventListener('message', message);
      worker.addEventListener('error', failed);
      worker.addEventListener('messageerror', failed);
      try { worker.postMessage(request, transfer); }
      catch (error) { cleanup(); reject(error); }
    });
    await ask({ type: 'open', name });
    for (let offset = 0; offset < bytes.byteLength; offset += 4 * 1024 * 1024) {
      const chunk = bytes.slice(offset, offset + 4 * 1024 * 1024);
      await ask({ type: 'write', bytes: chunk, offset }, [chunk.buffer]);
    }
    await ask({ type: 'finish', size: bytes.byteLength });
  } finally { worker.terminate(); }
}

export async function writeOpfsFile(name: string, bytes: Uint8Array): Promise<void> {
  try {
    const handle = await (await rootDir()).getFileHandle(name, { create: true });
    if (typeof handle.createWritable === 'function') {
      const writable = await handle.createWritable();
      try {
        for (let offset = 0; offset < bytes.byteLength; offset += 4 * 1024 * 1024) {
          await writable.write(bytes.subarray(offset, offset + 4 * 1024 * 1024) as FileSystemWriteChunkType);
        }
        await writable.truncate(bytes.byteLength);
        await writable.close();
      } catch (error) {
        try { await writable.abort(); } catch { /* preserve original failure */ }
        throw error;
      }
    } else {
      await writeWithWorker(name, bytes);
    }
    if (await opfsFileSize(name) !== bytes.byteLength) throw new Error('OPFS persisted size mismatch');
  } catch (error) { throw storageError(error, 'persist', name); }
}

export async function removeOpfsFile(name: string): Promise<void> {
  if (!(await opfsAvailable())) return;
  try { await (await rootDir()).removeEntry(name); }
  catch (error) {
    if (!isMissingFile(error)) throw storageError(error, 'remove', name);
  }
}
