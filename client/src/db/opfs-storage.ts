/**
 * OPFS file primitives — ADR-0024 DB-2
 * ponytail: main-thread async API (sync access handles are Worker-only)
 */

export function opfsAvailable(): boolean {
  return typeof navigator !== 'undefined' && typeof navigator.storage?.getDirectory === 'function';
}

async function rootDir(): Promise<FileSystemDirectoryHandle> {
  if (!opfsAvailable()) {
    throw new Error('OPFS unavailable (secure context + storage.getDirectory required)');
  }
  return navigator.storage.getDirectory();
}

export async function opfsFileSize(name: string): Promise<number> {
  try {
    const root = await rootDir();
    const handle = await root.getFileHandle(name);
    const file = await handle.getFile();
    return file.size;
  } catch {
    return 0;
  }
}

export async function readOpfsFile(name: string): Promise<Uint8Array | null> {
  try {
    const root = await rootDir();
    const handle = await root.getFileHandle(name);
    const file = await handle.getFile();
    if (!file.size) {
      return null;
    }
    return new Uint8Array(await file.arrayBuffer());
  } catch {
    return null;
  }
}

export async function writeOpfsFile(name: string, bytes: Uint8Array): Promise<void> {
  const root = await rootDir();
  const handle = await root.getFileHandle(name, { create: true });
  const writable = await handle.createWritable();
  await writable.write(bytes);
  await writable.close();
}

export async function removeOpfsFile(name: string): Promise<void> {
  try {
    const root = await rootDir();
    await root.removeEntry(name);
  } catch {
    // ponytail: missing entry is fine
  }
}
