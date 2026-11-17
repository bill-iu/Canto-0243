/** Safari <26: small storage-only Worker; never loads SQLite/WASM. */
import { storageError } from './storage-error.ts';

export type WriteRequest =
  | { type: 'open'; name: string }
  | { type: 'write'; bytes: Uint8Array; offset: number }
  | { type: 'finish'; size: number };

let access: FileSystemSyncAccessHandle | null = null;
let fileName = '';

export async function handleWriteRequest(message: WriteRequest): Promise<void> {
  try {
    if (message.type === 'open') {
      fileName = message.name;
      const root = await navigator.storage.getDirectory();
      const file = await root.getFileHandle(fileName, { create: true });
      if (typeof file.createSyncAccessHandle !== 'function') {
        throw new DOMException('OPFS sync writes unavailable', 'NotSupportedError');
      }
      access = await file.createSyncAccessHandle();
      access.truncate(0);
    } else {
      if (!access) throw new Error('OPFS writer not open');
      if (message.type === 'write') {
        let written = 0;
        while (written < message.bytes.byteLength) {
          const count = access.write(message.bytes.subarray(written) as BufferSource, { at: message.offset + written });
          if (count <= 0) throw new Error('OPFS write made no progress');
          written += count;
        }
      } else {
        access.truncate(message.size);
        access.flush();
        access.close();
        access = null;
      }
    }
  } catch (error) {
    try { access?.close(); } catch { /* preserve the original failure */ }
    access = null;
    throw storageError(error, `write-${message.type}`, fileName);
  }
}

self.onmessage = async (event: MessageEvent<WriteRequest>) => {
  try {
    await handleWriteRequest(event.data);
    self.postMessage({ ok: true });
  } catch (error) {
    const failure = storageError(error, `write-${event.data.type}`, fileName);
    self.postMessage({ ok: false, name: failure.name, message: failure.message });
  }
};
