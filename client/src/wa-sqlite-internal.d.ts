declare module '@journeyapps/wa-sqlite/dist/wa-sqlite.mjs' {
  const SQLiteESMFactory: () => Promise<unknown>;
  export default SQLiteESMFactory;
}

declare module '@journeyapps/wa-sqlite/src/examples/OPFSCoopSyncVFS.js' {
  export class OPFSCoopSyncVFS {
    static create(name: string, module: unknown): Promise<SQLiteVFS>;
  }
}

interface FileSystemSyncAccessHandle {
  close(): void;
  flush(): void;
  getSize(): number;
  truncate(size: number): void;
  write(buffer: BufferSource, options?: { at?: number }): number;
}

interface FileSystemFileHandle {
  createSyncAccessHandle(): Promise<FileSystemSyncAccessHandle>;
}
