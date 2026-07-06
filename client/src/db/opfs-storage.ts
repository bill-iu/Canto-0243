/**
 * OPFS file primitives — ADR-0024 DB-2
 * ponytail: main-thread async API (sync access handles are Worker-only)
 */

let opfsRoot: FileSystemDirectoryHandle | null = null;
let opfsProbe: Promise<FileSystemDirectoryHandle | null> | null = null;
let opfsUnavailable = false;

async function probeRootDir(): Promise<FileSystemDirectoryHandle | null> {
  if (opfsRoot) return opfsRoot;
  if (opfsUnavailable) return null;
  if (typeof navigator === 'undefined' || typeof navigator.storage?.getDirectory !== 'function') {
    opfsUnavailable = true;
    return null;
  }

  opfsProbe ??= navigator.storage.getDirectory()
    .then((root) => {
      opfsRoot = root;
      return root;
    })
    .catch(() => {
      opfsUnavailable = true;
      return null;
    })
    .finally(() => {
      opfsProbe = null;
    });

  return opfsProbe;
}

export async function opfsAvailable(): Promise<boolean> {
  return (await probeRootDir()) !== null;
}

async function rootDir(): Promise<FileSystemDirectoryHandle> {
  const root = await probeRootDir();
  if (!root) {
    throw new Error('OPFS unavailable (secure context + storage.getDirectory required)');
  }
  return root;
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
  await writable.write(bytes as FileSystemWriteChunkType);
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
